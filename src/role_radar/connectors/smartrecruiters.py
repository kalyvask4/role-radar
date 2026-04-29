"""SmartRecruiters ATS connector."""

from datetime import datetime
from typing import Optional

from role_radar.connectors.base import BaseConnector
from role_radar.models import ATSType, Company, Job, JobLocation
from role_radar.utils.http import HTTPClient
from role_radar.utils.logging import get_logger

logger = get_logger(__name__)


class SmartRecruitersConnector(BaseConnector):
    """Connector for SmartRecruiters job boards.

    SmartRecruiters provides a public job API:
    https://api.smartrecruiters.com/v1/companies/{company}/postings

    This is an official API that doesn't require authentication for public postings.
    """

    BASE_URL = "https://api.smartrecruiters.com/v1/companies"

    def __init__(self, http_client: HTTPClient):
        super().__init__(http_client)

    def _get_postings_url(self, company_id: str) -> str:
        """Get the API URL for a company's postings."""
        return f"{self.BASE_URL}/{company_id}/postings"

    def _parse_location(self, posting: dict) -> JobLocation:
        """Parse location from SmartRecruiters posting data."""
        location = posting.get("location", {})

        city = location.get("city", "")
        region = location.get("region", "")
        country = location.get("country", "")
        remote = location.get("remote", False)

        # SmartRecruiters also has a customField for remote/hybrid
        custom_fields = posting.get("customField", [])
        for field in custom_fields:
            if field.get("fieldLabel", "").lower() in ["work location", "workplace type"]:
                value = field.get("valueLabel", "").lower()
                if "remote" in value:
                    remote = True
                if "hybrid" in value:
                    return JobLocation(
                        city=city,
                        state=region,
                        country=country,
                        remote=remote,
                        hybrid=True,
                        raw_location=f"{city}, {region}".strip(", "),
                    )

        raw_parts = [p for p in [city, region, country] if p]
        raw_location = ", ".join(raw_parts) if raw_parts else "Location not specified"

        return JobLocation(
            city=city if city else None,
            state=region if region else None,
            country=country if country else None,
            remote=remote,
            hybrid=False,
            raw_location=raw_location,
        )

    def _parse_job(self, posting: dict, company: Company) -> Job:
        """Parse a single job from SmartRecruiters API response."""
        job_id = posting.get("id", "") or posting.get("uuid", "")
        title = posting.get("name", "")
        location = self._parse_location(posting)

        # Get apply URL
        ref = posting.get("ref", "")
        apply_url = posting.get("applyUrl", ref)

        # Parse posted date
        posted_date = None
        released_date = posting.get("releasedDate")
        if released_date:
            try:
                posted_date = datetime.fromisoformat(released_date.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        # Get department
        department_data = posting.get("department", {})
        department = department_data.get("label") if isinstance(department_data, dict) else None

        # Get employment type
        type_of_employment = posting.get("typeOfEmployment", {})
        employment_type = type_of_employment.get("label") if isinstance(type_of_employment, dict) else None

        # Get experience level (seniority proxy)
        experience_level = posting.get("experienceLevel", {})
        seniority = experience_level.get("label") if isinstance(experience_level, dict) else None

        return Job(
            id=f"{company.slug}_{job_id}",
            external_id=str(job_id),
            company=company.name,
            company_slug=company.slug,
            company_type=company.company_type,
            title=title,
            location=location,
            apply_url=apply_url,
            posted_date=posted_date,
            department=department,
            employment_type=employment_type,
            seniority=seniority,
            source_ats=ATSType.SMARTRECRUITERS,
            raw_data=posting,
        )

    def fetch_jobs(self, company: Company) -> list[Job]:
        """Fetch jobs from SmartRecruiters for a company."""
        company_id = company.ats_identifier or company.slug

        if not company_id:
            logger.warning("no_smartrecruiters_id", company=company.name)
            return []

        url = self._get_postings_url(company_id)
        all_jobs = []

        try:
            # SmartRecruiters API is paginated
            offset = 0
            limit = 100

            while True:
                params = {"offset": offset, "limit": limit}
                data = self.http_client.get_json(url, params=params)

                content = data.get("content", [])
                if not content:
                    break

                for posting in content:
                    try:
                        job = self._parse_job(posting, company)
                        all_jobs.append(job)
                    except Exception as e:
                        logger.warning(
                            "smartrecruiters_job_parse_error",
                            company=company.name,
                            job_id=posting.get("id"),
                            error=str(e),
                        )

                # Check if there are more pages
                total_found = data.get("totalFound", 0)
                offset += limit
                if offset >= total_found:
                    break

            logger.info(
                "smartrecruiters_jobs_fetched",
                company=company.name,
                company_id=company_id,
                job_count=len(all_jobs),
            )

            return all_jobs

        except Exception as e:
            logger.error(
                "smartrecruiters_fetch_error",
                company=company.name,
                company_id=company_id,
                error=str(e),
            )
            return []

    def get_raw_data(self, company: Company) -> Optional[dict]:
        """Get raw SmartRecruiters API response."""
        company_id = company.ats_identifier or company.slug
        if not company_id:
            return None

        url = self._get_postings_url(company_id)

        try:
            return self.http_client.get_json(url)
        except Exception as e:
            logger.error("smartrecruiters_raw_fetch_error", error=str(e))
            return None
