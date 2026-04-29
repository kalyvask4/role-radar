"""Greenhouse ATS connector."""

from datetime import datetime
from typing import Any, Optional

from role_radar.connectors.base import BaseConnector
from role_radar.models import ATSType, Company, Job, JobLocation, SalaryInfo
from role_radar.utils.http import HTTPClient
from role_radar.utils.logging import get_logger

logger = get_logger(__name__)


class GreenhouseConnector(BaseConnector):
    """Connector for Greenhouse job boards.

    Greenhouse provides a public JSON API for job boards:
    https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs

    This is an official API that doesn't require authentication for public boards.
    """

    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self, http_client: HTTPClient):
        super().__init__(http_client)

    def _get_board_url(self, board_token: str) -> str:
        """Get the API URL for a board."""
        return f"{self.BASE_URL}/{board_token}/jobs"

    def _parse_description(self, content: str) -> Optional[str]:
        """Parse and clean job description from HTML content."""
        if not content:
            return None

        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', content)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Truncate to reasonable length for display
        if len(text) > 1500:
            text = text[:1500] + "..."
        return text if text else None

    def _parse_salary(self, job_data: dict) -> Optional[SalaryInfo]:
        """Parse salary from Greenhouse job data if available."""
        import re

        min_salary = None
        max_salary = None

        # First try metadata
        metadata = job_data.get("metadata") or []
        for item in metadata:
            name = item.get("name", "").lower()
            value = item.get("value")

            if "salary" in name or "compensation" in name:
                if isinstance(value, str):
                    matches = re.findall(r'\$?([\d,]+)', value)
                    if matches:
                        numbers = [int(m.replace(",", "")) for m in matches]
                        if len(numbers) >= 2:
                            min_salary = min(numbers)
                            max_salary = max(numbers)
                        elif len(numbers) == 1:
                            min_salary = numbers[0]

        # If not in metadata, try to extract from content (pay transparency section)
        if not min_salary and not max_salary:
            content = job_data.get("content", "")
            if content:
                # Look for pay-range patterns in the HTML content
                # Common patterns: "$206,800—$258,500 USD" or "$150,000 - $200,000"
                # Greenhouse often uses class="pay-range" or class="content-pay-transparency"
                pay_patterns = [
                    r'pay-range.*?\$\s*([\d,]+).*?\$\s*([\d,]+)',  # pay-range class (greedy between)
                    r'content-pay-transparency.*?\$\s*([\d,]+).*?\$\s*([\d,]+)',  # pay transparency class
                    r'\$\s*([\d,]+)\s*[—–-]\s*\$\s*([\d,]+)',  # Direct range with various dashes
                    r'base salary.*?\$\s*([\d,]+).*?\$\s*([\d,]+)',  # "base salary" prefix
                ]
                for pattern in pay_patterns:
                    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                    if match:
                        try:
                            min_salary = int(match.group(1).replace(",", ""))
                            max_salary = int(match.group(2).replace(",", ""))
                            # Filter out unreasonable values (hourly rates or year-long dates)
                            if min_salary >= 30000 and max_salary <= 2000000:
                                break
                            else:
                                min_salary = None
                                max_salary = None
                        except (ValueError, IndexError):
                            pass

        if min_salary or max_salary:
            return SalaryInfo(
                min_salary=min_salary,
                max_salary=max_salary,
                currency="USD",
                interval="year",
                is_estimated=False,
            )

        return None

    def _parse_location(self, job_data: dict) -> JobLocation:
        """Parse location from Greenhouse job data."""
        location_data = job_data.get("location", {})

        if isinstance(location_data, str):
            raw = location_data
        else:
            raw = location_data.get("name", "")

        raw_lower = raw.lower()
        remote = "remote" in raw_lower
        hybrid = "hybrid" in raw_lower

        # Try to extract city/state
        city = None
        state = None
        country = None

        # Common patterns: "San Francisco, CA" or "San Francisco, CA, USA"
        parts = [p.strip() for p in raw.split(",")]
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
            raw_location=raw,
        )

    def _parse_job(self, job_data: dict, company: Company) -> Job:
        """Parse a single job from Greenhouse API response."""
        job_id = str(job_data.get("id", ""))
        title = job_data.get("title", "")
        location = self._parse_location(job_data)

        # Get job URL
        absolute_url = job_data.get("absolute_url", "")
        if not absolute_url:
            # Construct URL from board token
            board_token = company.ats_identifier or company.slug
            absolute_url = f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"

        # Parse posted date
        posted_date = None
        updated_at = job_data.get("updated_at")
        if updated_at:
            try:
                # Greenhouse uses ISO format
                posted_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        # Get department
        departments = job_data.get("departments", [])
        department = departments[0].get("name") if departments else None

        # Parse salary if available
        salary = self._parse_salary(job_data)

        # Extract description from content (HTML)
        description = self._parse_description(job_data.get("content", ""))

        return Job(
            id=f"{company.slug}_{job_id}",
            external_id=job_id,
            company=company.name,
            company_slug=company.slug,
            company_type=company.company_type,
            title=title,
            location=location,
            description=description,
            apply_url=absolute_url,
            posted_date=posted_date,
            department=department,
            salary=salary,
            source_ats=ATSType.GREENHOUSE,
            raw_data=job_data,
        )

    def fetch_jobs(self, company: Company) -> list[Job]:
        """Fetch jobs from Greenhouse for a company."""
        board_token = company.ats_identifier
        if not board_token:
            board_token = company.slug

        if not board_token:
            logger.warning("no_greenhouse_token", company=company.name)
            return []

        url = self._get_board_url(board_token)

        try:
            # Greenhouse API doesn't require robots.txt check as it's a public API
            data = self.http_client.get_json(url)
            jobs_data = data.get("jobs", [])

            jobs = []
            for job_data in jobs_data:
                try:
                    job = self._parse_job(job_data, company)
                    jobs.append(job)
                except Exception as e:
                    logger.warning(
                        "job_parse_error",
                        company=company.name,
                        job_id=job_data.get("id"),
                        error=str(e),
                    )

            logger.info(
                "greenhouse_jobs_fetched",
                company=company.name,
                board_token=board_token,
                job_count=len(jobs),
            )

            return jobs

        except Exception as e:
            logger.error(
                "greenhouse_fetch_error",
                company=company.name,
                board_token=board_token,
                error=str(e),
            )
            return []

    def get_raw_data(self, company: Company) -> Optional[dict]:
        """Get raw Greenhouse API response."""
        board_token = company.ats_identifier or company.slug
        if not board_token:
            return None

        url = self._get_board_url(board_token)

        try:
            return self.http_client.get_json(url)
        except Exception as e:
            logger.error("greenhouse_raw_fetch_error", error=str(e))
            return None
