"""Generic HTML careers page parser."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from role_radar.connectors.base import BaseConnector
from role_radar.models import ATSType, Company, Job, JobLocation
from role_radar.utils.http import HTTPClient
from role_radar.utils.logging import get_logger

logger = get_logger(__name__)


class GenericHTMLConnector(BaseConnector):
    """Generic connector for parsing HTML careers pages.

    This connector is used as a fallback when a company doesn't use
    a known ATS or when the ATS-specific connector fails.

    It respects robots.txt and uses heuristics to find job listings.
    """

    def __init__(self, http_client: HTTPClient):
        super().__init__(http_client)

    def _looks_like_job_link(self, href: str, text: str) -> bool:
        """Check if a link looks like a job posting."""
        text_lower = text.lower()
        href_lower = href.lower()

        # Positive signals
        job_keywords = [
            "product manager", "pm", "product", "manager",
            "job", "position", "role", "career", "opportunity",
        ]

        has_job_keyword = any(kw in text_lower for kw in job_keywords)

        # Negative signals - skip these
        skip_patterns = [
            r"sign\s*in", r"log\s*in", r"apply", r"submit",
            r"twitter", r"linkedin", r"facebook", r"instagram",
            r"privacy", r"terms", r"cookie", r"contact",
            r"blog", r"news", r"about\s*us", r"team",
            r"\.pdf$", r"\.doc", r"mailto:", r"tel:",
        ]

        for pattern in skip_patterns:
            if re.search(pattern, text_lower) or re.search(pattern, href_lower):
                return False

        return has_job_keyword and len(text) > 5 and len(text) < 200

    def _extract_location(self, text: str) -> JobLocation:
        """Try to extract location from text."""
        text_lower = text.lower()

        remote = "remote" in text_lower
        hybrid = "hybrid" in text_lower

        # Common location patterns
        location_patterns = [
            r"(san\s+francisco|sf|bay\s+area)",
            r"(new\s+york|nyc|ny)",
            r"(los\s+angeles|la)",
            r"(seattle|wa)",
            r"(austin|tx)",
            r"(boston|ma)",
            r"(chicago|il)",
        ]

        city = None
        for pattern in location_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                city = match.group(1).title()
                break

        return JobLocation(
            city=city,
            remote=remote,
            hybrid=hybrid,
            raw_location=text[:100] if text else "",
        )

    def _parse_jobs_from_page(
        self,
        soup: BeautifulSoup,
        company: Company,
        base_url: str,
    ) -> list[Job]:
        """Parse jobs from an HTML page."""
        jobs = []
        seen_urls = set()

        # Strategy 1: Look for structured job listings
        # Common patterns: <article>, <li> with job-related classes,
        # <div> with job/position/career classes

        job_containers = soup.find_all(
            ["article", "li", "div", "a"],
            class_=re.compile(r"job|position|career|posting|listing|opening", re.I),
        )

        for container in job_containers:
            try:
                # Find the job link
                link = container.find("a", href=True) if container.name != "a" else container
                if not link:
                    continue

                href = link.get("href", "")
                title = link.get_text(strip=True)

                if not href or not title:
                    continue

                # Make absolute URL
                full_url = urljoin(base_url, href)

                # Skip duplicates
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Look for location in nearby text
                container_text = container.get_text(" ", strip=True)
                location = self._extract_location(container_text)

                # Generate a pseudo-ID from URL
                job_id = urlparse(full_url).path.split("/")[-1] or str(hash(full_url))

                job = Job(
                    id=f"{company.slug}_{job_id}",
                    external_id=str(job_id),
                    company=company.name,
                    company_slug=company.slug,
                    company_type=company.company_type,
                    title=title,
                    location=location,
                    apply_url=full_url,
                    source_ats=ATSType.GENERIC_HTML,
                )
                jobs.append(job)

            except Exception as e:
                logger.debug("container_parse_error", error=str(e))

        # Strategy 2: Look for any links that look like job postings
        if not jobs:
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)

                if not self._looks_like_job_link(href, text):
                    continue

                full_url = urljoin(base_url, href)

                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Skip if it's clearly just navigation
                if len(text) < 10:
                    continue

                job_id = urlparse(full_url).path.split("/")[-1] or str(hash(full_url))

                job = Job(
                    id=f"{company.slug}_{job_id}",
                    external_id=str(job_id),
                    company=company.name,
                    company_slug=company.slug,
                    company_type=company.company_type,
                    title=text,
                    location=JobLocation(raw_location=""),
                    apply_url=full_url,
                    source_ats=ATSType.GENERIC_HTML,
                )
                jobs.append(job)

        return jobs

    # Validation thresholds for parsed output. Tune via subclass if needed.
    MAX_TITLE_LENGTH = 200
    MIN_TITLE_LENGTH = 4
    SUSPICIOUS_LOW_COUNT = 3  # Fewer real jobs than this → likely a layout change

    def _validate_jobs(self, jobs: list[Job], company: Company, careers_url: str) -> list[Job]:
        """Drop implausible parsed jobs and warn if the result looks suspicious.

        Generic HTML scraping is the most fragile connector type; one site redesign
        breaks the parser silently. These checks surface failures early instead of
        polluting downstream scoring with junk.
        """
        valid: list[Job] = []
        rejected_long = 0
        rejected_short = 0
        for job in jobs:
            title_len = len(job.title.strip())
            if title_len > self.MAX_TITLE_LENGTH:
                rejected_long += 1
                continue
            if title_len < self.MIN_TITLE_LENGTH:
                rejected_short += 1
                continue
            valid.append(job)

        if rejected_long or rejected_short:
            logger.warning(
                "generic_html_implausible_jobs_dropped",
                company=company.name,
                url=careers_url,
                rejected_too_long=rejected_long,
                rejected_too_short=rejected_short,
                kept=len(valid),
            )

        if 0 < len(valid) < self.SUSPICIOUS_LOW_COUNT:
            logger.warning(
                "generic_html_low_yield",
                company=company.name,
                url=careers_url,
                job_count=len(valid),
                hint="Page layout may have changed — verify in `role-radar debug`.",
            )

        return valid

    def fetch_jobs(self, company: Company) -> list[Job]:
        """Fetch jobs from a company's careers page."""
        careers_url = company.careers_url

        if not careers_url:
            logger.warning("no_careers_url", company=company.name)
            return []

        try:
            # This will check robots.txt
            response = self.http_client.get(careers_url)
            soup = BeautifulSoup(response.text, "html.parser")

            jobs = self._parse_jobs_from_page(soup, company, careers_url)
            jobs = self._validate_jobs(jobs, company, careers_url)

            logger.info(
                "generic_html_jobs_fetched",
                company=company.name,
                url=careers_url,
                job_count=len(jobs),
            )

            return jobs

        except ValueError as e:
            # robots.txt disallowed
            logger.warning(
                "robots_blocked",
                company=company.name,
                url=careers_url,
                error=str(e),
            )
            return []

        except Exception as e:
            logger.error(
                "generic_html_fetch_error",
                company=company.name,
                url=careers_url,
                error=str(e),
            )
            return []

    def get_raw_data(self, company: Company) -> Optional[dict]:
        """Get raw HTML content from careers page."""
        careers_url = company.careers_url
        if not careers_url:
            return None

        try:
            response = self.http_client.get(careers_url)
            return {
                "url": careers_url,
                "status_code": response.status_code,
                "content_type": response.headers.get("Content-Type"),
                "html_length": len(response.text),
                "html_preview": response.text[:5000],
            }
        except Exception as e:
            logger.error("generic_html_raw_fetch_error", error=str(e))
            return None
