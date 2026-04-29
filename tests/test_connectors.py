"""Tests for job board connectors."""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

from role_radar.connectors.greenhouse import GreenhouseConnector
from role_radar.connectors.lever import LeverConnector
from role_radar.models import Company, CompanyType, ATSType


@pytest.fixture
def mock_http_client():
    return Mock()


@pytest.fixture
def sample_company():
    return Company(
        name="TestCo",
        slug="testco",
        company_type=CompanyType.AI_TOP_20,
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="testco",
    )


class TestGreenhouseConnector:
    def test_parses_jobs_from_api(self, mock_http_client, sample_company):
        # Sample Greenhouse API response
        api_response = {
            "jobs": [
                {
                    "id": 123456,
                    "title": "Senior Product Manager",
                    "location": {"name": "San Francisco, CA"},
                    "absolute_url": "https://boards.greenhouse.io/testco/jobs/123456",
                    "updated_at": "2024-01-15T10:00:00Z",
                    "departments": [{"name": "Product"}],
                },
                {
                    "id": 789012,
                    "title": "Product Manager, AI",
                    "location": {"name": "Remote"},
                    "absolute_url": "https://boards.greenhouse.io/testco/jobs/789012",
                    "updated_at": "2024-01-14T10:00:00Z",
                    "departments": [{"name": "AI Team"}],
                },
            ]
        }

        mock_http_client.get_json.return_value = api_response

        connector = GreenhouseConnector(mock_http_client)
        jobs = connector.fetch_jobs(sample_company)

        assert len(jobs) == 2
        assert jobs[0].title == "Senior Product Manager"
        assert jobs[0].company == "TestCo"
        assert jobs[0].source_ats == ATSType.GREENHOUSE
        assert "San Francisco" in jobs[0].location.raw_location
        assert jobs[1].location.remote is True

    def test_handles_empty_response(self, mock_http_client, sample_company):
        mock_http_client.get_json.return_value = {"jobs": []}

        connector = GreenhouseConnector(mock_http_client)
        jobs = connector.fetch_jobs(sample_company)

        assert jobs == []

    def test_handles_api_error(self, mock_http_client, sample_company):
        mock_http_client.get_json.side_effect = Exception("API Error")

        connector = GreenhouseConnector(mock_http_client)
        jobs = connector.fetch_jobs(sample_company)

        assert jobs == []


class TestLeverConnector:
    def test_parses_postings_from_api(self, mock_http_client):
        company = Company(
            name="LeverCo",
            slug="leverco",
            company_type=CompanyType.VC_BACKED,
            ats_type=ATSType.LEVER,
            ats_identifier="leverco",
        )

        # Sample Lever API response
        api_response = [
            {
                "id": "abc123",
                "text": "Product Manager",
                "categories": {
                    "location": "San Francisco, CA",
                    "team": "Product",
                },
                "hostedUrl": "https://jobs.lever.co/leverco/abc123",
                "applyUrl": "https://jobs.lever.co/leverco/abc123/apply",
                "createdAt": 1705312800000,  # 2024-01-15
            },
        ]

        mock_http_client.get_json.return_value = api_response

        connector = LeverConnector(mock_http_client)
        jobs = connector.fetch_jobs(company)

        assert len(jobs) == 1
        assert jobs[0].title == "Product Manager"
        assert jobs[0].source_ats == ATSType.LEVER
        assert jobs[0].department == "Product"

    def test_handles_remote_jobs(self, mock_http_client):
        company = Company(
            name="LeverCo",
            slug="leverco",
            company_type=CompanyType.VC_BACKED,
            ats_type=ATSType.LEVER,
            ats_identifier="leverco",
        )

        api_response = [
            {
                "id": "def456",
                "text": "Senior PM",
                "categories": {
                    "location": "Remote - US",
                    "commitment": "Full-time, Remote",
                },
                "hostedUrl": "https://jobs.lever.co/leverco/def456",
            },
        ]

        mock_http_client.get_json.return_value = api_response

        connector = LeverConnector(mock_http_client)
        jobs = connector.fetch_jobs(company)

        assert len(jobs) == 1
        assert "remote" in jobs[0].location.raw_location.lower()
