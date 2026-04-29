"""AI Top-20 Companies scoring and selection."""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import yaml

from role_radar.models import AICategory, ATSType, Company, CompanyType
from role_radar.utils.logging import get_logger

logger = get_logger(__name__)

# Date the seed list below was last manually reviewed. Bump this whenever you
# add/remove companies, then re-run `role-radar companies` to confirm freshness.
LAST_UPDATED = date(2026, 4, 25)
STALE_AFTER_DAYS = 60


def check_freshness() -> Optional[int]:
    """Warn if the seed list hasn't been refreshed recently. Returns days stale or None."""
    age_days = (date.today() - LAST_UPDATED).days
    if age_days > STALE_AFTER_DAYS:
        logger.warning(
            "ai_companies_seed_stale",
            last_updated=LAST_UPDATED.isoformat(),
            age_days=age_days,
            threshold_days=STALE_AFTER_DAYS,
            message="Refresh ai_top20.py: new frontier labs and funding rounds may be missing.",
        )
        return age_days
    return None


def _yaml_to_company_data(entry: dict) -> "AICompanyData":
    """Convert a YAML override entry into AICompanyData."""
    category_raw = entry.get("category", "ai_apps")
    try:
        category = AICategory(category_raw)
    except ValueError:
        category = AICategory.AI_APPS

    ats_raw = entry.get("ats_type", "unknown")
    try:
        ats_type = ATSType(ats_raw)
    except ValueError:
        ats_type = ATSType.UNKNOWN

    return AICompanyData(
        name=entry["name"],
        homepage=entry.get("homepage", ""),
        careers_url=entry.get("careers_url"),
        ats_type=ats_type,
        ats_identifier=entry.get("ats_identifier"),
        category=category,
        github_stars=entry.get("github_stars"),
        funding_amount_m=entry.get("funding_amount_m"),
        is_public=entry.get("is_public", False),
        employee_count_estimate=entry.get("employee_count_estimate"),
        founded_year=entry.get("founded_year"),
        notable_achievements=entry.get("notable_achievements") or [],
        description=entry.get("description"),
    )


def get_company_descriptions(overrides_path: Optional[Path] = None) -> dict[str, str]:
    """Build a {company_name_lower: description} map from seed + YAML overrides.

    Falls back to the first notable_achievement when an explicit description is
    missing. Used by the email template and HTML report to give Alex a 1-line
    "what this company does" so he doesn't have to look it up.
    """
    if overrides_path is None:
        overrides_path = Path.cwd() / "data" / "ai_companies.yaml"
    additions, removals = load_overrides(overrides_path)

    seed = [c for c in AI_COMPANIES_SEED if c.name.lower() not in removals] + additions

    descriptions: dict[str, str] = {}
    for c in seed:
        if c.description:
            desc = c.description
        elif c.notable_achievements:
            desc = c.notable_achievements[0]
        else:
            continue
        # Cap length so it fits cleanly under the company name
        if len(desc) > 90:
            desc = desc[:87].rstrip() + "…"
        descriptions[c.name.lower()] = desc
    return descriptions


def load_overrides(path: Path) -> tuple[list["AICompanyData"], set[str]]:
    """Load company add/remove overrides from a YAML file.

    Format:
        last_updated: "2026-04-25"
        add:
          - name: NewCo
            careers_url: ...
            ats_type: greenhouse
            ats_identifier: newco
            category: frontier_lab
            funding_amount_m: 500
        remove:
          - "Old Company Name"

    Returns (additions, removals_lower_set).
    """
    if not path.exists():
        return [], set()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        logger.warning("ai_overrides_yaml_invalid", path=str(path), error=str(e))
        return [], set()

    additions = [_yaml_to_company_data(e) for e in (data.get("add") or [])]
    removals = {str(name).lower() for name in (data.get("remove") or [])}

    if "last_updated" in data:
        logger.info(
            "ai_overrides_loaded",
            path=str(path),
            additions=len(additions),
            removals=len(removals),
            last_updated=str(data["last_updated"]),
        )
    return additions, removals


@dataclass
class AICompanyData:
    """Data for scoring an AI company."""
    name: str
    homepage: str
    careers_url: Optional[str] = None
    ats_type: ATSType = ATSType.UNKNOWN
    ats_identifier: Optional[str] = None
    category: AICategory = AICategory.AI_APPS

    # Scoring inputs (pre-researched for reliability)
    github_stars: Optional[int] = None  # If OSS
    funding_amount_m: Optional[float] = None  # In millions USD
    is_public: bool = False
    employee_count_estimate: Optional[int] = None
    founded_year: Optional[int] = None
    notable_achievements: list[str] = None
    description: Optional[str] = None  # Short one-liner shown in email/report

    def __post_init__(self):
        if self.notable_achievements is None:
            self.notable_achievements = []


# Seed list of AI companies with pre-researched data
# This data is manually curated to ensure accuracy without requiring API calls
AI_COMPANIES_SEED: list[AICompanyData] = [
    # Frontier Labs (Category score: 25)
    AICompanyData(
        name="OpenAI",
        homepage="https://openai.com",
        careers_url="https://openai.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="openai",
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=13000,
        employee_count_estimate=3000,
        notable_achievements=["GPT-4", "ChatGPT", "DALL-E", "Sora"],
    ),
    AICompanyData(
        name="Anthropic",
        homepage="https://anthropic.com",
        careers_url="https://www.anthropic.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="anthropic",
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=7600,
        employee_count_estimate=1000,
        notable_achievements=["Claude", "Constitutional AI", "Safety research leader"],
    ),
    AICompanyData(
        name="Google DeepMind",
        homepage="https://deepmind.google",
        careers_url="https://deepmind.google/about/careers/",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="deepmind",
        category=AICategory.FRONTIER_LAB,
        is_public=True,
        employee_count_estimate=3000,
        notable_achievements=["AlphaGo", "AlphaFold", "Gemini"],
    ),
    AICompanyData(
        name="xAI",
        homepage="https://x.ai",
        careers_url="https://x.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="xai",
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=6000,
        employee_count_estimate=200,
        notable_achievements=["Grok"],
    ),
    AICompanyData(
        name="Meta AI",
        homepage="https://ai.meta.com",
        careers_url="https://www.metacareers.com",
        ats_type=ATSType.GENERIC_HTML,  # Custom platform (not Workday)
        category=AICategory.FRONTIER_LAB,
        is_public=True,
        github_stars=50000,  # LLaMA
        notable_achievements=["LLaMA", "Open source AI leader"],
    ),

    # AI Infrastructure (Category score: 20)
    AICompanyData(
        name="NVIDIA",
        homepage="https://www.nvidia.com",
        careers_url="https://nvidia.eightfold.ai/careers",
        ats_type=ATSType.GENERIC_HTML,  # Eightfold AI (no public API)
        category=AICategory.AI_INFRA,
        is_public=True,
        notable_achievements=["GPU leader", "CUDA", "AI hardware dominance"],
    ),
    AICompanyData(
        name="Databricks",
        homepage="https://databricks.com",
        careers_url="https://www.databricks.com/company/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="databricks",
        category=AICategory.AI_INFRA,
        funding_amount_m=4100,
        employee_count_estimate=6000,
        notable_achievements=["Lakehouse architecture", "MLflow", "Mosaic ML acquisition"],
    ),
    AICompanyData(
        name="Scale AI",
        homepage="https://scale.com",
        careers_url="https://scale.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="scaleai",
        category=AICategory.AI_INFRA,
        funding_amount_m=1000,
        employee_count_estimate=1000,
        notable_achievements=["Data labeling leader", "Government contracts"],
    ),
    AICompanyData(
        name="Anyscale",
        homepage="https://www.anyscale.com",
        careers_url="https://www.anyscale.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="anyscale",
        category=AICategory.AI_INFRA,
        github_stars=35000,  # Ray
        funding_amount_m=260,
        notable_achievements=["Ray framework", "Distributed computing"],
    ),
    AICompanyData(
        name="Together AI",
        homepage="https://together.ai",
        careers_url="https://www.together.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="togetherai",
        category=AICategory.AI_INFRA,
        funding_amount_m=225,
        notable_achievements=["Open source model hosting", "RedPajama"],
    ),
    AICompanyData(
        name="Modal",
        homepage="https://modal.com",
        careers_url="https://modal.com/careers",
        ats_type=ATSType.LEVER,
        ats_identifier="modal",
        category=AICategory.AI_INFRA,
        funding_amount_m=68,
        notable_achievements=["Serverless GPU compute"],
    ),
    AICompanyData(
        name="Weights & Biases",
        homepage="https://wandb.ai",
        careers_url="https://wandb.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="wandb",
        category=AICategory.AI_INFRA,
        funding_amount_m=250,
        notable_achievements=["ML experiment tracking leader"],
    ),

    # AI Applications (Category score: 15)
    AICompanyData(
        name="Hugging Face",
        homepage="https://huggingface.co",
        careers_url="https://huggingface.co/jobs",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="huggingface",
        category=AICategory.AI_APPS,
        github_stars=130000,  # transformers
        funding_amount_m=395,
        notable_achievements=["Transformers library", "Model hub", "Open source leader"],
    ),
    AICompanyData(
        name="Cohere",
        homepage="https://cohere.com",
        careers_url="https://cohere.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="cohere",
        category=AICategory.AI_APPS,
        funding_amount_m=970,
        notable_achievements=["Enterprise LLM", "Command models"],
    ),
    AICompanyData(
        name="Mistral AI",
        homepage="https://mistral.ai",
        careers_url="https://mistral.ai/careers/",
        ats_type=ATSType.LEVER,
        ats_identifier="mistral",
        category=AICategory.AI_APPS,
        funding_amount_m=640,
        notable_achievements=["European AI leader", "Open weights models"],
    ),
    AICompanyData(
        name="Perplexity",
        homepage="https://perplexity.ai",
        careers_url="https://www.perplexity.ai/hub/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="perplexity",
        category=AICategory.AI_APPS,
        funding_amount_m=500,
        notable_achievements=["AI-powered search"],
    ),
    AICompanyData(
        name="Character.AI",
        homepage="https://character.ai",
        careers_url="https://character.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="characterai",
        category=AICategory.AI_APPS,
        funding_amount_m=150,
        notable_achievements=["AI companions", "High engagement"],
    ),
    AICompanyData(
        name="Runway",
        homepage="https://runwayml.com",
        careers_url="https://runwayml.com/careers/",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="runwayml",
        category=AICategory.AI_APPS,
        funding_amount_m=230,
        notable_achievements=["Gen-2", "AI video generation leader"],
    ),
    AICompanyData(
        name="Stability AI",
        homepage="https://stability.ai",
        careers_url="https://stability.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="stabilityai",
        category=AICategory.AI_APPS,
        funding_amount_m=170,
        notable_achievements=["Stable Diffusion", "Open source image generation"],
    ),
    AICompanyData(
        name="Midjourney",
        homepage="https://www.midjourney.com",
        careers_url="https://www.midjourney.com/careers/",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        notable_achievements=["Image generation leader", "Viral adoption"],
    ),
    AICompanyData(
        name="Inflection AI",
        homepage="https://inflection.ai",
        careers_url="https://inflection.ai/careers",
        ats_type=ATSType.LEVER,
        ats_identifier="inflection",
        category=AICategory.AI_APPS,
        funding_amount_m=1500,
        notable_achievements=["Pi personal assistant"],
    ),
    AICompanyData(
        name="Adept",
        homepage="https://adept.ai",
        careers_url="https://www.adept.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="adept",
        category=AICategory.AI_APPS,
        funding_amount_m=415,
        notable_achievements=["Action transformers", "AI agents"],
    ),
    AICompanyData(
        name="Goodfire",
        homepage="https://goodfire.ai",
        careers_url="https://goodfire.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="goodfire",
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=50,
        notable_achievements=["Interpretability research", "AI safety", "Model internals"],
    ),
    AICompanyData(
        name="Reflection AI",
        homepage="https://reflection.ai",
        careers_url="https://reflection.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="reflection",
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=130,
        notable_achievements=["AI agents", "Founded by ex-Inflection team"],
    ),
    AICompanyData(
        name="Resolve AI",
        homepage="https://resolve.ai",
        careers_url="https://resolve.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="resolveai",
        category=AICategory.AI_APPS,
        funding_amount_m=35,
        notable_achievements=["AI coding agent", "Enterprise AI"],
    ),
    AICompanyData(
        name="Sierra AI",
        homepage="https://sierra.ai",
        careers_url="https://sierra.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="sierra",
        category=AICategory.AI_APPS,
        funding_amount_m=110,
        notable_achievements=["Conversational AI for CX", "Founded by Bret Taylor"],
    ),
    AICompanyData(
        name="Magic",
        homepage="https://magic.dev",
        careers_url="https://magic.dev/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="magic",
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=465,
        notable_achievements=["Long context AI", "Code generation"],
    ),
    AICompanyData(
        name="World Labs",
        homepage="https://worldlabs.ai",
        careers_url="https://worldlabs.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="worldlabs",
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=230,
        notable_achievements=["Spatial intelligence", "Founded by Fei-Fei Li"],
    ),
    AICompanyData(
        name="Physical Intelligence",
        homepage="https://physicalintelligence.company",
        careers_url="https://physicalintelligence.company/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="physicalintelligence",
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=400,
        notable_achievements=["Robotics foundation models", "Pi-zero"],
    ),
    AICompanyData(
        name="Pika",
        homepage="https://pika.art",
        careers_url="https://pika.art/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="pika",
        category=AICategory.AI_APPS,
        funding_amount_m=135,
        notable_achievements=["AI video generation", "Consumer video AI"],
    ),
    AICompanyData(
        name="ElevenLabs",
        homepage="https://elevenlabs.io",
        careers_url="https://elevenlabs.io/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="elevenlabs",
        category=AICategory.AI_APPS,
        funding_amount_m=180,
        notable_achievements=["Voice AI leader", "Text-to-speech"],
    ),
    AICompanyData(
        name="Suno",
        homepage="https://suno.ai",
        careers_url="https://suno.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="suno",
        category=AICategory.AI_APPS,
        funding_amount_m=125,
        notable_achievements=["AI music generation", "Viral adoption"],
    ),
    AICompanyData(
        name="Harvey",
        homepage="https://harvey.ai",
        careers_url="https://www.harvey.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="harvey",
        category=AICategory.AI_APPS,
        funding_amount_m=206,
        notable_achievements=["AI for legal", "Enterprise legal AI"],
    ),
    AICompanyData(
        name="Glean",
        homepage="https://glean.com",
        careers_url="https://glean.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="gleanwork",
        category=AICategory.AI_APPS,
        funding_amount_m=360,
        notable_achievements=["Enterprise search AI", "Work assistant"],
    ),

    # AI Developer Tools (Category score: 15)
    AICompanyData(
        name="LangChain",
        homepage="https://langchain.com",
        careers_url="https://www.langchain.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="langchain",
        category=AICategory.AI_DEV_TOOLS,
        github_stars=95000,
        funding_amount_m=35,
        notable_achievements=["LLM orchestration framework"],
    ),
    AICompanyData(
        name="Pinecone",
        homepage="https://www.pinecone.io",
        careers_url="https://www.pinecone.io/careers/",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="pinecone",
        category=AICategory.AI_DEV_TOOLS,
        funding_amount_m=138,
        notable_achievements=["Vector database leader"],
    ),
    AICompanyData(
        name="Weaviate",
        homepage="https://weaviate.io",
        careers_url="https://weaviate.io/company/careers",
        ats_type=ATSType.LEVER,
        ats_identifier="weaviate",
        category=AICategory.AI_DEV_TOOLS,
        github_stars=12000,
        funding_amount_m=68,
        notable_achievements=["Open source vector database"],
    ),
    AICompanyData(
        name="Chroma",
        homepage="https://www.trychroma.com",
        careers_url="https://www.trychroma.com/careers",
        ats_type=ATSType.LEVER,
        ats_identifier="chroma",
        category=AICategory.AI_DEV_TOOLS,
        github_stars=15000,
        funding_amount_m=20,
        notable_achievements=["AI-native embedding database"],
    ),
    AICompanyData(
        name="Replicate",
        homepage="https://replicate.com",
        careers_url="https://replicate.com/about#jobs",
        ats_type=ATSType.LEVER,
        ats_identifier="replicate",
        category=AICategory.AI_DEV_TOOLS,
        funding_amount_m=40,
        notable_achievements=["ML model deployment platform"],
    ),
    AICompanyData(
        name="Replit",
        homepage="https://replit.com",
        careers_url="https://replit.com/site/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="replit",
        category=AICategory.AI_DEV_TOOLS,
        funding_amount_m=222,
        notable_achievements=["AI-powered development environment", "Ghostwriter"],
    ),
    AICompanyData(
        name="Cursor",
        homepage="https://cursor.com",
        careers_url="https://www.cursor.com/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="cursor",
        category=AICategory.AI_DEV_TOOLS,
        funding_amount_m=60,
        notable_achievements=["AI-first code editor"],
    ),
    AICompanyData(
        name="Cognition",
        homepage="https://cognition.ai",
        careers_url="https://cognition.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="cognition",
        category=AICategory.AI_DEV_TOOLS,
        funding_amount_m=175,
        notable_achievements=["Devin AI software engineer", "Windsurf IDE"],
    ),
    AICompanyData(
        name="Poolside",
        homepage="https://poolside.ai",
        careers_url="https://poolside.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="poolside",
        category=AICategory.AI_DEV_TOOLS,
        funding_amount_m=500,
        notable_achievements=["AI code generation", "Coding-focused LLM"],
    ),

    # New Frontier Labs (2025-2026 additions)
    AICompanyData(
        name="Safe Superintelligence",
        homepage="https://ssi.inc",
        careers_url="https://ssi.inc/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=2000,
        employee_count_estimate=30,
        notable_achievements=["Founded by Ilya Sutskever", "$32B valuation", "Safe AGI mission"],
    ),
    AICompanyData(
        name="Thinking Machines Lab",
        homepage="https://thinkingmachines.ai",
        careers_url="https://thinkingmachines.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=2000,
        employee_count_estimate=50,
        notable_achievements=["Founded by Mira Murati (ex-OpenAI CTO)", "Tinker product", "$12B valuation"],
    ),
    AICompanyData(
        name="Reka AI",
        homepage="https://reka.ai",
        careers_url="https://reka.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="Reka",
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=100,
        notable_achievements=["Multimodal AI models", "Founded by ex-Google/DeepMind researchers"],
    ),

    # New AI Infra (2025-2026 additions)
    AICompanyData(
        name="CoreWeave",
        homepage="https://www.coreweave.com",
        careers_url="https://www.coreweave.com/careers/job",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="coreweave",
        category=AICategory.AI_INFRA,
        funding_amount_m=15000,
        employee_count_estimate=1500,
        notable_achievements=["GPU cloud leader", "IPO 2025", "$35B+ valuation"],
    ),
    AICompanyData(
        name="Cerebras",
        homepage="https://www.cerebras.ai",
        careers_url="https://www.cerebras.ai/open-positions",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="cerebrassystems",
        category=AICategory.AI_INFRA,
        funding_amount_m=1000,
        employee_count_estimate=500,
        notable_achievements=["Wafer-scale AI chips", "World's largest AI processor", "$23B valuation"],
    ),
    AICompanyData(
        name="Groq",
        homepage="https://groq.com",
        careers_url="https://groq.com/careers",
        ats_type=ATSType.GENERIC_HTML,  # Uses Gem, not standard ATS
        category=AICategory.AI_INFRA,
        funding_amount_m=750,
        employee_count_estimate=400,
        notable_achievements=["LPU inference chips", "Fastest AI inference", "$6.9B valuation"],
    ),
    AICompanyData(
        name="Lambda",
        homepage="https://lambda.ai",
        careers_url="https://lambda.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="lambda",
        category=AICategory.AI_INFRA,
        funding_amount_m=2300,
        employee_count_estimate=300,
        notable_achievements=["GPU cloud", "Superintelligence Cloud", "$4B+ valuation"],
    ),
    AICompanyData(
        name="Fireworks AI",
        homepage="https://fireworks.ai",
        careers_url="https://fireworks.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="fireworksai",
        category=AICategory.AI_INFRA,
        funding_amount_m=254,
        notable_achievements=["Fast AI inference platform", "Ex-Meta engineering team", "$4B valuation"],
    ),

    # New AI Apps (2025-2026 additions)
    AICompanyData(
        name="Distyl AI",
        homepage="https://distyl.ai",
        careers_url="https://distyl.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="Distyl",
        category=AICategory.AI_APPS,
        funding_amount_m=175,
        notable_achievements=["Enterprise AI software", "$1.8B valuation"],
    ),
    AICompanyData(
        name="Hebbia",
        homepage="https://hebbia.ai",
        careers_url="https://careers.hebbia.ai/",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="hebbia",
        category=AICategory.AI_APPS,
        funding_amount_m=130,
        notable_achievements=["AI for finance", "40%+ of largest asset managers use it"],
    ),
    AICompanyData(
        name="Abridge",
        homepage="https://abridge.com",
        careers_url="https://abridge.com/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="abridge",
        category=AICategory.AI_APPS,
        funding_amount_m=213,
        notable_achievements=["AI healthcare documentation", "Clinical AI leader"],
    ),

    # ===== Definitive Target List (user-curated, 2026) =====

    # AI Infrastructure & Compute
    AICompanyData(
        name="Applied Intuition",
        homepage="https://appliedintuition.com",
        careers_url="https://appliedintuition.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="appliedintuition",
        category=AICategory.AI_INFRA,
        funding_amount_m=1500,
        employee_count_estimate=600,
        notable_achievements=["AV software stack leader", "Simulation platform", "$15B valuation"],
    ),
    AICompanyData(
        name="Crusoe",
        homepage="https://crusoe.ai",
        careers_url="https://crusoe.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="crusoe",
        category=AICategory.AI_INFRA,
        funding_amount_m=1400,
        employee_count_estimate=500,
        notable_achievements=["AI cloud and data centers", "Sustainable compute", "$3B+ valuation"],
    ),
    AICompanyData(
        name="SambaNova",
        homepage="https://sambanova.ai",
        careers_url="https://sambanova.ai/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="sambanova",
        category=AICategory.AI_INFRA,
        funding_amount_m=1150,
        employee_count_estimate=400,
        notable_achievements=["AI chip and systems leader", "Fastest LLM inference", "$5B valuation"],
    ),
    AICompanyData(
        name="fal",
        homepage="https://fal.ai",
        careers_url="https://fal.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="fal",
        category=AICategory.AI_INFRA,
        funding_amount_m=23,
        notable_achievements=["Generative media infrastructure", "Fast image/video inference APIs"],
    ),
    AICompanyData(
        name="Skild AI",
        homepage="https://skild.ai",
        careers_url="https://skild.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_INFRA,
        funding_amount_m=300,
        notable_achievements=["AI foundation models for robotics", "$1.5B valuation"],
    ),

    # AI Applications
    AICompanyData(
        name="Black Forest Labs",
        homepage="https://blackforestlabs.ai",
        careers_url="https://blackforestlabs.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=100,
        notable_achievements=["FLUX image generation model", "Ex-Stability AI founders", "State-of-the-art image gen"],
    ),
    AICompanyData(
        name="Chai Discovery",
        homepage="https://chaidiscovery.com",
        careers_url="https://chaidiscovery.com/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="chai",
        category=AICategory.AI_APPS,
        funding_amount_m=30,
        notable_achievements=["AI drug discovery", "Molecular structure prediction"],
    ),
    AICompanyData(
        name="Clay",
        homepage="https://clay.com",
        careers_url="https://clay.com/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="clay",
        category=AICategory.AI_APPS,
        funding_amount_m=62,
        notable_achievements=["AI go-to-market tools", "Data enrichment AI", "$1.25B valuation"],
    ),
    AICompanyData(
        name="Cyera",
        homepage="https://cyera.io",
        careers_url="https://cyera.io/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="cyera",
        category=AICategory.AI_APPS,
        funding_amount_m=760,
        notable_achievements=["AI data security platform", "$3B valuation"],
    ),
    AICompanyData(
        name="Gamma",
        homepage="https://gamma.app",
        careers_url="https://gamma.app/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="gamma",
        category=AICategory.AI_APPS,
        funding_amount_m=12,
        notable_achievements=["AI graphic design and presentations", "YC-backed"],
    ),
    AICompanyData(
        name="Genspark",
        homepage="https://genspark.ai",
        careers_url="https://genspark.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        funding_amount_m=100,
        notable_achievements=["AI tools for knowledge workers", "AI search and agents"],
    ),
    AICompanyData(
        name="HeyGen",
        homepage="https://heygen.com",
        careers_url="https://heygen.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="heygen",
        category=AICategory.AI_APPS,
        funding_amount_m=60,
        notable_achievements=["AI video and avatar generation", "$500M+ valuation"],
    ),
    AICompanyData(
        name="krea.ai",
        homepage="https://krea.ai",
        careers_url="https://krea.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        funding_amount_m=21,
        notable_achievements=["AI image generation and editing", "Real-time image AI"],
    ),
    AICompanyData(
        name="Legora",
        homepage="https://legora.com",
        careers_url="https://legora.com/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        funding_amount_m=30,
        notable_achievements=["Legal automation software", "AI for law firms"],
    ),
    AICompanyData(
        name="Listen Labs",
        homepage="https://listenlabs.ai",
        careers_url="https://listenlabs.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        funding_amount_m=10,
        notable_achievements=["AI market research tools", "Automated qualitative research"],
    ),
    AICompanyData(
        name="Mercor",
        homepage="https://mercor.com",
        careers_url="https://mercor.com/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="mercor",
        category=AICategory.AI_APPS,
        funding_amount_m=32,
        notable_achievements=["AI data labeling and hiring", "AI workforce marketplace"],
    ),
    AICompanyData(
        name="Rogo",
        homepage="https://rogo.ai",
        careers_url="https://rogo.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="rogo",
        category=AICategory.AI_APPS,
        funding_amount_m=30,
        notable_achievements=["AI finance tools", "AI for investment research"],
    ),
    AICompanyData(
        name="Speak",
        homepage="https://speak.com",
        careers_url="https://speak.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="speak",
        category=AICategory.AI_APPS,
        funding_amount_m=78,
        notable_achievements=["AI language learning tutor", "GPT-4 powered speaking practice"],
    ),
    AICompanyData(
        name="Surge AI",
        homepage="https://surgehq.ai",
        careers_url="https://surgehq.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        funding_amount_m=15,
        notable_achievements=["AI data labeling service", "RLHF data provider"],
    ),
    AICompanyData(
        name="Synthesia",
        homepage="https://synthesia.io",
        careers_url="https://synthesia.io/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="synthesia",
        category=AICategory.AI_APPS,
        funding_amount_m=250,
        notable_achievements=["AI avatar and video generator", "$1B+ valuation"],
    ),

    # Additional AI Companies (2026 additions)
    AICompanyData(
        name="Decagon",
        homepage="https://decagon.ai",
        careers_url="https://decagon.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="decagon",
        category=AICategory.AI_APPS,
        funding_amount_m=100,
        notable_achievements=["AI customer support agents", "Enterprise CX automation"],
    ),
    AICompanyData(
        name="Higgsfield",
        homepage="https://higgsfield.ai",
        careers_url="https://higgsfield.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        funding_amount_m=8,
        notable_achievements=["AI video generation", "Social video AI"],
    ),
    AICompanyData(
        name="Cline",
        homepage="https://cline.bot",
        careers_url="https://cline.bot/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_DEV_TOOLS,
        notable_achievements=["AI coding assistant", "VS Code extension", "Autonomous coding agent"],
    ),
    AICompanyData(
        name="Neo4j",
        homepage="https://neo4j.com",
        careers_url="https://neo4j.com/careers/",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="neo4j",
        category=AICategory.AI_INFRA,
        funding_amount_m=582,
        notable_achievements=["Graph database leader", "GraphRAG", "Knowledge graphs for AI"],
    ),
    AICompanyData(
        name="HappyRobot",
        homepage="https://happyrobot.ai",
        careers_url="https://happyrobot.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        funding_amount_m=25,
        notable_achievements=["AI for trucking and logistics", "Voice AI for freight"],
    ),
    AICompanyData(
        name="Casca",
        homepage="https://casca.co",
        careers_url="https://casca.co/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        funding_amount_m=10,
        notable_achievements=["AI for lending", "Loan origination automation"],
    ),
    AICompanyData(
        name="Granola",
        homepage="https://granola.ai",
        careers_url="https://granola.ai/careers",
        ats_type=ATSType.ASHBY,
        ats_identifier="granola",
        category=AICategory.AI_APPS,
        funding_amount_m=20,
        notable_achievements=["AI meeting notes", "AI notepad for meetings"],
    ),
    AICompanyData(
        name="Aleph Alpha",
        homepage="https://aleph-alpha.com",
        careers_url="https://aleph-alpha.com/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.FRONTIER_LAB,
        funding_amount_m=500,
        notable_achievements=["European sovereign AI", "Enterprise AI platform", "German AI leader"],
    ),
    AICompanyData(
        name="EliseAI",
        homepage="https://eliseai.com",
        careers_url="https://eliseai.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="eliseai",
        category=AICategory.AI_APPS,
        funding_amount_m=75,
        notable_achievements=["AI for real estate", "Property management AI", "Healthcare AI"],
    ),
    AICompanyData(
        name="Trunk Tools",
        homepage="https://trunktools.com",
        careers_url="https://trunktools.com/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        funding_amount_m=36,
        notable_achievements=["AI for construction", "Enterprise construction AI"],
    ),
    AICompanyData(
        name="Edra",
        homepage="https://edra.ai",
        careers_url="https://edra.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        notable_achievements=["AI startup"],
    ),
    AICompanyData(
        name="Emergent",
        homepage="https://emergentai.com",
        careers_url="https://emergentai.com/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        notable_achievements=["AI company"],
    ),
    AICompanyData(
        name="Wonderful",
        homepage="https://wonderful.ai",
        careers_url="https://wonderful.ai/careers",
        ats_type=ATSType.GENERIC_HTML,
        category=AICategory.AI_APPS,
        notable_achievements=["AI company"],
    ),

    # AI-Adjacent (Category score: 10)
    AICompanyData(
        name="Snowflake",
        homepage="https://www.snowflake.com",
        careers_url="https://careers.snowflake.com",
        ats_type=ATSType.GENERIC_HTML,  # PhenomPeople (not Workday)
        category=AICategory.AI_ADJACENT,
        is_public=True,
        notable_achievements=["Data cloud leader", "Cortex AI features"],
    ),
    AICompanyData(
        name="Vercel",
        homepage="https://vercel.com",
        careers_url="https://vercel.com/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="vercel",
        category=AICategory.AI_ADJACENT,
        funding_amount_m=563,
        notable_achievements=["AI SDK", "Next.js", "v0 AI product"],
    ),
    AICompanyData(
        name="Notion",
        homepage="https://notion.so",
        careers_url="https://www.notion.so/careers",
        ats_type=ATSType.GREENHOUSE,
        ats_identifier="notion",
        category=AICategory.AI_ADJACENT,
        funding_amount_m=343,
        notable_achievements=["Notion AI", "Popular productivity tool"],
    ),
]


class AICompanyScorer:
    """Scorer for AI companies using the defined rubric."""

    # Category scores (0-25)
    CATEGORY_SCORES = {
        AICategory.FRONTIER_LAB: 25,
        AICategory.AI_INFRA: 20,
        AICategory.AI_APPS: 15,
        AICategory.AI_DEV_TOOLS: 15,
        AICategory.AI_ADJACENT: 10,
    }

    def score_technical_reputation(self, data: AICompanyData) -> float:
        """Score based on GitHub stars and benchmarks (0-20)."""
        if data.github_stars is None:
            # No OSS presence, give moderate score based on notable achievements
            return 10 if data.notable_achievements else 5

        if data.github_stars >= 50000:
            return 20
        elif data.github_stars >= 20000:
            return 17
        elif data.github_stars >= 10000:
            return 15
        elif data.github_stars >= 5000:
            return 12
        else:
            return 8

    def score_funding(self, data: AICompanyData) -> float:
        """Score based on funding amount or public status (0-20)."""
        if data.is_public:
            return 20

        if data.funding_amount_m is None:
            return 5

        if data.funding_amount_m >= 1000:
            return 20
        elif data.funding_amount_m >= 500:
            return 17
        elif data.funding_amount_m >= 100:
            return 14
        elif data.funding_amount_m >= 50:
            return 10
        else:
            return 6

    def score_hiring_velocity(self, data: AICompanyData, job_count: int = 0) -> float:
        """Score based on number of open roles (0-15)."""
        # This would ideally be fetched dynamically
        # For now, use employee count as proxy
        if data.employee_count_estimate:
            if data.employee_count_estimate >= 3000:
                return 15
            elif data.employee_count_estimate >= 1000:
                return 12
            elif data.employee_count_estimate >= 500:
                return 10
            elif data.employee_count_estimate >= 100:
                return 8
            else:
                return 5
        return 8  # Default for unknown

    def score_developer_adoption(self, data: AICompanyData) -> float:
        """Score based on developer adoption signals (0-10)."""
        score = 5  # Base score

        if data.github_stars:
            if data.github_stars >= 50000:
                score = 10
            elif data.github_stars >= 10000:
                score = 8
            elif data.github_stars >= 5000:
                score = 6

        return score

    def score_momentum(self, data: AICompanyData) -> float:
        """Score based on recent momentum (0-10)."""
        # Based on notable achievements and recent news
        achievements = data.notable_achievements or []
        if len(achievements) >= 3:
            return 10
        elif len(achievements) >= 2:
            return 8
        elif len(achievements) >= 1:
            return 6
        return 4

    def score_company(self, data: AICompanyData) -> tuple[float, dict]:
        """Calculate total score for a company.

        Returns (total_score, breakdown_dict).
        """
        category = self.CATEGORY_SCORES.get(data.category, 10)
        technical = self.score_technical_reputation(data)
        funding = self.score_funding(data)
        velocity = self.score_hiring_velocity(data)
        adoption = self.score_developer_adoption(data)
        momentum = self.score_momentum(data)

        total = category + technical + funding + velocity + adoption + momentum

        breakdown = {
            "category": category,
            "technical_reputation": technical,
            "funding_scale": funding,
            "hiring_velocity": velocity,
            "developer_adoption": adoption,
            "momentum": momentum,
            "total": total,
        }

        return total, breakdown


def generate_ai_top20(
    output_path: Optional[Path] = None,
    overrides_path: Optional[Path] = None,
) -> tuple[list[Company], str]:
    """Generate the top 20 AI companies list with scoring.

    If `overrides_path` exists, additions/removals from that YAML file are applied
    on top of the in-code seed list, letting users iterate without code changes.

    Returns (list of Company objects, markdown report).
    """
    check_freshness()
    scorer = AICompanyScorer()

    # Apply YAML overrides if available
    additions: list[AICompanyData] = []
    removals: set[str] = set()
    if overrides_path is None:
        overrides_path = Path.cwd() / "data" / "ai_companies.yaml"
    additions, removals = load_overrides(overrides_path)

    effective_seed = [c for c in AI_COMPANIES_SEED if c.name.lower() not in removals]
    effective_seed.extend(additions)

    # Score all companies
    scored_companies: list[tuple[AICompanyData, float, dict]] = []
    for data in effective_seed:
        score, breakdown = scorer.score_company(data)
        scored_companies.append((data, score, breakdown))

    # Sort by score descending
    scored_companies.sort(key=lambda x: -x[1])

    # Use full list — the function name says "top 20" but capping silently drops
    # legitimate companies (Big Tech / Greenhouse boards) added via YAML overrides.
    # If you want to limit, do it at the email/report layer where the user can see.
    top_20 = scored_companies

    # Generate markdown report
    md_lines = [
        "# Top 20 AI Companies Scoring Report",
        "",
        "## Methodology",
        "",
        "Companies are scored on a 100-point scale across six dimensions:",
        "",
        "| Dimension | Max Points | Description |",
        "|-----------|------------|-------------|",
        "| Company Category | 25 | Frontier Lab (25), AI Infra (20), AI Apps (15), AI-Adjacent (10) |",
        "| Technical Reputation | 20 | GitHub stars, benchmark performance, research output |",
        "| Funding/Scale | 20 | Total funding raised or public company status |",
        "| Hiring Velocity | 15 | Open roles count, employee growth |",
        "| Developer Adoption | 10 | API usage, community engagement, ecosystem |",
        "| Recent Momentum | 10 | Major announcements, product launches |",
        "",
        "## Top 20 Rankings",
        "",
        "| Rank | Company | Category | Total | Cat | Tech | Fund | Hire | Adopt | Mom |",
        "|------|---------|----------|-------|-----|------|------|------|-------|-----|",
    ]

    for i, (data, score, breakdown) in enumerate(top_20, 1):
        md_lines.append(
            f"| {i} | {data.name} | {data.category.value} | {score:.0f} | "
            f"{breakdown['category']} | {breakdown['technical_reputation']:.0f} | "
            f"{breakdown['funding_scale']:.0f} | {breakdown['hiring_velocity']:.0f} | "
            f"{breakdown['developer_adoption']:.0f} | {breakdown['momentum']:.0f} |"
        )

    md_lines.extend([
        "",
        "## Company Details",
        "",
    ])

    for i, (data, score, breakdown) in enumerate(top_20, 1):
        achievements = ", ".join(data.notable_achievements) if data.notable_achievements else "N/A"
        funding_str = f"${data.funding_amount_m:.0f}M" if data.funding_amount_m else ("Public" if data.is_public else "Unknown")

        md_lines.extend([
            f"### {i}. {data.name}",
            f"- **Score**: {score:.0f}/100",
            f"- **Category**: {data.category.value}",
            f"- **Funding**: {funding_str}",
            f"- **Notable**: {achievements}",
            f"- **Homepage**: {data.homepage}",
            "",
        ])

    markdown_report = "\n".join(md_lines)

    # Save if path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_report)
        logger.info("ai_top20_report_saved", path=str(output_path))

    # Convert to Company objects
    companies = []
    for data, score, _ in top_20:
        company = Company(
            name=data.name,
            company_type=CompanyType.AI_TOP_20,
            homepage=data.homepage,
            careers_url=data.careers_url,
            ats_type=data.ats_type,
            ats_identifier=data.ats_identifier,
            ai_category=data.category,
            ai_score=score,
        )
        companies.append(company)

    return companies, markdown_report
