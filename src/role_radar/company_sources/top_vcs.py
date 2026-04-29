"""Top VCs scoring and list management."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from role_radar.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VCData:
    """Data for a VC firm."""
    name: str
    website: str
    portfolio_url: Optional[str] = None
    portfolio_page_selector: Optional[str] = None  # CSS selector for company links

    # Scoring inputs
    unicorn_count: int = 0  # Known unicorn investments
    aum_billions: Optional[float] = None  # Assets under management
    stage_focus: str = "multi"  # seed, early, growth, multi
    sf_focus_pct: int = 50  # Estimated % of portfolio in SF/tech
    recent_deals_per_year: int = 10
    notable_investments: list[str] = field(default_factory=list)


# Curated list of top VCs with pre-researched data
TOP_VCS: list[VCData] = [
    VCData(
        name="Sequoia Capital",
        website="https://www.sequoiacap.com",
        portfolio_url="https://www.sequoiacap.com/our-companies/",
        unicorn_count=100,
        aum_billions=85,
        stage_focus="multi",
        sf_focus_pct=70,
        recent_deals_per_year=50,
        notable_investments=["Apple", "Google", "Stripe", "Airbnb", "WhatsApp"],
    ),
    VCData(
        name="Andreessen Horowitz",
        website="https://a16z.com",
        portfolio_url="https://a16z.com/portfolio/",
        unicorn_count=80,
        aum_billions=35,
        stage_focus="multi",
        sf_focus_pct=80,
        recent_deals_per_year=60,
        notable_investments=["GitHub", "Coinbase", "Slack", "Figma", "OpenAI"],
    ),
    VCData(
        name="Accel",
        website="https://www.accel.com",
        portfolio_url="https://www.accel.com/companies",
        unicorn_count=50,
        aum_billions=15,
        stage_focus="early",
        sf_focus_pct=60,
        recent_deals_per_year=30,
        notable_investments=["Facebook", "Spotify", "Dropbox", "Slack", "Crowdstrike"],
    ),
    VCData(
        name="Greylock Partners",
        website="https://greylock.com",
        portfolio_url="https://greylock.com/portfolio/",
        unicorn_count=40,
        aum_billions=5,
        stage_focus="early",
        sf_focus_pct=75,
        recent_deals_per_year=15,
        notable_investments=["LinkedIn", "Airbnb", "Discord", "Figma", "Palo Alto Networks"],
    ),
    VCData(
        name="Benchmark",
        website="https://www.benchmark.com",
        portfolio_url="https://www.benchmark.com/portfolio/",
        unicorn_count=35,
        aum_billions=4,
        stage_focus="seed",
        sf_focus_pct=80,
        recent_deals_per_year=10,
        notable_investments=["Uber", "Twitter", "Snap", "Discord", "eBay"],
    ),
    VCData(
        name="Lightspeed Venture Partners",
        website="https://lsvp.com",
        portfolio_url="https://lsvp.com/portfolio/",
        unicorn_count=50,
        aum_billions=18,
        stage_focus="multi",
        sf_focus_pct=65,
        recent_deals_per_year=40,
        notable_investments=["Snap", "Affirm", "Rubrik", "Epic Games", "Carta"],
    ),
    VCData(
        name="Kleiner Perkins",
        website="https://www.kleinerperkins.com",
        portfolio_url="https://www.kleinerperkins.com/portfolios/",
        unicorn_count=45,
        aum_billions=9,
        stage_focus="early",
        sf_focus_pct=75,
        recent_deals_per_year=20,
        notable_investments=["Amazon", "Google", "Twitter", "Slack", "Figma"],
    ),
    VCData(
        name="NEA",
        website="https://www.nea.com",
        portfolio_url="https://www.nea.com/portfolio",
        unicorn_count=40,
        aum_billions=25,
        stage_focus="multi",
        sf_focus_pct=60,
        recent_deals_per_year=35,
        notable_investments=["Salesforce", "Tableau", "Robinhood", "Plaid", "Databricks"],
    ),
    VCData(
        name="Founders Fund",
        website="https://foundersfund.com",
        portfolio_url="https://foundersfund.com/portfolio/",
        unicorn_count=30,
        aum_billions=11,
        stage_focus="early",
        sf_focus_pct=80,
        recent_deals_per_year=20,
        notable_investments=["SpaceX", "Palantir", "Stripe", "Airbnb", "Figma"],
    ),
    VCData(
        name="GV (Google Ventures)",
        website="https://www.gv.com",
        portfolio_url="https://www.gv.com/portfolio/",
        unicorn_count=35,
        aum_billions=8,
        stage_focus="multi",
        sf_focus_pct=70,
        recent_deals_per_year=30,
        notable_investments=["Uber", "Slack", "Stripe", "GitLab", "Duolingo"],
    ),
    VCData(
        name="Khosla Ventures",
        website="https://www.khoslaventures.com",
        portfolio_url="https://www.khoslaventures.com/portfolio/",
        unicorn_count=25,
        aum_billions=15,
        stage_focus="early",
        sf_focus_pct=75,
        recent_deals_per_year=25,
        notable_investments=["Square", "DoorDash", "Instacart", "Impossible Foods"],
    ),
    VCData(
        name="General Catalyst",
        website="https://www.generalcatalyst.com",
        portfolio_url="https://www.generalcatalyst.com/portfolio",
        unicorn_count=40,
        aum_billions=25,
        stage_focus="multi",
        sf_focus_pct=55,
        recent_deals_per_year=45,
        notable_investments=["Stripe", "Airbnb", "Snap", "HubSpot", "Datadog"],
    ),
    VCData(
        name="Index Ventures",
        website="https://www.indexventures.com",
        portfolio_url="https://www.indexventures.com/companies/",
        unicorn_count=50,
        aum_billions=16,
        stage_focus="multi",
        sf_focus_pct=40,
        recent_deals_per_year=40,
        notable_investments=["Figma", "Discord", "Notion", "Roblox", "Plaid"],
    ),
    VCData(
        name="Bessemer Venture Partners",
        website="https://www.bvp.com",
        portfolio_url="https://www.bvp.com/portfolio",
        unicorn_count=45,
        aum_billions=20,
        stage_focus="multi",
        sf_focus_pct=50,
        recent_deals_per_year=40,
        notable_investments=["LinkedIn", "Shopify", "Twilio", "Toast", "Canva"],
    ),
    VCData(
        name="IVP",
        website="https://www.ivp.com",
        portfolio_url="https://www.ivp.com/portfolio/",
        unicorn_count=35,
        aum_billions=12,
        stage_focus="growth",
        sf_focus_pct=60,
        recent_deals_per_year=20,
        notable_investments=["Slack", "Dropbox", "Twitter", "Snap", "GitHub"],
    ),
    VCData(
        name="Insight Partners",
        website="https://www.insightpartners.com",
        portfolio_url="https://www.insightpartners.com/portfolio/",
        unicorn_count=55,
        aum_billions=80,
        stage_focus="growth",
        sf_focus_pct=45,
        recent_deals_per_year=60,
        notable_investments=["Twitter", "Shopify", "Monday.com", "Wiz", "JFrog"],
    ),
    VCData(
        name="Battery Ventures",
        website="https://www.battery.com",
        portfolio_url="https://www.battery.com/our-companies/",
        unicorn_count=30,
        aum_billions=13,
        stage_focus="multi",
        sf_focus_pct=55,
        recent_deals_per_year=25,
        notable_investments=["Groupon", "Glassdoor", "Coinbase", "Wix"],
    ),
    VCData(
        name="Redpoint Ventures",
        website="https://www.redpoint.com",
        portfolio_url="https://www.redpoint.com/companies/",
        unicorn_count=25,
        aum_billions=6,
        stage_focus="early",
        sf_focus_pct=70,
        recent_deals_per_year=20,
        notable_investments=["Netflix", "Stripe", "Snowflake", "Twilio", "HashiCorp"],
    ),
    VCData(
        name="First Round Capital",
        website="https://firstround.com",
        portfolio_url="https://firstround.com/companies/",
        unicorn_count=20,
        aum_billions=3,
        stage_focus="seed",
        sf_focus_pct=75,
        recent_deals_per_year=35,
        notable_investments=["Uber", "Square", "Notion", "Roblox", "Looker"],
    ),
    VCData(
        name="Y Combinator",
        website="https://www.ycombinator.com",
        portfolio_url="https://www.ycombinator.com/companies",
        unicorn_count=100,
        aum_billions=5,
        stage_focus="seed",
        sf_focus_pct=85,
        recent_deals_per_year=300,
        notable_investments=["Airbnb", "Stripe", "Dropbox", "Coinbase", "DoorDash"],
    ),
    VCData(
        name="Spark Capital",
        website="https://www.sparkcapital.com",
        portfolio_url="https://www.sparkcapital.com/portfolio/",
        unicorn_count=20,
        aum_billions=4,
        stage_focus="early",
        sf_focus_pct=50,
        recent_deals_per_year=15,
        notable_investments=["Twitter", "Slack", "Affirm", "Discord", "Postmates"],
    ),
    VCData(
        name="Union Square Ventures",
        website="https://www.usv.com",
        portfolio_url="https://www.usv.com/companies/",
        unicorn_count=25,
        aum_billions=3,
        stage_focus="early",
        sf_focus_pct=40,
        recent_deals_per_year=15,
        notable_investments=["Twitter", "Coinbase", "Stripe", "Etsy", "Tumblr"],
    ),
    VCData(
        name="Felicis Ventures",
        website="https://www.felicis.com",
        portfolio_url="https://www.felicis.com/portfolio",
        unicorn_count=30,
        aum_billions=4,
        stage_focus="early",
        sf_focus_pct=75,
        recent_deals_per_year=30,
        notable_investments=["Shopify", "Canva", "Notion", "Plaid", "Flexport"],
    ),
    VCData(
        name="Ribbit Capital",
        website="https://ribbitcap.com",
        portfolio_url="https://ribbitcap.com/companies/",
        unicorn_count=15,
        aum_billions=5,
        stage_focus="early",
        sf_focus_pct=70,
        recent_deals_per_year=20,
        notable_investments=["Robinhood", "Coinbase", "Nubank", "Affirm"],
    ),
    VCData(
        name="Thrive Capital",
        website="https://www.thrivecap.com",
        portfolio_url="https://www.thrivecap.com/companies",
        unicorn_count=25,
        aum_billions=15,
        stage_focus="multi",
        sf_focus_pct=55,
        recent_deals_per_year=25,
        notable_investments=["Instagram", "Spotify", "Stripe", "OpenAI", "Slack"],
    ),
]


class VCScorer:
    """Scorer for VC firms using the defined rubric."""

    def score_track_record(self, vc: VCData) -> float:
        """Score based on unicorn count and exits (0-35)."""
        if vc.unicorn_count >= 50:
            return 35
        elif vc.unicorn_count >= 30:
            return 28
        elif vc.unicorn_count >= 15:
            return 20
        elif vc.unicorn_count >= 5:
            return 12
        else:
            return 5

    def score_fund_size(self, vc: VCData) -> float:
        """Score based on AUM (0-25)."""
        if vc.aum_billions is None:
            return 10

        if vc.aum_billions >= 20:
            return 25
        elif vc.aum_billions >= 10:
            return 22
        elif vc.aum_billions >= 5:
            return 18
        elif vc.aum_billions >= 2:
            return 14
        else:
            return 10

    def score_stage_focus(self, vc: VCData) -> float:
        """Score based on stage focus (0-20). Early stage preferred."""
        stage_scores = {
            "seed": 20,
            "early": 18,
            "multi": 15,
            "growth": 12,
        }
        return stage_scores.get(vc.stage_focus, 15)

    def score_sf_concentration(self, vc: VCData) -> float:
        """Score based on SF/tech portfolio concentration (0-10)."""
        if vc.sf_focus_pct >= 75:
            return 10
        elif vc.sf_focus_pct >= 60:
            return 8
        elif vc.sf_focus_pct >= 45:
            return 6
        else:
            return 4

    def score_activity(self, vc: VCData) -> float:
        """Score based on recent deal activity (0-10)."""
        if vc.recent_deals_per_year >= 40:
            return 10
        elif vc.recent_deals_per_year >= 25:
            return 8
        elif vc.recent_deals_per_year >= 15:
            return 6
        else:
            return 4

    def score_vc(self, vc: VCData) -> tuple[float, dict]:
        """Calculate total score for a VC.

        Returns (total_score, breakdown_dict).
        """
        track_record = self.score_track_record(vc)
        fund_size = self.score_fund_size(vc)
        stage = self.score_stage_focus(vc)
        sf_concentration = self.score_sf_concentration(vc)
        activity = self.score_activity(vc)

        total = track_record + fund_size + stage + sf_concentration + activity

        breakdown = {
            "track_record": track_record,
            "fund_size": fund_size,
            "stage_focus": stage,
            "sf_concentration": sf_concentration,
            "activity": activity,
            "total": total,
        }

        return total, breakdown


def generate_top_vcs_list(
    output_path: Optional[Path] = None,
) -> tuple[list[VCData], str]:
    """Generate ranked VC list with scoring.

    Returns (list of VCData, markdown report).
    """
    scorer = VCScorer()

    # Score all VCs
    scored_vcs: list[tuple[VCData, float, dict]] = []
    for vc in TOP_VCS:
        score, breakdown = scorer.score_vc(vc)
        scored_vcs.append((vc, score, breakdown))

    # Sort by score descending
    scored_vcs.sort(key=lambda x: -x[1])

    # Generate markdown report
    md_lines = [
        "# Top VCs Scoring Report",
        "",
        "## Methodology",
        "",
        "VCs are scored on a 100-point scale across five dimensions:",
        "",
        "| Dimension | Max Points | Description |",
        "|-----------|------------|-------------|",
        "| Track Record | 35 | Unicorn count, notable exits |",
        "| Fund Size/AUM | 25 | Assets under management |",
        "| Stage Focus | 20 | Seed/Early (20), Multi (15), Growth (12) |",
        "| SF/Tech Concentration | 10 | Portfolio focus on SF Bay Area |",
        "| Recent Activity | 10 | Deals per year |",
        "",
        "## Rankings",
        "",
        "| Rank | VC | Score | Track | Fund | Stage | SF | Activity |",
        "|------|-----|-------|-------|------|-------|-----|----------|",
    ]

    for i, (vc, score, breakdown) in enumerate(scored_vcs, 1):
        md_lines.append(
            f"| {i} | {vc.name} | {score:.0f} | "
            f"{breakdown['track_record']:.0f} | {breakdown['fund_size']:.0f} | "
            f"{breakdown['stage_focus']:.0f} | {breakdown['sf_concentration']:.0f} | "
            f"{breakdown['activity']:.0f} |"
        )

    md_lines.extend([
        "",
        "## VC Details",
        "",
    ])

    for i, (vc, score, breakdown) in enumerate(scored_vcs, 1):
        notable = ", ".join(vc.notable_investments) if vc.notable_investments else "N/A"
        aum = f"${vc.aum_billions:.0f}B" if vc.aum_billions else "Unknown"

        md_lines.extend([
            f"### {i}. {vc.name}",
            f"- **Score**: {score:.0f}/100",
            f"- **Stage Focus**: {vc.stage_focus}",
            f"- **AUM**: {aum}",
            f"- **Unicorns**: {vc.unicorn_count}",
            f"- **Notable Investments**: {notable}",
            f"- **Website**: {vc.website}",
            "",
        ])

    markdown_report = "\n".join(md_lines)

    # Save if path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_report)
        logger.info("top_vcs_report_saved", path=str(output_path))

    # Return sorted VCs
    sorted_vcs = [vc for vc, _, _ in scored_vcs]

    return sorted_vcs, markdown_report
