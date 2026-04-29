"""VC Portfolio company discovery and management."""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from role_radar.models import ATSType, Company, CompanyType
from role_radar.company_sources.top_vcs import TOP_VCS, VCData
from role_radar.utils.http import HTTPClient
from role_radar.utils.logging import get_logger

logger = get_logger(__name__)


# Known ATS mappings for popular companies
# Format: company_name_lower -> (ATSType, ats_identifier)
KNOWN_COMPANY_ATS = {
    # Greenhouse companies (verified)
    "anthropic": (ATSType.GREENHOUSE, "anthropic"),
    "scale ai": (ATSType.GREENHOUSE, "scaleai"),
    "figma": (ATSType.GREENHOUSE, "figma"),
    "plaid": (ATSType.GREENHOUSE, "plaid"),
    "stripe": (ATSType.GREENHOUSE, "stripe"),
    "rippling": (ATSType.GREENHOUSE, "rippling"),
    "brex": (ATSType.GREENHOUSE, "brex"),
    "ramp": (ATSType.GREENHOUSE, "ramp"),
    "retool": (ATSType.GREENHOUSE, "retool"),
    "linear": (ATSType.GREENHOUSE, "linear"),
    "vercel": (ATSType.GREENHOUSE, "vercel"),
    "replit": (ATSType.GREENHOUSE, "replit"),
    "runway": (ATSType.GREENHOUSE, "runwayml"),
    "elevenlabs": (ATSType.GREENHOUSE, "elevenlabs"),
    "perplexity": (ATSType.GREENHOUSE, "perplexityai"),
    "character.ai": (ATSType.GREENHOUSE, "characterai"),
    "glean": (ATSType.GREENHOUSE, "gleanwork"),
    "harvey": (ATSType.GREENHOUSE, "harvey"),
    "descript": (ATSType.GREENHOUSE, "descript"),
    "stability ai": (ATSType.GREENHOUSE, "stabilityai"),
    "hugging face": (ATSType.GREENHOUSE, "huggingface"),
    "langchain": (ATSType.GREENHOUSE, "langchain"),
    "weights & biases": (ATSType.GREENHOUSE, "wandb"),
    "weaviate": (ATSType.GREENHOUSE, "weaviate"),
    "neon": (ATSType.GREENHOUSE, "neondatabase"),
    "supabase": (ATSType.GREENHOUSE, "supabase"),
    "modal": (ATSType.GREENHOUSE, "modal"),
    "together ai": (ATSType.GREENHOUSE, "togetherai"),
    "sierra": (ATSType.GREENHOUSE, "sierra"),
    "suno": (ATSType.GREENHOUSE, "suno"),
    "photoroom": (ATSType.GREENHOUSE, "photoroom"),
    "writer": (ATSType.GREENHOUSE, "writer"),
    "jasper": (ATSType.GREENHOUSE, "jasper"),
    "copy.ai": (ATSType.GREENHOUSE, "copyai"),
    "synthesia": (ATSType.GREENHOUSE, "synthesia"),
    "adept": (ATSType.GREENHOUSE, "adept"),
    "cohere": (ATSType.GREENHOUSE, "cohere"),
    "inflection": (ATSType.GREENHOUSE, "inflectionai"),
    "ada": (ATSType.GREENHOUSE, "ada"),
    "clerk": (ATSType.GREENHOUSE, "clerkdev"),
    "webflow": (ATSType.GREENHOUSE, "webflow"),
    "flexport": (ATSType.GREENHOUSE, "flexport"),
    "airtable": (ATSType.GREENHOUSE, "airtable"),
    "mercury": (ATSType.GREENHOUSE, "mercury"),
    "warp": (ATSType.GREENHOUSE, "warp"),
    "veed": (ATSType.GREENHOUSE, "veed"),
    "gamma": (ATSType.GREENHOUSE, "gamma"),
    "11x": (ATSType.GREENHOUSE, "11x"),
    "metaview": (ATSType.GREENHOUSE, "metaview"),
    "midjourney": (ATSType.GREENHOUSE, "midjourney"),
    "ideogram": (ATSType.GREENHOUSE, "ideogram"),
    "luma ai": (ATSType.GREENHOUSE, "lumalabs"),

    # Lever companies
    "databricks": (ATSType.LEVER, "databricks"),
    "anyscale": (ATSType.LEVER, "anyscale"),
    "canva": (ATSType.LEVER, "canva"),

    # More Greenhouse companies (verified)
    "cerebras": (ATSType.GREENHOUSE, "cerebrassystems"),
    "coreweave": (ATSType.GREENHOUSE, "coreweave"),
    "hebbia": (ATSType.GREENHOUSE, "hebbia"),
    "labelbox": (ATSType.GREENHOUSE, "labelbox"),
    "contextual ai": (ATSType.GREENHOUSE, "contextualai"),
    "fireworks ai": (ATSType.GREENHOUSE, "fireworksai"),
    "harmonic": (ATSType.GREENHOUSE, "harmonic"),

    # Lever companies (verified)
    "databricks": (ATSType.LEVER, "databricks"),
    "anyscale": (ATSType.LEVER, "anyscale"),
    "canva": (ATSType.LEVER, "canva"),
    "imbue": (ATSType.LEVER, "imbue"),
    "encord": (ATSType.LEVER, "CordTechnologies"),

    # Ashby companies (verified)
    "lovable": (ATSType.ASHBY, "lovable"),
    "chroma": (ATSType.ASHBY, "chroma"),
    "clay": (ATSType.ASHBY, "claylabs"),
    "cognition": (ATSType.ASHBY, "cognition"),
    "pika": (ATSType.ASHBY, "pika"),
    "cursor": (ATSType.ASHBY, "cursor"),
    "notion": (ATSType.ASHBY, "notion"),
    "pinecone": (ATSType.ASHBY, "pinecone"),
    "openai": (ATSType.ASHBY, "openai"),
    "distyl ai": (ATSType.ASHBY, "Distyl"),
    "reka": (ATSType.ASHBY, "Reka"),
    "reka ai": (ATSType.ASHBY, "Reka"),
    "abridge": (ATSType.ASHBY, "abridge"),
    "assembled": (ATSType.ASHBY, "assembledhq"),
    "baseten": (ATSType.ASHBY, "baseten"),
    "windsurf": (ATSType.ASHBY, "Windsurf"),
    "codeium": (ATSType.ASHBY, "Windsurf"),
    "ramp": (ATSType.ASHBY, "ramp"),
    "sierra": (ATSType.ASHBY, "sierra"),
    "sierra ai": (ATSType.ASHBY, "sierra"),
}


@dataclass
class PortfolioCompany:
    """A company from a VC portfolio."""
    name: str
    homepage: Optional[str] = None
    careers_url: Optional[str] = None
    backed_by: list[str] = field(default_factory=list)
    ats_type: ATSType = ATSType.UNKNOWN
    ats_identifier: Optional[str] = None
    notes: Optional[str] = None


# Common patterns for detecting ATS from careers page URLs
ATS_PATTERNS = {
    ATSType.GREENHOUSE: [
        r"boards\.greenhouse\.io/(\w+)",
        r"job-boards\.greenhouse\.io/(\w+)",
        r"greenhouse\.io",
    ],
    ATSType.LEVER: [
        r"jobs\.lever\.co/(\w+)",
        r"lever\.co",
    ],
    ATSType.ASHBY: [
        r"jobs\.ashbyhq\.com/(\w+)",
        r"ashbyhq\.com",
    ],
    ATSType.SMARTRECRUITERS: [
        r"jobs\.smartrecruiters\.com/(\w+)",
        r"smartrecruiters\.com",
    ],
    ATSType.WORKDAY: [
        r"(\w+)\.wd\d+\.myworkdayjobs\.com",
        r"myworkdayjobs\.com",
        r"workday\.com",
    ],
    ATSType.BAMBOOHR: [
        r"(\w+)\.bamboohr\.com/jobs",
        r"bamboohr\.com",
    ],
}


def detect_ats_from_url(url: str) -> tuple[ATSType, Optional[str]]:
    """Detect ATS type and identifier from a URL.

    Returns (ats_type, identifier).
    """
    if not url:
        return ATSType.UNKNOWN, None

    url_lower = url.lower()

    for ats_type, patterns in ATS_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, url_lower)
            if match:
                identifier = match.group(1) if match.lastindex else None
                return ats_type, identifier

    return ATSType.GENERIC_HTML, None


class PortfolioManager:
    """Manages portfolio companies from VCs and user CSV."""

    def __init__(
        self,
        http_client: HTTPClient,
        cache_dir: Path,
        csv_path: Optional[Path] = None,
    ):
        self.http_client = http_client
        self.cache_dir = cache_dir
        self.csv_path = csv_path
        self.companies: dict[str, PortfolioCompany] = {}

    def load_from_csv(self) -> list[PortfolioCompany]:
        """Load portfolio companies from user-maintained CSV."""
        if not self.csv_path or not self.csv_path.exists():
            logger.debug("no_portfolio_csv", path=str(self.csv_path))
            return []

        companies = []
        try:
            with open(self.csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Skip comments and empty rows
                    if not row or row.get("company_name", "").startswith("#"):
                        continue

                    name = row.get("company_name", "").strip()
                    if not name:
                        continue

                    homepage = row.get("homepage_url", "").strip() or None
                    careers_url = row.get("careers_url", "").strip() or None
                    vcs = [
                        v.strip()
                        for v in row.get("vc_backers", "").split(",")
                        if v.strip()
                    ]
                    notes = row.get("notes", "").strip() or None

                    # Check known ATS mapping first
                    name_lower = name.lower()
                    if name_lower in KNOWN_COMPANY_ATS:
                        ats_type, ats_id = KNOWN_COMPANY_ATS[name_lower]
                    else:
                        ats_type, ats_id = detect_ats_from_url(careers_url or "")

                    company = PortfolioCompany(
                        name=name,
                        homepage=homepage,
                        careers_url=careers_url,
                        backed_by=vcs,
                        ats_type=ats_type,
                        ats_identifier=ats_id,
                        notes=notes,
                    )
                    companies.append(company)
                    logger.debug("loaded_portfolio_company", name=name, ats=ats_type.value, source="csv")

        except Exception as e:
            logger.error("csv_load_error", path=str(self.csv_path), error=str(e))

        logger.info("portfolio_csv_loaded", count=len(companies))
        return companies

    def _scrape_portfolio_page(self, vc: VCData) -> list[PortfolioCompany]:
        """Attempt to scrape companies from a VC's portfolio page.

        This is best-effort and respects robots.txt.
        """
        if not vc.portfolio_url:
            return []

        companies = []
        try:
            response = self.http_client.get(vc.portfolio_url)
            soup = BeautifulSoup(response.text, "html.parser")

            # Try common portfolio page patterns
            # Pattern 1: Links with company names
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)

                # Skip navigation, social links, etc.
                if not text or len(text) < 2 or len(text) > 50:
                    continue
                if any(skip in href.lower() for skip in [
                    "twitter", "linkedin", "facebook", "instagram",
                    "mailto:", "tel:", "#", "javascript:",
                    "blog", "news", "about", "team", "contact",
                ]):
                    continue

                # Check if it looks like a company link (external domain)
                if href.startswith("http"):
                    parsed = urlparse(href)
                    # Skip links back to the VC's own site
                    if vc.website and parsed.netloc in vc.website:
                        continue

                    # This might be a portfolio company
                    company = PortfolioCompany(
                        name=text,
                        homepage=href,
                        backed_by=[vc.name],
                    )
                    companies.append(company)

            logger.info(
                "portfolio_scraped",
                vc=vc.name,
                companies_found=len(companies),
            )

        except Exception as e:
            logger.warning(
                "portfolio_scrape_failed",
                vc=vc.name,
                url=vc.portfolio_url,
                error=str(e),
            )

        return companies

    def _find_careers_url(self, company: PortfolioCompany) -> Optional[str]:
        """Attempt to find a company's careers page URL."""
        if not company.homepage:
            return None

        # Common careers page paths
        careers_paths = [
            "/careers",
            "/jobs",
            "/careers/",
            "/jobs/",
            "/about/careers",
            "/company/careers",
            "/join",
            "/join-us",
            "/work-with-us",
        ]

        try:
            # First check the homepage for a careers link
            response = self.http_client.get(company.homepage)
            soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link.get("href", "").lower()
                text = link.get_text(strip=True).lower()

                if any(kw in href or kw in text for kw in ["career", "job", "join", "hiring"]):
                    full_url = urljoin(company.homepage, link.get("href"))
                    ats_type, ats_id = detect_ats_from_url(full_url)
                    company.ats_type = ats_type
                    company.ats_identifier = ats_id
                    return full_url

        except Exception as e:
            logger.debug(
                "careers_discovery_failed",
                company=company.name,
                error=str(e),
            )

        return None

    def discover_from_vcs(
        self,
        vcs: list[VCData],
        scrape_portfolios: bool = True,
    ) -> list[PortfolioCompany]:
        """Discover portfolio companies from VC portfolio pages.

        Args:
            vcs: List of VCs to check
            scrape_portfolios: Whether to attempt scraping portfolio pages

        Returns:
            List of discovered portfolio companies
        """
        all_companies: dict[str, PortfolioCompany] = {}

        if scrape_portfolios:
            for vc in vcs:
                companies = self._scrape_portfolio_page(vc)
                for company in companies:
                    # Merge with existing or add new
                    key = company.name.lower()
                    if key in all_companies:
                        all_companies[key].backed_by.extend(company.backed_by)
                        all_companies[key].backed_by = list(set(
                            all_companies[key].backed_by
                        ))
                    else:
                        all_companies[key] = company

        # Dedupe VCs
        for company in all_companies.values():
            company.backed_by = list(set(company.backed_by))

        return list(all_companies.values())

    def get_all_companies(
        self,
        vcs: list[VCData],
        scrape_portfolios: bool = True,
    ) -> list[Company]:
        """Get all portfolio companies from CSV and scraping.

        Returns Company objects ready for job discovery.
        """
        # Load from CSV first (these take priority)
        csv_companies = self.load_from_csv()

        # Try to discover from VC portfolio pages
        discovered = []
        if scrape_portfolios:
            discovered = self.discover_from_vcs(vcs, scrape_portfolios=True)

        # Merge: CSV takes priority
        csv_names = {c.name.lower() for c in csv_companies}
        merged = list(csv_companies)

        for company in discovered:
            if company.name.lower() not in csv_names:
                merged.append(company)

        # Convert to Company objects
        result = []
        for pc in merged:
            # Try to find careers URL if not set
            if not pc.careers_url and pc.homepage:
                pc.careers_url = self._find_careers_url(pc)

            company = Company(
                name=pc.name,
                company_type=CompanyType.VC_BACKED,
                homepage=pc.homepage,
                careers_url=pc.careers_url,
                ats_type=pc.ats_type,
                ats_identifier=pc.ats_identifier,
                backed_by=pc.backed_by,
                notes=pc.notes,
            )
            result.append(company)

        logger.info(
            "portfolio_companies_total",
            csv_count=len(csv_companies),
            discovered_count=len(discovered),
            merged_count=len(result),
        )

        return result


def discover_portfolio_companies(
    http_client: HTTPClient,
    cache_dir: Path,
    csv_path: Optional[Path] = None,
    vcs: Optional[list[VCData]] = None,
    scrape_portfolios: bool = True,
) -> list[Company]:
    """Convenience function to discover all portfolio companies.

    Args:
        http_client: HTTP client for making requests
        cache_dir: Directory for caching
        csv_path: Path to user-maintained portfolios.csv
        vcs: List of VCs to check (defaults to TOP_VCS)
        scrape_portfolios: Whether to scrape VC portfolio pages

    Returns:
        List of Company objects
    """
    if vcs is None:
        vcs = TOP_VCS

    manager = PortfolioManager(
        http_client=http_client,
        cache_dir=cache_dir,
        csv_path=csv_path,
    )

    return manager.get_all_companies(vcs, scrape_portfolios=scrape_portfolios)
