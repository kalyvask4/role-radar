# Role Radar 🎯

A production-quality CLI tool that helps Product Managers find relevant roles at top AI companies and VC-backed startups in the SF Bay Area.

## Features

- **Curated Company Lists**: Transparent scoring methodology for Top 20 AI companies and Top VCs
- **Multi-ATS Support**: Connectors for Greenhouse, Lever, SmartRecruiters, and generic HTML parsing
- **Smart Matching**: CV-based scoring across title/seniority, skills, domains, and location
- **Deduplication**: Intelligent removal of duplicate job postings across sources
- **Email Reports**: Beautiful HTML emails with match rationale and score breakdowns
- **Local Caching**: SQLite database to avoid redundant API calls
- **Observability**: Structured JSON logging and run summaries

## Installation

### Prerequisites

- Python 3.11 or higher
- pip or pipx

### Install from source

```bash
cd role-radar
pip install -e ".[dev]"
```

### Quick Setup

```bash
# Initialize configuration files
role-radar init

# Edit .env with your email credentials
# Edit preferences.yaml for your job search

# Run in test mode (no email sent)
role-radar run path/to/your/cv.pdf

# Run and send email
role-radar run path/to/your/cv.pdf --send
```

## Configuration

### Environment Variables (.env)

Copy `.env.example` to `.env` and configure:

```bash
# Email settings (choose one provider)
ROLE_RADAR_EMAIL_PROVIDER=smtp  # smtp or sendgrid

# SMTP settings (for Gmail, use an App Password)
ROLE_RADAR_SMTP_HOST=smtp.gmail.com
ROLE_RADAR_SMTP_PORT=587
ROLE_RADAR_SMTP_USERNAME=your-email@gmail.com
ROLE_RADAR_SMTP_PASSWORD=your-app-password

# Email addresses
ROLE_RADAR_EMAIL_FROM=your-email@gmail.com
ROLE_RADAR_EMAIL_TO=your-email@gmail.com

# Test mode (prints email instead of sending)
ROLE_RADAR_EMAIL_TEST_MODE=true
```

### Preferences (preferences.yaml)

Customize your job search:

```yaml
location: "San Francisco Bay Area"
include_remote: true

seniority:
  - "PM"
  - "Senior PM"
  - "Staff PM"

allowed_titles:
  - "Product Manager"
  - "Technical Product Manager"
  - "AI Product Manager"
  - "Senior Product Manager"

excluded_keywords:
  - "Sales"
  - "Marketing"

max_roles_per_email: 15
```

### Portfolio Companies (data/portfolios.csv)

Add custom VC-backed companies:

```csv
company_name,homepage_url,careers_url,vc_backers,notes
Glean,https://www.glean.com,https://www.glean.com/careers,"Sequoia, Kleiner Perkins",Enterprise AI search
Harvey,https://www.harvey.ai,https://www.harvey.ai/careers,"Sequoia",Legal AI
```

## Usage

### CLI Commands

```bash
# Initialize configuration files
role-radar init

# Run job search (test mode - no email sent)
role-radar run path/to/cv.pdf

# Run with custom preferences
role-radar run path/to/cv.pdf --prefs my-preferences.yaml

# Run and send email
role-radar run path/to/cv.pdf --send

# Daily run mode (for cron)
role-radar run path/to/cv.pdf --daily

# Use cached jobs (skip fetching)
role-radar run path/to/cv.pdf --skip-fetch

# Show company lists
role-radar companies

# Debug a specific company
role-radar debug "OpenAI"
```

### Daily Cron Setup

Add to your crontab (`crontab -e`):

```bash
# Run Role Radar daily at 9 AM
0 9 * * * cd /path/to/role-radar && /path/to/venv/bin/role-radar run /path/to/cv.pdf --daily >> /var/log/role-radar.log 2>&1
```

## Scoring Methodology

### AI Top 20 Companies (100 points)

| Dimension | Max Points | Description |
|-----------|------------|-------------|
| Company Category | 25 | Frontier Lab (25), AI Infra (20), AI Apps (15) |
| Technical Reputation | 20 | GitHub stars, benchmarks, research output |
| Funding/Scale | 20 | Total funding or public company status |
| Hiring Velocity | 15 | Open roles count, growth signals |
| Developer Adoption | 10 | API usage, community size |
| Recent Momentum | 10 | Product launches, major announcements |

### Top VCs (100 points)

| Dimension | Max Points | Description |
|-----------|------------|-------------|
| Track Record | 35 | Unicorn count, notable exits |
| Fund Size/AUM | 25 | Assets under management |
| Stage Focus | 20 | Seed/Early (20), Growth (12) |
| SF Concentration | 10 | Portfolio focus on Bay Area |
| Recent Activity | 10 | Deals per year |

### Job Matching (100 points)

| Dimension | Max Points | Description |
|-----------|------------|-------------|
| Title/Seniority | 25 | Match between CV and job seniority |
| Skills Overlap | 35 | Technical and product skills match |
| Domain Overlap | 25 | Industry/domain expertise alignment |
| Location Fit | 10 | Geographic and remote preferences |
| Company Preference | 5 | Boost for AI/VC-backed companies |

## Output Files

After each run, find these files in `outputs/`:

- `report_YYYYMMDD_HHMMSS.json` - Detailed JSON report
- `report_YYYYMMDD_HHMMSS.html` - Visual HTML report
- `email_RUNID.html` - Email preview (test mode)
- `ai_top20_scoring.md` - AI company scoring breakdown
- `top_vcs_scoring.md` - VC scoring breakdown

## Legal & Ethical Considerations

Role Radar is designed to be respectful of websites and APIs:

- **No LinkedIn scraping** - We don't scrape LinkedIn or any site that prohibits it
- **robots.txt compliance** - All HTML parsing respects robots.txt
- **Rate limiting** - Built-in rate limiter (2 req/sec default)
- **Official APIs only** - Uses official ATS APIs (Greenhouse, Lever, etc.)
- **User-agent identification** - Identifies itself properly
- **Caching** - SQLite cache reduces redundant requests

## Troubleshooting

### No jobs found

1. Check that companies have valid ATS identifiers in the seed data
2. Verify your network can reach the job board APIs
3. Try `role-radar debug "CompanyName"` to test a specific company

### Email not sending

1. Ensure `.env` has correct credentials
2. For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833)
3. Test with `ROLE_RADAR_EMAIL_TEST_MODE=true` first

### Low match scores

1. Review your CV to ensure skills are clearly listed
2. Adjust `preferences.yaml` to match your experience level
3. Check that domains in your CV align with target companies

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=role_radar --cov-report=html

# Format code
black src tests
ruff check src tests

# Type checking
mypy src
```

## Architecture

```
src/role_radar/
├── main.py              # Typer CLI entry point
├── config.py            # Settings and preferences
├── cv_parser.py         # CV/resume parsing
├── company_sources/     # Company list generation
│   ├── ai_top20.py      # AI company scoring
│   ├── top_vcs.py       # VC scoring
│   └── vc_portfolios.py # Portfolio discovery
├── connectors/          # Job board connectors
│   ├── greenhouse.py
│   ├── lever.py
│   ├── smartrecruiters.py
│   └── generic_html.py
├── scoring.py           # Job-CV matching
├── dedupe.py            # Deduplication
├── storage.py           # SQLite caching
├── emailer.py           # Email sending
├── reporting.py         # Report generation
└── utils/
    ├── http.py          # HTTP client with rate limiting
    └── logging.py       # Structured logging
```

## License

MIT

## Contributing

Contributions welcome! Please open an issue first to discuss proposed changes.
