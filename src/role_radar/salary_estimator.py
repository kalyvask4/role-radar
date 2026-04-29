"""Salary estimation for PM roles based on company type, seniority, and location."""

from role_radar.models import CompanyType, Job, SalaryInfo


# Salary ranges for PM roles at top tech/AI companies (2024/2025 data)
# Based on levels.fyi, Glassdoor, and LinkedIn salary data
PM_SALARY_RANGES = {
    # Frontier AI Labs - Top tier compensation
    "frontier_lab": {
        "APM": (130000, 180000),
        "PM": (180000, 250000),
        "Senior PM": (250000, 350000),
        "Staff PM": (350000, 450000),
        "Principal PM": (400000, 500000),
        "Group PM": (400000, 550000),
        "Director": (450000, 600000),
        "VP": (550000, 800000),
    },
    # Top AI/Tech companies - Very competitive
    "ai_top_20": {
        "APM": (120000, 160000),
        "PM": (160000, 220000),
        "Senior PM": (220000, 300000),
        "Staff PM": (300000, 400000),
        "Principal PM": (350000, 450000),
        "Group PM": (350000, 450000),
        "Director": (400000, 550000),
        "VP": (500000, 700000),
    },
    # Well-funded VC-backed startups - Competitive with equity
    "vc_backed": {
        "APM": (110000, 150000),
        "PM": (140000, 190000),
        "Senior PM": (180000, 260000),
        "Staff PM": (250000, 350000),
        "Principal PM": (300000, 400000),
        "Group PM": (300000, 400000),
        "Director": (350000, 500000),
        "VP": (450000, 650000),
    },
    # Standard tech
    "standard": {
        "APM": (100000, 130000),
        "PM": (120000, 160000),
        "Senior PM": (150000, 220000),
        "Staff PM": (200000, 300000),
        "Principal PM": (250000, 350000),
        "Group PM": (250000, 350000),
        "Director": (300000, 420000),
        "VP": (400000, 550000),
    },
}

# Frontier AI labs for premium salary estimates
FRONTIER_LABS = {
    "anthropic", "openai", "google deepmind", "deepmind", "meta ai",
    "xai", "mistral", "cohere", "ai21 labs", "inflection",
}

# Location adjustments (SF Bay Area = 1.0)
LOCATION_MULTIPLIERS = {
    "sf_bay_area": 1.0,
    "nyc": 0.95,
    "seattle": 0.90,
    "la": 0.85,
    "austin": 0.80,
    "denver": 0.75,
    "remote_us": 0.85,
    "remote": 0.80,
    "international": 0.70,
}


def detect_seniority_from_title(title: str) -> str:
    """Detect seniority level from job title."""
    title_lower = title.lower()

    # Check for specific levels
    if "vp" in title_lower or "vice president" in title_lower:
        return "VP"
    if "director" in title_lower or "head of" in title_lower:
        return "Director"
    if "group" in title_lower:
        return "Group PM"
    if "principal" in title_lower:
        return "Principal PM"
    if "staff" in title_lower:
        return "Staff PM"
    if "senior" in title_lower or "sr." in title_lower or "sr " in title_lower:
        return "Senior PM"
    if "associate" in title_lower or "apm" in title_lower:
        return "APM"

    # Default to mid-level PM
    return "PM"


def get_location_multiplier(job: Job) -> float:
    """Get location-based salary multiplier."""
    if job.location.remote:
        if job.location.country and job.location.country.lower() != "usa":
            return LOCATION_MULTIPLIERS["international"]
        return LOCATION_MULTIPLIERS["remote_us"]

    if job.location.is_sf_bay_area():
        return LOCATION_MULTIPLIERS["sf_bay_area"]

    location_lower = job.location.raw_location.lower()

    if "new york" in location_lower or "nyc" in location_lower:
        return LOCATION_MULTIPLIERS["nyc"]
    if "seattle" in location_lower:
        return LOCATION_MULTIPLIERS["seattle"]
    if "los angeles" in location_lower:
        return LOCATION_MULTIPLIERS["la"]
    if "austin" in location_lower or "texas" in location_lower:
        return LOCATION_MULTIPLIERS["austin"]
    if "denver" in location_lower or "colorado" in location_lower:
        return LOCATION_MULTIPLIERS["denver"]

    # Default to slightly lower for unknown US locations
    return 0.85


def estimate_salary(job: Job) -> SalaryInfo:
    """Estimate salary for a job based on company type, title, and location."""
    # Detect seniority
    seniority = job.seniority or detect_seniority_from_title(job.title)

    # Determine salary tier
    company_lower = job.company.lower()

    if company_lower in FRONTIER_LABS:
        tier = "frontier_lab"
    elif job.company_type == CompanyType.AI_TOP_20:
        tier = "ai_top_20"
    elif job.company_type == CompanyType.VC_BACKED:
        tier = "vc_backed"
    else:
        tier = "standard"

    # Get base salary range
    salary_table = PM_SALARY_RANGES.get(tier, PM_SALARY_RANGES["standard"])
    min_salary, max_salary = salary_table.get(seniority, salary_table["PM"])

    # Apply location multiplier
    location_mult = get_location_multiplier(job)
    min_salary = int(min_salary * location_mult)
    max_salary = int(max_salary * location_mult)

    return SalaryInfo(
        min_salary=min_salary,
        max_salary=max_salary,
        currency="USD",
        interval="year",
        is_estimated=True,
    )


def get_salary_for_job(job: Job) -> SalaryInfo:
    """Get salary for a job - use actual if available, otherwise estimate."""
    if job.salary and (job.salary.min_salary or job.salary.max_salary):
        return job.salary

    return estimate_salary(job)
