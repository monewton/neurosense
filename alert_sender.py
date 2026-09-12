"""
NeuroSense AI - Email alert sender
Sends alerts to configured emails when summary status warrants it (e.g. "Needs Attention").
"""

import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Optional

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Statuses that trigger an email alert
ALERT_STATUSES = ("needs attention",)

DEFAULT_EMAILS_PATH = Path(__file__).parent / "alert_emails.json"


def load_alert_emails(path: Optional[Path] = None) -> List[str]:
    """Load email addresses from the JSON config file."""
    path = path or DEFAULT_EMAILS_PATH
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("alert_emails", [])


def should_send_alert(status: str) -> bool:
    """Return True if the given summary status should trigger an email alert."""
    if not status:
        return False
    return status.strip().lower() in ALERT_STATUSES


def send_alert(
    status: str,
    summary_details: Optional[dict] = None,
    *,
    dry_run: bool = False,
    emails_path: Optional[Path] = None,
) -> bool:
    """
    Send an email alert to all configured addresses for the given status.

    Args:
        status: Summary status (e.g. "Needs Attention").
        summary_details: Optional dict with keys like confidence, raw_analysis, timestamp.
        dry_run: If True, only log what would be sent; do not send.
        emails_path: Path to alert_emails.json (default: next to this module).

    Returns:
        True if alert was sent (or dry_run succeeded), False on error or no recipients.
    """
    if not should_send_alert(status):
        return False

    recipients = load_alert_emails(emails_path)
    if not recipients:
        print("[!] No alert emails configured in alert_emails.json")
        return False

    summary_details = summary_details or {}
    confidence = summary_details.get("confidence", "N/A")
    raw_analysis = summary_details.get("raw_analysis", "")[:500]
    timestamp = summary_details.get("timestamp", "")

    subject = f"[NeuroSense AI] Behavioral alert: {status}"
    body = f"""NeuroSense AI Behavioral Alert

Status: {status}
Confidence: {confidence}
Timestamp: {timestamp}

Summary:
{raw_analysis or 'No details available.'}

---
This is an automated alert from NeuroSense AI.
"""

    if dry_run:
        print("[DRY RUN] Would send alert:")
        print(f"   To: {recipients}")
        print(f"   Subject: {subject}")
        print(f"   Body preview: {body[:200]}...")
        return True

    smtp_host = os.getenv("ALERT_SMTP_HOST") or os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("ALERT_SMTP_PORT", os.getenv("SMTP_PORT", "587")))
    smtp_user = os.getenv("ALERT_SMTP_USER") or os.getenv("SMTP_USER")
    smtp_password = os.getenv("ALERT_SMTP_PASSWORD") or os.getenv("SMTP_PASSWORD")

    if not smtp_host or not smtp_user or not smtp_password:
        print("[!] SMTP not configured. Set ALERT_SMTP_HOST, ALERT_SMTP_USER, ALERT_SMTP_PASSWORD (or SMTP_*) in .env")
        print("   Dry run: would have sent to:", recipients)
        return False

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipients, msg.as_string())
        print(f"[OK] Alert sent to {len(recipients)} recipient(s)")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send alert: {e}")
        return False


def send_test_alert(dry_run: bool = True) -> bool:
    """
    Send a test alert for status "needs attention".
    Use for verifying email config and recipient list.
    """
    return send_alert(
        status="needs attention",
        summary_details={
            "confidence": "High",
            "timestamp": "Test run",
            "raw_analysis": "This is a test alert from NeuroSense AI. Status: needs attention.",
        },
        dry_run=dry_run,
    )


if __name__ == "__main__":
    import sys
    do_send = "--send" in sys.argv
    ok = send_test_alert(dry_run=not do_send)
    if do_send and ok:
        print("Test alert sent. Check inboxes for configured addresses.")
    elif not do_send:
        print("Run with --send to actually send the test email (requires SMTP in .env).")
    sys.exit(0 if ok else 1)
