"""Gmail SMTP delivery provider."""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from research_digest.delivery.base import DeliveryProvider

logger = logging.getLogger(__name__)

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


class GmailProvider(DeliveryProvider):
    """Send digest via Gmail SMTP with App Password."""

    def __init__(
        self,
        from_addr: str | None = None,
        to_addr: str | None = None,
        app_password: str | None = None,
    ) -> None:
        self.from_addr = from_addr or os.environ.get("EMAIL_FROM", "")
        self.to_addr = to_addr or os.environ.get("EMAIL_TO", "")
        self.app_password = app_password or os.environ.get("GMAIL_APP_PASSWORD", "")

        if not self.from_addr:
            raise ValueError("EMAIL_FROM not set")
        if not self.to_addr:
            raise ValueError("EMAIL_TO not set")
        if not self.app_password:
            raise ValueError(
                "GMAIL_APP_PASSWORD not set. Create one at https://myaccount.google.com/apppasswords"
            )

    def send(self, subject: str, body_html: str, body_text: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr

        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        logger.info("Sending digest to %s via Gmail SMTP", self.to_addr)
        with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(self.from_addr, self.app_password)
            server.send_message(msg)
        logger.info("Digest sent successfully")
