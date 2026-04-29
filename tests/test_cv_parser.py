"""Tests for CV parser module."""

import pytest
from pathlib import Path
import tempfile

from role_radar.cv_parser import (
    extract_skills,
    extract_domains,
    extract_titles,
    detect_seniority,
    parse_cv,
)


class TestExtractSkills:
    def test_extracts_technical_skills(self):
        text = "Experienced with SQL, Python, and machine learning"
        skills = extract_skills(text)
        assert "sql" in skills
        assert "python" in skills
        assert "machine learning" in skills

    def test_extracts_product_skills(self):
        text = "Led product roadmap development using agile methodologies with Jira"
        skills = extract_skills(text)
        assert "roadmap" in skills
        assert "agile" in skills
        assert "jira" in skills

    def test_extracts_ai_skills(self):
        text = "Built LLM applications using GPT and transformers"
        skills = extract_skills(text)
        assert "llm" in skills
        assert "gpt" in skills
        assert "transformers" in skills

    def test_handles_empty_text(self):
        skills = extract_skills("")
        assert skills == []

    def test_deduplicates_skills(self):
        text = "SQL expert. Also uses SQL for analytics. SQL is great."
        skills = extract_skills(text)
        assert skills.count("sql") == 1


class TestExtractDomains:
    def test_extracts_ai_ml_domain(self):
        text = "Worked on machine learning products and AI applications"
        domains = extract_domains(text)
        assert "ai/ml" in domains

    def test_extracts_infrastructure_domain(self):
        text = "Built cloud infrastructure on AWS with kubernetes"
        domains = extract_domains(text)
        assert "infrastructure" in domains

    def test_extracts_fintech_domain(self):
        text = "Led payments products in fintech startup"
        domains = extract_domains(text)
        assert "fintech" in domains

    def test_extracts_multiple_domains(self):
        text = "Built B2B SaaS products for fintech companies using ML"
        domains = extract_domains(text)
        assert len(domains) >= 2


class TestExtractTitles:
    def test_extracts_pm_titles(self):
        text = """
        Senior Product Manager at TechCorp
        Product Manager at StartupXYZ
        """
        recent, all_titles = extract_titles(text)
        assert len(all_titles) >= 2
        assert any("senior product manager" in t.lower() for t in all_titles)

    def test_extracts_technical_pm_title(self):
        text = "Technical Product Manager - AI Platform"
        recent, all_titles = extract_titles(text)
        assert any("technical product manager" in t.lower() for t in all_titles)

    def test_handles_no_titles(self):
        text = "Just some random text without any job titles"
        recent, all_titles = extract_titles(text)
        assert len(all_titles) == 0


class TestDetectSeniority:
    def test_detects_senior_pm(self):
        assert detect_seniority(["Senior Product Manager"]) == "Senior PM"
        assert detect_seniority(["Sr. PM at TechCorp"]) == "Senior PM"

    def test_detects_apm(self):
        assert detect_seniority(["Associate Product Manager"]) == "APM"
        assert detect_seniority(["APM - Growth Team"]) == "APM"

    def test_detects_group_pm(self):
        assert detect_seniority(["Group Product Manager"]) == "Group PM"

    def test_detects_director(self):
        assert detect_seniority(["Director of Product"]) == "Director"

    def test_detects_vp(self):
        assert detect_seniority(["VP of Product"]) == "VP"
        assert detect_seniority(["Vice President, Product"]) == "VP"

    def test_returns_none_for_no_match(self):
        assert detect_seniority(["Software Engineer"]) is None


class TestParseCv:
    def test_parses_text_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("""
            John Doe
            Senior Product Manager

            Experience:
            - Senior PM at TechCorp (2020-Present)
            - PM at StartupXYZ (2018-2020)

            Skills:
            - SQL, Python, Data Analysis
            - Product Roadmap, Agile, Jira
            - Machine Learning, AI
            """)
            f.flush()
            path = Path(f.name)

        try:
            signals = parse_cv(path)

            assert signals.raw_text
            assert len(signals.skills) > 0
            assert "sql" in signals.skills
            assert signals.inferred_seniority == "Senior PM"
        finally:
            path.unlink()

    def test_extracts_years_experience_from_text(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("I have 8+ years of product management experience")
            f.flush()
            path = Path(f.name)

        try:
            signals = parse_cv(path)
            assert signals.years_experience == 8
        finally:
            path.unlink()
