# """
# notifier.py — Geldium AI Collections System: Email Notifier
# ============================================================
# This module handles all email notifications sent by the agent.
# It has two jobs:
#   1. Alert a human agent when a High-risk customer is found
#   2. Send a daily summary report of all predictions

# HOW EMAIL SENDING WORKS:
#   We use Gmail's SMTP server (Simple Mail Transfer Protocol).
#   SMTP is the standard protocol computers use to send emails.
#   Think of it as the postal system — we hand our letter to Gmail,
#   Gmail delivers it.

# SETUP REQUIRED (do this once):
#   1. You need a Gmail account for the agent to send FROM
#   2. Enable 2-Factor Authentication on that Gmail account
#   3. Generate an "App Password" (not your real password):
#        Google Account → Security → 2-Step Verification → App Passwords
#        Name it "Geldium Agent" → copy the 16-character password
#   4. Set these environment variables on your machine or Render:
#        GELDIUM_SENDER_EMAIL    = youragent@gmail.com
#        GELDIUM_SENDER_PASSWORD = your-16-char-app-password
#        GELDIUM_RECEIVER_EMAIL  = where alerts should go (can be same address)

# WHY ENVIRONMENT VARIABLES?
#   Never hardcode passwords in code. If you push to GitHub, the whole
#   world can see your credentials. Environment variables keep secrets
#   out of your codebase — they live on the machine, not in the file.
# """

# # ── IMPORTS ──────────────────────────────────────────────────────────────────

# # smtplib   → Python's built-in email sending library
# #             handles the connection to Gmail's mail server
# import smtplib

# # email.*   → builds the email structure (headers, body, HTML content)
# from email.mime.multipart import MIMEMultipart   # container for email parts
# from email.mime.text import MIMEText             # the actual text/html content

# # os        → to read environment variables safely
# import os

# # logging   → structured logs (better than print in production)
# import logging

# # datetime  → for timestamps in reports
# from datetime import datetime

# logger = logging.getLogger(__name__)


# # ── CONFIG ────────────────────────────────────────────────────────────────────
# # Read credentials from environment variables.
# # os.getenv() returns None if the variable isn't set — we handle that below.

# SENDER_EMAIL    = os.getenv("GELDIUM_SENDER_EMAIL")
# SENDER_PASSWORD = os.getenv("GELDIUM_SENDER_PASSWORD")
# RECEIVER_EMAIL  = os.getenv("GELDIUM_RECEIVER_EMAIL")

# # Gmail's SMTP server address and port
# # Port 587 = TLS encryption (secure — always use this, not port 25)
# SMTP_SERVER = "smtp.gmail.com"
# SMTP_PORT   = 587


# # ── HELPER: CHECK CREDENTIALS ────────────────────────────────────────────────

# def credentials_configured() -> bool:
#     """
#     Check if email credentials are set before trying to send.
#     Returns True if all three env vars are present, False otherwise.
#     """
#     return all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL])


# # ── HELPER: SEND EMAIL ────────────────────────────────────────────────────────

# def send_email(subject: str, html_body: str) -> bool:
#     """
#     Core email sending function.
#     Takes a subject line and HTML body, sends via Gmail SMTP.
#     Returns True if sent successfully, False if anything went wrong.

#     Why HTML body?
#       Plain text emails look like terminal output. HTML lets us add
#       colours, tables, bold text — making alerts readable at a glance.
#     """

#     # Case: credentials not configured — log warning but don't crash
#     if not credentials_configured():
#         logger.warning(
#             "Email credentials not set. Skipping email send.\n"
#             "Set GELDIUM_SENDER_EMAIL, GELDIUM_SENDER_PASSWORD, "
#             "GELDIUM_RECEIVER_EMAIL as environment variables."
#         )
#         return False

#     try:
#         # Build the email message container
#         # MIMEMultipart("alternative") = email that can have both plain + HTML
#         msg = MIMEMultipart("alternative")
#         msg["Subject"] = subject
#         msg["From"]    = SENDER_EMAIL
#         msg["To"]      = RECEIVER_EMAIL

#         # Attach the HTML body
#         # "html" tells the email client to render it as HTML, not raw text
#         html_part = MIMEText(html_body, "html")
#         msg.attach(html_part)

#         # Connect to Gmail's SMTP server
#         # smtplib.SMTP() opens a connection (like dialling a phone number)
#         with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
#             server.ehlo()           # identify ourselves to the server
#             server.starttls()       # upgrade connection to encrypted TLS
#             server.login(SENDER_EMAIL, SENDER_PASSWORD)  # authenticate
#             server.sendmail(
#                 SENDER_EMAIL,
#                 RECEIVER_EMAIL,
#                 msg.as_string()     # convert message object to raw email string
#             )

#         logger.info(f"✅ Email sent: {subject}")
#         return True

#     # Case: wrong password or email address
#     except smtplib.SMTPAuthenticationError:
#         logger.error(
#             "Email authentication failed. Check your App Password.\n"
#             "Make sure you're using a Gmail App Password, not your real password."
#         )
#         return False

#     # Case: no internet connection or Gmail is unreachable
#     except smtplib.SMTPConnectError:
#         logger.error("Could not connect to Gmail SMTP server. Check internet connection.")
#         return False

#     # Case: anything else unexpected
#     except Exception as e:
#         logger.error(f"Failed to send email: {e}")
#         return False


# # ── EMAIL TEMPLATES ───────────────────────────────────────────────────────────
# # These functions build the HTML content for each type of email.
# # Keeping templates separate from the sending logic makes them easy to update.

# def send_high_risk_alert(customer_index: int, risk_score: float, confidence: float, intervention: str) -> bool:
#     """
#     Send an urgent alert email when a High-risk customer is detected.
#     Called once per High-risk customer found during the agent's daily run.
#     """

#     timestamp = datetime.now().strftime("%d %B %Y at %H:%M")

#     html_body = f"""
#     <html>
#     <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">

#         <!-- Header -->
#         <div style="background-color: #c0392b; padding: 20px; border-radius: 8px 8px 0 0;">
#             <h2 style="color: white; margin: 0;">🔴 HIGH RISK ALERT — Immediate Action Required</h2>
#             <p style="color: #fadbd8; margin: 5px 0 0 0;">Geldium AI Collections System — {timestamp}</p>
#         </div>

#         <!-- Body -->
#         <div style="background-color: #f9f9f9; padding: 25px; border: 1px solid #ddd;">
#             <p style="font-size: 16px;">A customer has been flagged as <strong>HIGH RISK</strong> by the automated delinquency prediction model.</p>

#             <!-- Stats table -->
#             <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
#                 <tr style="background-color: #c0392b; color: white;">
#                     <th style="padding: 10px; text-align: left;">Field</th>
#                     <th style="padding: 10px; text-align: left;">Value</th>
#                 </tr>
#                 <tr style="background-color: white;">
#                     <td style="padding: 10px; border-bottom: 1px solid #eee;">Customer Index</td>
#                     <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>#{customer_index}</strong></td>
#                 </tr>
#                 <tr style="background-color: #fef9f9;">
#                     <td style="padding: 10px; border-bottom: 1px solid #eee;">Risk Score</td>
#                     <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>{risk_score * 100:.1f}%</strong></td>
#                 </tr>
#                 <tr style="background-color: white;">
#                     <td style="padding: 10px; border-bottom: 1px solid #eee;">Model Confidence</td>
#                     <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>{confidence * 100:.1f}%</strong></td>
#                 </tr>
#                 <tr style="background-color: #fef9f9;">
#                     <td style="padding: 10px;">Recommended Action</td>
#                     <td style="padding: 10px;"><strong>{intervention}</strong></td>
#                 </tr>
#             </table>

#             <!-- Action box -->
#             <div style="background-color: #fadbd8; border-left: 4px solid #c0392b; padding: 15px; border-radius: 4px;">
#                 <strong>⚠️ Human Review Required</strong>
#                 <p style="margin: 8px 0 0 0;">
#                     This customer requires immediate human agent review.
#                     Please contact the customer within 24 hours and offer
#                     a personalised hardship plan or account review.
#                 </p>
#             </div>
#         </div>

#         <!-- Footer -->
#         <div style="background-color: #eee; padding: 12px; text-align: center; border-radius: 0 0 8px 8px;">
#             <small style="color: #888;">Geldium AI Collections System — Automated Alert | Do not reply to this email</small>
#         </div>

#     </body>
#     </html>
#     """

#     return send_email(
#         subject=f"🔴 HIGH RISK ALERT — Customer #{customer_index} Requires Immediate Review",
#         html_body=html_body
#     )


# def send_daily_summary(summary: dict) -> bool:
#     """
#     Send the daily summary report after the agent completes its run.
#     summary dict expected keys:
#         total, high, medium, low, run_time, errors
#     """

#     timestamp = datetime.now().strftime("%d %B %Y at %H:%M")

#     html_body = f"""
#     <html>
#     <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">

#         <!-- Header -->
#         <div style="background-color: #1a5276; padding: 20px; border-radius: 8px 8px 0 0;">
#             <h2 style="color: white; margin: 0;">📊 Daily Collections Risk Report</h2>
#             <p style="color: #aed6f1; margin: 5px 0 0 0;">Geldium AI Collections System — {timestamp}</p>
#         </div>

#         <!-- Summary stats -->
#         <div style="background-color: #f9f9f9; padding: 25px; border: 1px solid #ddd;">
#             <h3 style="color: #1a5276;">Today's Summary</h3>

#             <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
#                 <tr style="background-color: #1a5276; color: white;">
#                     <th style="padding: 12px; text-align: left;">Metric</th>
#                     <th style="padding: 12px; text-align: center;">Count</th>
#                 </tr>
#                 <tr style="background-color: white;">
#                     <td style="padding: 12px; border-bottom: 1px solid #eee;">Total Customers Scored</td>
#                     <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;"><strong>{summary['total']}</strong></td>
#                 </tr>
#                 <tr style="background-color: #fdedec;">
#                     <td style="padding: 12px; border-bottom: 1px solid #eee;">🔴 High Risk (Escalated)</td>
#                     <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;"><strong style="color: #c0392b;">{summary['high']}</strong></td>
#                 </tr>
#                 <tr style="background-color: #fef9e7;">
#                     <td style="padding: 12px; border-bottom: 1px solid #eee;">🟡 Medium Risk (Outreach)</td>
#                     <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;"><strong style="color: #d68910;">{summary['medium']}</strong></td>
#                 </tr>
#                 <tr style="background-color: #eafaf1;">
#                     <td style="padding: 12px; border-bottom: 1px solid #eee;">🟢 Low Risk (Reminder)</td>
#                     <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;"><strong style="color: #1e8449;">{summary['low']}</strong></td>
#                 </tr>
#                 <tr style="background-color: white;">
#                     <td style="padding: 12px;">⏱️ Agent Run Time</td>
#                     <td style="padding: 12px; text-align: center;">{summary['run_time']}</td>
#                 </tr>
#             </table>

#             <!-- Errors section (only shown if there were errors) -->
#             {'<div style="background-color: #fadbd8; border-left: 4px solid #c0392b; padding: 15px; border-radius: 4px; margin-top: 15px;"><strong>⚠️ Errors Encountered:</strong><p style="margin: 8px 0 0 0;">' + str(summary['errors']) + '</p></div>' if summary['errors'] else '<div style="background-color: #eafaf1; border-left: 4px solid #27ae60; padding: 15px; border-radius: 4px; margin-top: 15px;"><strong>✅ Agent completed with no errors.</strong></div>'}
#         </div>

#         <!-- Footer -->
#         <div style="background-color: #eee; padding: 12px; text-align: center; border-radius: 0 0 8px 8px;">
#             <small style="color: #888;">Geldium AI Collections System — Daily Report | Automated by AI Agent</small>
#         </div>

#     </body>
#     </html>
#     """

#     return send_email(
#         subject=f"📊 Geldium Daily Risk Report — {datetime.now().strftime('%d %b %Y')}",
#         html_body=html_body
#     )

"""
notifier.py — Geldium AI Collections System: Email Notifier
============================================================
Updated version — sender comes from .env (business controlled),
receiver is passed in as a parameter (user controlled).

This means:
  - Geldium owns and controls the sending email
  - Each user sets their own receiving email in the dashboard
  - No credentials are ever hardcoded in this file
"""

import smtplib
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv
from settings import get_sender_info, sender_configured

load_dotenv()

logger = logging.getLogger(__name__)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 587


# ── CORE SEND FUNCTION ────────────────────────────────────────────────────────

def send_email(subject: str, html_body: str, receiver_email: str, receiver_name: str = "Agent") -> bool:
    """
    Send an email FROM Geldium's business account TO the user's email.

    Parameters:
        subject        → email subject line
        html_body      → HTML formatted email body
        receiver_email → user's email (set in dashboard settings)
        receiver_name  → user's name (set in dashboard settings)

    Returns True if sent successfully, False otherwise.
    """

    if not sender_configured():
        logger.warning(
            "Sender credentials not configured.\n"
            "Set GELDIUM_SENDER_EMAIL and GELDIUM_SENDER_PASSWORD in .env"
        )
        return False

    if not receiver_email:
        logger.warning("No receiver email set. User must configure it in the dashboard.")
        return False

    sender = get_sender_info()

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{sender['name']} <{sender['email']}>"
        msg["To"]      = f"{receiver_name} <{receiver_email}>"

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(sender["email"], sender["password"])
            server.sendmail(sender["email"], receiver_email, msg.as_string())

        logger.info(f"✅ Email sent to {receiver_name} <{receiver_email}>: {subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("Authentication failed. Check GELDIUM_SENDER_PASSWORD in .env.")
        return False

    except smtplib.SMTPConnectError:
        logger.error("Could not connect to Gmail SMTP. Check internet connection.")
        return False

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


# ── EMAIL TEMPLATES ───────────────────────────────────────────────────────────

def send_high_risk_alert(
    customer_index: int,
    risk_score: float,
    confidence: float,
    intervention: str,
    explanation: str,
    receiver_email: str,
    receiver_name: str = "Collections Agent"
) -> bool:
    """Send a high-risk alert with AI explanation to the configured receiver."""

    timestamp   = datetime.now().strftime("%d %B %Y at %H:%M")
    sender_name = os.getenv("GELDIUM_SENDER_NAME", "Geldium Collections Team")

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #c0392b; padding: 20px; border-radius: 8px 8px 0 0;">
            <h2 style="color: white; margin: 0;">🔴 HIGH RISK ALERT — Immediate Action Required</h2>
            <p style="color: #fadbd8; margin: 5px 0 0 0;">{sender_name} — {timestamp}</p>
        </div>
        <div style="background-color: #f9f9f9; padding: 25px; border: 1px solid #ddd;">
            <p>Dear <strong>{receiver_name}</strong>,</p>
            <p>A customer has been flagged as <strong>HIGH RISK</strong> by the Geldium AI model.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #c0392b; color: white;">
                    <th style="padding: 10px; text-align: left;">Field</th>
                    <th style="padding: 10px; text-align: left;">Value</th>
                </tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #eee;">Customer Index</td><td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>#{customer_index}</strong></td></tr>
                <tr style="background-color: #fef9f9;"><td style="padding: 10px; border-bottom: 1px solid #eee;">Risk Score</td><td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>{risk_score * 100:.1f}%</strong></td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #eee;">Confidence</td><td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>{confidence * 100:.1f}%</strong></td></tr>
                <tr style="background-color: #fef9f9;"><td style="padding: 10px;">Action</td><td style="padding: 10px;"><strong>{intervention}</strong></td></tr>
            </table>
            <div style="background-color: #eaf4fb; border-left: 4px solid #2e86c1; padding: 15px; border-radius: 4px; margin: 20px 0;">
                <strong>🤖 AI Risk Explanation:</strong>
                <p style="margin: 8px 0 0 0;">{explanation}</p>
            </div>
            <div style="background-color: #fadbd8; border-left: 4px solid #c0392b; padding: 15px; border-radius: 4px;">
                <strong>⚠️ Human Review Required within 24 hours.</strong>
            </div>
        </div>
        <div style="background-color: #eee; padding: 12px; text-align: center; border-radius: 0 0 8px 8px;">
            <small style="color: #888;">{sender_name} — Automated Alert</small>
        </div>
    </body>
    </html>
    """

    return send_email(
        subject=f"🔴 HIGH RISK ALERT — Customer #{customer_index}",
        html_body=html_body,
        receiver_email=receiver_email,
        receiver_name=receiver_name
    )


def send_daily_summary(
    summary: dict,
    receiver_email: str,
    receiver_name: str = "Collections Agent"
) -> bool:
    """Send the daily summary report to the configured receiver."""

    timestamp   = datetime.now().strftime("%d %B %Y at %H:%M")
    sender_name = os.getenv("GELDIUM_SENDER_NAME", "Geldium Collections Team")

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #1a5276; padding: 20px; border-radius: 8px 8px 0 0;">
            <h2 style="color: white; margin: 0;">📊 Daily Collections Risk Report</h2>
            <p style="color: #aed6f1; margin: 5px 0 0 0;">{sender_name} — {timestamp}</p>
        </div>
        <div style="background-color: #f9f9f9; padding: 25px; border: 1px solid #ddd;">
            <p>Dear <strong>{receiver_name}</strong>,</p>
            <p>Here is today's automated collections risk summary.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background-color: #1a5276; color: white;">
                    <th style="padding: 12px; text-align: left;">Metric</th>
                    <th style="padding: 12px; text-align: center;">Count</th>
                </tr>
                <tr><td style="padding: 12px; border-bottom: 1px solid #eee;">Total Scored</td><td style="padding: 12px; text-align: center; border-bottom: 1px solid #eee;"><strong>{summary['total']}</strong></td></tr>
                <tr style="background-color: #fdedec;"><td style="padding: 12px; border-bottom: 1px solid #eee;">🔴 High Risk</td><td style="padding: 12px; text-align: center; border-bottom: 1px solid #eee;"><strong style="color: #c0392b;">{summary['high']}</strong></td></tr>
                <tr style="background-color: #fef9e7;"><td style="padding: 12px; border-bottom: 1px solid #eee;">🟡 Medium Risk</td><td style="padding: 12px; text-align: center; border-bottom: 1px solid #eee;"><strong style="color: #d68910;">{summary['medium']}</strong></td></tr>
                <tr style="background-color: #eafaf1;"><td style="padding: 12px; border-bottom: 1px solid #eee;">🟢 Low Risk</td><td style="padding: 12px; text-align: center; border-bottom: 1px solid #eee;"><strong style="color: #1e8449;">{summary['low']}</strong></td></tr>
                <tr><td style="padding: 12px;">⏱️ Run Time</td><td style="padding: 12px; text-align: center;">{summary['run_time']}</td></tr>
            </table>
            {'<div style="background-color: #fadbd8; border-left: 4px solid #c0392b; padding: 15px; border-radius: 4px;"><strong>⚠️ Errors:</strong><p>' + str(summary["errors"]) + '</p></div>' if summary["errors"] else '<div style="background-color: #eafaf1; border-left: 4px solid #27ae60; padding: 15px; border-radius: 4px;"><strong>✅ No errors.</strong></div>'}
        </div>
        <div style="background-color: #eee; padding: 12px; text-align: center; border-radius: 0 0 8px 8px;">
            <small style="color: #888;">{sender_name} — Daily Report</small>
        </div>
    </body>
    </html>
    """

    return send_email(
        subject=f"📊 Geldium Daily Risk Report — {datetime.now().strftime('%d %b %Y')}",
        html_body=html_body,
        receiver_email=receiver_email,
        receiver_name=receiver_name
    )