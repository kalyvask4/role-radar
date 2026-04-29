"""Ashby ATS connector."""

from datetime import datetime
from typing import Optional

from role_radar.connectors.base import BaseConnector
from role_radar.models import ATSType, Company, Job, JobLocation, SalaryInfo
from role_radar.utils.http import HTTPClient
from role_radar.utils.logging import get_logger

logger = get_logger(__name__)


class AshbyConnector(BaseConnector):
    """Connector for Ashby job boards.

    Ashby provides a public posting API:
    https://api.ashbyhq.com/posting-api/job-board/{company}

    This is an official API that doesn't require authentication for public postings.
    """

    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"

    def __init__(self, http_client: HTTPClient):
        super().__init__(http_client)

    def _get_postings_url(self, company_slug: str) -> str:
        """Get the API URL for a company's postings."""
        return f"{self.BASE_URL}/{company_slug}"

    def _parse_description(self, job_data: dict) -> Optional[str]:
        """Parse and clean job description from Ashby job data."""
        import re
        # Ashby provides description field
        description = job_data.get("description", "") or job_data.get("descriptionHtml", "")

        if not description:
            return None

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', description)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > 1500:
            text = text[:1500] + "..."

        return text if text else None

    def _parse_salary(self, job_data: dict) -> Optional[SalaryInfo]:
        """Parse salary from Ashby job data if available."""
        # Ashby can include compensation info
        compensation = job_data.get("compensation", {})

        if not compensation:
            # Try to extract from description
            return None

        min_salary = compensation.get("min")
        max_salary = compensation.get("max")
        currency = compensation.get("currency", "USD")

        if min_salary or max_salary:
            return SalaryInfo(
                min_salary=int(min_salary) if min_salary else None,
                max_salary=int(max_salary) if max_salary else None,
                currency=currency,
                interval="year",
                is_estimated=False,
            )

        return None

    def _parse_location(self, job_data: dict) -> JobLocation:
        """Parse location from Ashby job data."""
        location = job_data.get("location", "")

        if not location:
            # Check for locationType
            location_type = job_data.get("locationTypes", [])
            if location_type:
                if "Remote" in location_type:
                    return JobLocation(remote=True, raw_location="Remote")
            return JobLocation(raw_location="Location not specified")

        raw_lower = location.lower()
        remote = "remote" in raw_lower
        hybrid = "hybrid" in raw_lower

        # Try to extract city/state
        city = None
        state = None
        country = None

        parts = [p.strip() for p in location.split(",")]
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
            raw_location=location,
        )

    def _parse_job(self, job_data: dict, company: Company) -> Job:
        """Parse a single job from Ashby API response."""
        job_id = job_data.get("id", "")
        title = job_data.get("title", "")
        location = self._parse_location(job_data)

        # Get apply URL - Ashby uses jobUrl
        apply_url = job_data.get("jobUrl", "")
        if not apply_url:
            # Fall back to constructing the URL
            company_slug = company.ats_identifier or company.slug
            apply_url = f"https://jobs.ashbyhq.com/{company_slug}/{job_id}"

        # Parse posted date
        posted_date = None
        published_at = job_data.get("publishedAt")
        if published_at:
            try:
                # Ashby uses ISO format
                posted_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Get department/team
        department = job_data.get("department", "")
        if not department:
            team = job_data.get("team", {})
            if isinstance(team, dict):
                department = team.get("name", "")

        # Get employment type
        employment_type = job_data.get("employmentType", "")

        # Parse salary if available
        salary = self._parse_salary(job_data)

        # Parse description
        description = self._parse_description(job_data)

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
            employment_type=employment_type if employment_type else None,
            salary=salary,
            source_ats=ATSType.ASHBY,
            raw_data=job_data,
        )

    def fetch_jobs(self, company: Company) -> list[Job]:
        """Fetch jobs from Ashby for a company."""
        company_slug = company.ats_identifier or company.slug

        if not company_slug:
            logger.warning("no_ashby_slug", company=company.name)
            return []

        url = self._get_postings_url(company_slug)

        try:
            # Ashby API is a public API - skip robots.txt check
            response = self.http_client.get_json(url, skip_robots_check=True)

            # Handle both array response and object with jobs key
            if isinstance(response, list):
                postings = response
            elif isinstance(response, dict):
                postings = response.get("jobs", [])
            else:
                logger.warning("unexpected_ashby_response", company=company.name)
                return []

            jobs = []
            for posting in postings:
                try:
                    job = self._parse_job(posting, company)
                    jobs.append(job)
                except Exception as e:
                    logger.warning(
                        "ashby_job_parse_error",
                        company=company.name,
                        job_id=posting.get("id"),
                        error=str(e),
                    )

            logger.info(
                "ashby_jobs_fetched",
                company=company.name,
                company_slug=company_slug,
                job_count=len(jobs),
            )

            return jobs

        except Exception as e:
            logger.error(
                "ashby_fetch_error",
                company=company.name,
                company_slug=company_slug,
                error=str(e),
            )
            return []

    def get_raw_data(self, company: Company) -> Optional[dict]:
        """Get raw Ashby API response."""
        company_slug = company.ats_identifier or company.slug
        if not company_slug:
            return None

        url = self._get_postings_url(company_slug)

        try:
            data = self.http_client.get_json(url, skip_robots_check=True)
            if isinstance(data, list):
                return {"jobs": data}
            return data
        except Exception as e:
            logger.error("ashby_raw_fetch_error", error=str(e))
            return None
