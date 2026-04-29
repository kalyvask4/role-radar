"""Email sending module for Role Radar."""

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from role_radar.company_sources import get_company_descriptions
from role_radar.config import EmailConfig
from role_radar.models import CompanyType, ScoredJob
from role_radar.utils.logging import get_logger

logger = get_logger(__name__)


class EmailRenderer:
    """Renders email content from templates."""

    def __init__(self, template_dir: Optional[Path] = None):
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    def _get_template_context(self, jobs: list[ScoredJob]) -> dict:
        """Build template context from scored jobs."""
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

        return {
            "jobs": jobs,
            "run_date": datetime.now().strftime("%B %d, %Y"),
            "total_roles": len(jobs),
            "ai_company_count": ai_count,
            "vc_backed_count": vc_count,
            "avg_score": avg_score,
            "company_descriptions": company_descriptions,
        }

    def render_html(self, jobs: list[ScoredJob]) -> str:
        """Render HTML email content."""
        template = self.env.get_template("email.html")
        context = self._get_template_context(jobs)
        return template.render(**context)

    def render_text(self, jobs: list[ScoredJob]) -> str:
        """Render plain text email content."""
        template = self.env.get_template("email.txt")
        context = self._get_template_context(jobs)
        return template.render(**context)


class EmailSender:
    """Sends emails via SMTP or SendGrid."""

    def __init__(self, config: EmailConfig):
        self.config = config
        self.renderer = EmailRenderer()

    def _send_smtp(
        self,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Send email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.config.from_email
        msg["To"] = self.config.to_email

        # Attach plain text and HTML versions
        text_part = MIMEText(text_body, "plain")
        html_part = MIMEText(html_body, "html")

        msg.attach(text_part)
        msg.attach(html_part)

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)

            logger.info(
                "email_sent_smtp",
                to=self.config.to_email,
                subject=subject,
            )
            return True

        except Exception as e:
            logger.error(
                "smtp_send_failed",
                error=str(e),
                host=self.config.smtp_host,
            )
            return False

    def _send_sendgrid(
        self,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Send email via SendGrid."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = SendGridAPIClient(api_key=self.config.sendgrid_api_key)

            message = Mail(
                from_email=Email(self.config.from_email),
                to_emails=To(self.config.to_email),
                subject=subject,
            )
            message.content = [
                Content("text/plain", text_body),
                Content("text/html", html_body),
            ]

            response = sg.send(message)

            logger.info(
                "email_sent_sendgrid",
                to=self.config.to_email,
                subject=subject,
                status_code=response.status_code,
            )
            return response.status_code in (200, 201, 202)

        except ImportError:
            logger.error("sendgrid_not_installed")
            return False

        except Exception as e:
            logger.error("sendgrid_send_failed", error=str(e))
            return False

    def send(
        self,
        jobs: list[ScoredJob],
        subject: Optional[str] = None,
    ) -> tuple[bool, str, str]:
        """Send email with job listings.

        Returns (success, html_body, text_body).
        """
        if not jobs:
            logger.warning("no_jobs_to_email")
            return False, "", ""

        if subject is None:
            subject = f"Role Radar: {len(jobs)} PM Roles for You ({datetime.now().strftime('%b %d')})"

        html_body = self.renderer.render_html(jobs)
        text_body = self.renderer.render_text(jobs)

        # Test mode: don't actually send
        if self.config.test_mode:
            logger.info(
                "email_test_mode",
                subject=subject,
                html_length=len(html_body),
                text_length=len(text_body),
            )
            print("\n" + "=" * 80)
            print("EMAIL TEST MODE - Would send:")
            print(f"To: {self.config.to_email}")
            print(f"Subject: {subject}")
            print("=" * 80)
            print("\nPLAIN TEXT VERSION:")
            print("-" * 40)
            print(text_body)
            print("=" * 80 + "\n")
            return True, html_body, text_body

        # Send via configured provider
        if self.config.provider == "sendgrid":
            success = self._send_sendgrid(subject, html_body, text_body)
        else:
            success = self._send_smtp(subject, html_body, text_body)

        return success, html_body, text_body
