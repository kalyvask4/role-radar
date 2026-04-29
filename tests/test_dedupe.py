"""Tests for job deduplication."""

import pytest

from role_radar.dedupe import (
    normalize_title,
    normalize_company,
    title_similarity,
    is_duplicate,
    deduplicate_jobs,
)
from role_radar.models import Job, JobLocation, CompanyType, ATSType


@pytest.fixture
def create_job():
    """Factory for creating test jobs."""
    def _create(
        id: str,
        title: str,
        company: str,
        apply_url: str,
        **kwargs
    ) -> Job:
        return Job(
            id=id,
            external_id=id.split("_")[-1],
            company=company,
            company_slug=company.lower().replace(" ", "-"),
            company_type=kwargs.get("company_type", CompanyType.AI_TOP_20),
            title=title,
            location=kwargs.get("location", JobLocation(raw_location="Remote")),
            apply_url=apply_url,
            description=kwargs.get("description"),
            source_ats=kwargs.get("source_ats", ATSType.GREENHOUSE),
        )
    return _create


class TestNormalizeTitle:
    def test_lowercases(self):
        assert normalize_title("Senior PM") == "senior pm"

    def test_removes_leading_numbers(self):
        assert normalize_title("1 - Product Manager") == "product manager"

    def test_removes_trailing_numbers(self):
        assert normalize_title("Product Manager - 123") == "product manager"

    def test_normalizes_abbreviations(self):
        assert normalize_title("Sr. PM") == "senior pm"

    def test_normalizes_whitespace(self):
        assert normalize_title("Product    Manager") == "product manager"


class TestNormalizeCompany:
    def test_lowercases(self):
        assert normalize_company("OpenAI") == "openai"

    def test_removes_inc(self):
        assert normalize_company("TechCorp, Inc.") == "techcorp"

    def test_removes_llc(self):
        assert normalize_company("StartupXYZ LLC") == "startupxyz"


class TestTitleSimilarity:
    def test_exact_match(self):
        assert title_similarity("Product Manager", "Product Manager") == 1.0

    def test_similar_titles(self):
        sim = title_similarity("Senior Product Manager", "Sr. Product Manager")
        assert sim > 0.8

    def test_different_titles(self):
        sim = title_similarity("Product Manager", "Software Engineer")
        assert sim < 0.5


class TestIsDuplicate:
    def test_same_url(self, create_job):
        job1 = create_job("1", "PM", "TestCo", "https://example.com/job/123")
        job2 = create_job("2", "Product Manager", "TestCo", "https://example.com/job/123")

        assert is_duplicate(job1, job2) is True

    def test_same_company_similar_title(self, create_job):
        job1 = create_job("1", "Senior Product Manager", "TestCo", "https://a.com/1")
        job2 = create_job("2", "Sr. Product Manager", "TestCo", "https://b.com/2")

        assert is_duplicate(job1, job2) is True

    def test_different_companies(self, create_job):
        job1 = create_job("1", "Product Manager", "CompanyA", "https://a.com/1")
        job2 = create_job("2", "Product Manager", "CompanyB", "https://b.com/2")

        assert is_duplicate(job1, job2) is False

    def test_same_company_different_title(self, create_job):
        job1 = create_job("1", "Product Manager, Growth", "TestCo", "https://a.com/1")
        job2 = create_job("2", "Senior PM, Infrastructure", "TestCo", "https://b.com/2")

        assert is_duplicate(job1, job2) is False


class TestDeduplicateJobs:
    def test_removes_duplicates(self, create_job):
        jobs = [
            create_job("1", "Product Manager", "TestCo", "https://example.com/1"),
            create_job("2", "Product Manager", "TestCo", "https://example.com/1"),  # Same URL
            create_job("3", "PM", "TestCo", "https://example.com/3"),  # Different
        ]

        deduped = deduplicate_jobs(jobs)
        assert len(deduped) == 2

    def test_keeps_most_complete(self, create_job):
        job1 = create_job(
            "1",
            "Product Manager",
            "TestCo",
            "https://example.com/1",
            description="Detailed job description",
        )
        job2 = create_job(
            "2",
            "Product Manager",
            "TestCo",
            "https://example.com/1",
        )

        deduped = deduplicate_jobs([job2, job1])  # job2 first, but job1 has more data
        assert len(deduped) == 1
        assert deduped[0].description == "Detailed job description"

    def test_handles_empty_list(self):
        assert deduplicate_jobs([]) == []

    def test_handles_single_job(self, create_job):
        jobs = [create_job("1", "PM", "TestCo", "https://example.com/1")]
        assert len(deduplicate_jobs(jobs)) == 1
