"""Base connector interface."""

from abc import ABC, abstractmethod
from typing import Optional

from role_radar.models import Company, Job
from role_radar.utils.http import HTTPClient


class BaseConnector(ABC):
    """Base class for job board connectors."""

    def __init__(self, http_client: HTTPClient):
        self.http_client = http_client

    @abstractmethod
    def fetch_jobs(self, company: Company) -> list[Job]:
        """Fetch jobs from the job board for a company.

        Args:
            company: Company to fetch jobs for

        Returns:
            List of Job objects
        """
        pass

    @abstractmethod
    def get_raw_data(self, company: Company) -> Optional[dict]:
        """Get raw data from the job board for debugging.

        Args:
            company: Company to fetch raw data for

        Returns:
            Raw API/page response data or None
        """
        pass
