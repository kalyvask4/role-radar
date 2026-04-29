"""Report generation for Role Radar."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from role_radar.company_sources import get_company_descriptions
from role_radar.models import CompanyType, RunSummary, ScoredJob
from role_radar.salary_estimator import get_salary_for_job
from role_radar.utils.logging import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Generates reports for debugging and auditing."""

    def __init__(self, output_dir: Path, template_dir: Optional[Path] = None):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    def _generate_filename(self, prefix: str, extension: str) -> Path:
        """Generate a unique filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{prefix}_{timestamp}.{extension}"

    def save_json_report(
        self,
        jobs: list[ScoredJob],
        summary: RunSummary,
    ) -> Path:
        """Save detailed JSON report."""
        filepath = self._generate_filename("report", "json")

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "run_id": summary.run_id,
                "started_at": summary.started_at.isoformat(),
                "completed_at": summary.completed_at.isoformat() if summary.completed_at else None,
                "companies_processed": summary.companies_processed,
                "total_jobs_found": summary.total_jobs_found,
                "jobs_after_filter": summary.jobs_after_filter,
                "jobs_after_dedupe": summary.jobs_after_dedupe,
                "jobs_in_email": summary.jobs_in_email,
                "email_sent": summary.email_sent,
            },
            "jobs": [],
        }

        for scored_job in jobs:
            job = scored_job.job
            # Get salary (actual or estimated)
            salary = get_salary_for_job(job)
            salary_data = {
                "min": salary.min_salary,
                "max": salary.max_salary,
                "currency": salary.currency,
                "formatted": salary.format(),
                "is_estimated": salary.is_estimated,
            } if salary else None

            job_data = {
                "rank": scored_job.rank,
                "score": scored_job.score,
                "score_breakdown": scored_job.score_breakdown.to_dict(),
                "match_reasons": scored_job.match_reasons,
                "job": {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "company_type": job.company_type.value,
                    "location": {
                        "city": job.location.city,
                        "state": job.location.state,
                        "country": job.location.country,
                        "remote": job.location.remote,
                        "hybrid": job.location.hybrid,
                        "formatted": job.location.format(),
                    },
                    "salary": salary_data,
                    "apply_url": job.apply_url,
                    "posted_date": job.posted_date.isoformat() if job.posted_date else None,
                    "department": job.department,
                    "seniority": job.seniority,
                    "source_ats": job.source_ats.value if job.source_ats else None,
                    "description": job.description,
                },
            }
            report["jobs"].append(job_data)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("json_report_saved", path=str(filepath))
        return filepath

    def save_html_report(
        self,
        jobs: list[ScoredJob],
        summary: RunSummary,
    ) -> Path:
        """Save HTML report for viewing."""
        filepath = self._generate_filename("report", "html")

        # Calculate stats
        ai_count = sum(
            1 for j in jobs
            if j.job.company_type in (CompanyType.AI_TOP_20, CompanyType.BOTH)
        )
        vc_count = sum(
            1 for j in jobs
            if j.job.company_type in (CompanyType.VC_BACKED, CompanyType.BOTH)
        )
        avg_score = sum(j.score for j in jobs) / len(jobs) if jobs else 0
        company_descriptions = get_company_descriptions()

        # ───── Impeccable design system: tinted neutrals, modular type scale,
        # serif headings, single warm accent, hairline rules instead of nested cards.
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Role Radar — {datetime.now().strftime('%b %d, %Y')}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg:        #F7F6F3;
            --surface:   #FFFFFF;
            --rule:      #EAE7E0;
            --rule-soft: #F0EDE6;
            --ink:       #1F1D1A;
            --ink-muted: #6E6A63;
            --ink-soft:  #9A958C;
            --accent:    #C2410C;
            --accent-bg: #FBEBE0;
            --good:      #15803D;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            padding: 64px 24px;
            background: var(--bg);
            color: var(--ink);
            font-family: 'Söhne', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Helvetica, sans-serif;
            font-size: 16px;
            line-height: 1.55;
            -webkit-font-smoothing: antialiased;
        }}
        .wrap {{ max-width: 880px; margin: 0 auto; }}

        h1, h2, h3 {{
            font-family: 'Fraunces', 'Iowan Old Style', Georgia, serif;
            font-weight: 500;
            letter-spacing: -0.01em;
            margin: 0;
            color: var(--ink);
        }}
        h1 {{ font-size: 48px; line-height: 1.05; }}
        .role-title {{
            font-family: 'Fraunces', Georgia, serif;
            font-size: 22px;
            line-height: 1.25;
            font-weight: 500;
            margin: 0;
        }}

        .eyebrow {{
            font-size: 12px;
            font-weight: 500;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--accent);
            margin-bottom: 12px;
        }}
        .lede {{ font-size: 18px; color: var(--ink-muted); margin: 16px 0 0; max-width: 540px; }}

        header {{ margin-bottom: 64px; }}

        /* Stats: inline row, hairline-bordered, NOT cards */
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0;
            border-top: 1px solid var(--rule);
            border-bottom: 1px solid var(--rule);
            margin-bottom: 64px;
        }}
        .stat {{
            padding: 24px 0;
            border-right: 1px solid var(--rule-soft);
        }}
        .stat:last-child {{ border-right: none; }}
        .stat-num {{
            font-family: 'Fraunces', Georgia, serif;
            font-size: 34px;
            font-weight: 500;
            line-height: 1;
            color: var(--ink);
            font-variant-numeric: tabular-nums;
        }}
        .stat-label {{
            font-size: 12px;
            color: var(--ink-muted);
            margin-top: 8px;
            letter-spacing: 0.02em;
        }}

        /* Run summary as a single muted paragraph, not a debug box */
        .run-summary {{
            font-size: 13px;
            color: var(--ink-soft);
            margin: -32px 0 64px;
            font-variant-numeric: tabular-nums;
        }}
        .run-summary span + span::before {{ content: " · "; color: var(--rule); }}

        /* Roles: hairline-separated rows on the page surface */
        .roles {{
            background: var(--surface);
            border: 1px solid var(--rule);
            padding: 0 32px;
        }}
        .role {{
            padding: 32px 0;
            border-top: 1px solid var(--rule-soft);
            display: grid;
            grid-template-columns: 32px 1fr auto;
            gap: 24px;
            align-items: baseline;
        }}
        .role:first-child {{ border-top: none; }}
        .role:hover {{ background: var(--rule-soft); margin: 0 -32px; padding-left: 32px; padding-right: 32px; transition: background 150ms ease-out; }}

        .role-rank {{
            font-family: 'Fraunces', Georgia, serif;
            font-size: 14px;
            color: var(--ink-soft);
            font-variant-numeric: tabular-nums;
            padding-top: 4px;
        }}
        .role-body {{ min-width: 0; }}
        .company-line {{
            font-size: 14px;
            color: var(--ink-muted);
            margin: 8px 0 0;
        }}
        .company-name {{ color: var(--ink); font-weight: 500; }}
        .company-desc {{ color: var(--ink-soft); font-style: italic; }}
        .badge {{
            display: inline-block;
            font-size: 11px;
            color: var(--accent);
            background: var(--accent-bg);
            padding: 2px 8px;
            border-radius: 999px;
            margin-left: 8px;
            letter-spacing: 0.02em;
            vertical-align: 1px;
        }}

        .meta {{
            font-size: 13px;
            color: var(--ink-muted);
            margin: 12px 0 0;
        }}
        .meta span + span::before {{ content: " · "; color: var(--ink-soft); }}

        .reasons {{
            font-size: 13px;
            color: var(--good);
            margin: 12px 0 0;
            padding-left: 16px;
            position: relative;
        }}
        .reasons::before {{
            content: "";
            position: absolute;
            left: 0; top: 7px;
            width: 6px; height: 6px;
            background: var(--good);
            border-radius: 50%;
        }}
        .breakdown {{
            font-size: 11px;
            color: var(--ink-soft);
            margin-top: 12px;
            font-variant-numeric: tabular-nums;
        }}
        .breakdown span + span::before {{ content: " / "; color: var(--rule); }}

        .cta {{
            display: inline-block;
            margin-top: 16px;
            font-size: 14px;
            font-weight: 500;
            color: var(--accent);
            text-decoration: none;
            border-bottom: 1px solid var(--accent);
            padding-bottom: 1px;
            transition: color 150ms ease-out, border-color 150ms ease-out;
        }}
        .cta:hover {{ color: var(--ink); border-color: var(--ink); }}

        .score {{
            font-family: 'Fraunces', Georgia, serif;
            font-size: 32px;
            font-weight: 500;
            color: var(--ink);
            line-height: 1;
            text-align: right;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }}
        .score-out {{ color: var(--ink-soft); font-size: 14px; }}

        @media (max-width: 640px) {{
            body {{ padding: 32px 16px; }}
            h1 {{ font-size: 34px; }}
            .stats {{ grid-template-columns: repeat(2, 1fr); }}
            .stat:nth-child(2) {{ border-right: none; }}
            .role {{ grid-template-columns: 24px 1fr; }}
            .score {{ grid-column: 2; text-align: left; font-size: 26px; margin-top: 8px; }}
            .roles {{ padding: 0 20px; }}
            .role:hover {{ margin: 0 -20px; padding-left: 20px; padding-right: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="wrap">
        <header>
            <div class="eyebrow">Role Radar · {datetime.now().strftime('%b %d, %Y')}</div>
            <h1>{len(jobs)} roles worth a look</h1>
            <p class="lede">Bay Area PM matches scored against your CV, ranked by fit.</p>
        </header>

        <div class="stats">
            <div class="stat">
                <div class="stat-num">{len(jobs)}</div>
                <div class="stat-label">Total roles</div>
            </div>
            <div class="stat">
                <div class="stat-num">{ai_count}</div>
                <div class="stat-label">Top AI companies</div>
            </div>
            <div class="stat">
                <div class="stat-num">{vc_count}</div>
                <div class="stat-label">VC-backed</div>
            </div>
            <div class="stat">
                <div class="stat-num">{avg_score:.1f}</div>
                <div class="stat-label">Avg fit</div>
            </div>
        </div>

        <p class="run-summary">
            <span>Run {summary.run_id}</span>
            <span>{summary.companies_processed} companies</span>
            <span>{summary.total_jobs_found:,} jobs scanned</span>
            <span>{summary.jobs_after_dedupe} after dedupe</span>
            <span>Email {'sent' if summary.email_sent else 'not sent'}</span>
        </p>

        <div class="roles">
"""

        for scored_job in jobs:
            job = scored_job.job
            badge = ""
            if job.company_type == CompanyType.AI_TOP_20:
                badge = '<span class="badge">Top AI</span>'
            elif job.company_type == CompanyType.VC_BACKED:
                badge = '<span class="badge">VC-backed</span>'

            posted_str = job.posted_date.strftime('%b %d') if job.posted_date else 'date unknown'
            desc = company_descriptions.get(job.company.lower())
            desc_html = f' · <span class="company-desc">{desc}</span>' if desc else ''
            reason_html = f'<p class="reasons">{scored_job.match_reasons[0]}</p>' if scored_job.match_reasons else ''
            dept_html = f'<span>{job.department}</span>' if job.department else ''

            html_content += f"""
            <div class="role">
                <div class="role-rank">{scored_job.rank:02d}</div>
                <div class="role-body">
                    <h3 class="role-title">{job.title}</h3>
                    <p class="company-line">
                        <span class="company-name">{job.company}</span>{desc_html}{badge}
                    </p>
                    <p class="meta">
                        <span>{job.location.format()}</span>
                        <span>Posted {posted_str}</span>
                        {dept_html}
                    </p>
                    {reason_html}
                    <div class="breakdown">
                        <span>Title {scored_job.score_breakdown.title_seniority:.0f}/25</span>
                        <span>Skills {scored_job.score_breakdown.skills_overlap:.0f}/35</span>
                        <span>Domain {scored_job.score_breakdown.domain_overlap:.0f}/25</span>
                        <span>Location {scored_job.score_breakdown.location_fit:.0f}/10</span>
                        <span>Company {scored_job.score_breakdown.company_preference:.0f}/5</span>
                    </div>
                    <a href="{job.apply_url}" class="cta" target="_blank">View role →</a>
                </div>
                <div class="score">{scored_job.score:.0f}<span class="score-out">/100</span></div>
            </div>
"""

        html_content += """
        </div>
    </div>
</body>
</html>
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info("html_report_saved", path=str(filepath))
        return filepath

    def save_reports(
        self,
        jobs: list[ScoredJob],
        summary: RunSummary,
    ) -> tuple[Path, Path]:
        """Save both JSON and HTML reports.

        Returns (json_path, html_path).
        """
        json_path = self.save_json_report(jobs, summary)
        html_path = self.save_html_report(jobs, summary)

        return json_path, html_path
