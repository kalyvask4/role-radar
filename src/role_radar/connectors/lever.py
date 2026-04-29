"""Lever ATS connector."""

from datetime import datetime
from typing import Optional

from role_radar.connectors.base import BaseConnector
from role_radar.models import ATSType, Company, Job, JobLocation, SalaryInfo
from role_radar.utils.http import HTTPClient
from role_radar.utils.logging import get_logger

logger = get_logger(__name__)


class LeverConnector(BaseConnector):
    """Connector for Lever job boards.

    Lever provides a public posting API:
    https://api.lever.co/v0/postings/{company}

    This is an official API that doesn't require authentication for public postings.
    """

    BASE_URL = "https://api.lever.co/v0/postings"

    def __init__(self, http_client: HTTPClient):
        super().__init__(http_client)

    def _get_postings_url(self, company_slug: str) -> str:
        """Get the API URL for a company's postings."""
        return f"{self.BASE_URL}/{company_slug}"

    def _parse_description(self, posting: dict) -> Optional[str]:
        """Parse and clean job description from Lever posting."""
        import re
        # Lever provides description in lists array with type "list"
        lists = posting.get("lists", [])
        description_parts = []

        for item in lists:
            text = item.get("text", "")
            content = item.get("content", "")
            if text:
                description_parts.append(text)
            if content:
                # Remove HTML tags
                clean = re.sub(r'<[^>]+>', ' ', content)
                description_parts.append(clean)

        # Also check descriptionPlain field
        plain = posting.get("descriptionPlain", "")
        if plain:
            description_parts.append(plain)

        text = " ".join(description_parts)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > 1500:
            text = text[:1500] + "..."

        return text if text else None

    def _parse_salary(self, posting: dict) -> Optional[SalaryInfo]:
        """Parse salary from Lever posting data if available."""
        # Lever can include salary ranges in posting
        salary_range = posting.get("salaryRange", {})

        if not salary_range:
            # Check in compensation/description fields
            return None

        min_salary = salary_range.get("min")
        max_salary = salary_range.get("max")
        currency = salary_range.get("currency", "USD")
        interval = salary_range.get("interval", "per-year-salary")

        if min_salary or max_salary:
            return SalaryInfo(
                min_salary=int(min_salary) if min_salary else None,
                max_salary=int(max_salary) if max_salary else None,
                currency=currency,
                interval="year" if "year" in interval else "hour",
                is_estimated=False,
            )

        return None

    def _parse_location(self, posting: dict) -> JobLocation:
        """Parse location from Lever posting data."""
        # Lever uses categories.location
        categories = posting.get("categories", {})
        location_str = categories.get("location", "")

        if not location_str:
            # Check for workplaceType
            workplace = categories.get("commitment", "")
            if "remote" in workplace.lower():
                return JobLocation(remote=True, raw_location="Remote")
            return JobLocation(raw_location="Location not specified")

        raw_lower = location_str.lower()
        remote = "remote" in raw_lower
        hybrid = "hybrid" in raw_lower

        # Try to extract city/state
        city = None
        state = None
        country = None

        parts = [p.strip() for p in location_str.split(",")]
        if len(parts) >= 1:
            city = parts[0]
        if len(parts) >= 2:
            state = parts[1]
        if len(parts) >= 3:
            country = parts[2]

        return JobLocation(
            city=city,
            state=state,
            country=country,
            remote=remote,
            hybrid=hybrid,
            raw_location=location_str,
        )

    def _parse_job(self, posting: dict, company: Company) -> Job:
        """Parse a single job from Lever API response."""
        job_id = posting.get("id", "")
        title = posting.get("text", "")
        location = self._parse_location(posting)

        # Get apply URL
        apply_url = posting.get("applyUrl", "")
        if not apply_url:
            apply_url = posting.get("hostedUrl", "")

        # Parse posted date
        posted_date = None
        created_at = posting.get("createdAt")
        if created_at:
            try:
                # Lever uses milliseconds since epoch
                posted_date = datetime.fromtimestamp(created_at / 1000)
            except (ValueError, TypeError):
                pass

        # Get department/team
        categories = posting.get("categories", {})
        department = categories.get("team", categories.get("department"))

        # Get employment type
        commitment = categories.get("commitment", "")

        # Parse salary if available
        salary = self._parse_salary(posting)

        # Parse description
        description = self._parse_description(posting)

        return Job(
            id=f"{company.slug}_{job_id}",
            external_id=job_id,
            company=company.name,
            company_slug=company.slug,
            company_type=company.company_type,
            title=title,
            location=location,
            description=description,
            apply_url=apply_url,
            posted_date=posted_date,
            department=department,
            employment_type=commitment if commitment else None,
            salary=salary,
            source_ats=ATSType.LEVER,
            raw_data=posting,
        )

    def fetch_jobs(self, company: Company) -> list[Job]:
        """Fetch jobs from Lever for a company."""
        company_slug = company.ats_identifier or company.slug

        if not company_slug:
            logger.warning("no_lever_slug", company=company.name)
            return []

        url = self._get_postings_url(company_slug)

        try:
            # Lever API is a public API
            postings = self.http_client.get_json(url)

            if not isinstance(postings, list):
                logger.warning("unexpected_lever_response", company=company.name)
                return []

            jobs = []
            for posting in postings:
                try:
                    job = self._parse_job(posting, company)
                    jobs.append(job)
                except Exception as e:
                    logger.warning(
                        "lever_job_parse_error",
                        company=company.name,
                        job_id=posting.get("id"),
                        error=str(e),
                    )

            logger.info(
                "lever_jobs_fetched",
                company=company.name,
                company_slug=company_slug,
                job_count=len(jobs),
            )

            return jobs

        except Exception as e:
            logger.error(
                "lever_fetch_error",
                company=company.name,
                company_slug=company_slug,
                error=str(e),
            )
            return []

    def get_raw_data(self, company: Company) -> Optional[dict]:
        """Get raw Lever API response."""
        company_slug = company.ats_identifier or company.slug
        if not company_slug:
            return None

        url = self._get_postings_url(company_slug)

        try:
            data = self.http_client.get_json(url)
            return {"postings": data}
        except Exception as e:
            logger.error("lever_raw_fetch_error", error=str(e))
            return None
