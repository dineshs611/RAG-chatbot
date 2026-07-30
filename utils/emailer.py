import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("EduRAG.Emailer")

def send_password_reset_email(to_email: str, username: str, temp_password: str) -> tuple:
    """
    Sends a temporary password reset email to a student.
    Uses SMTP parameters from environment variables (.env).
    Returns (success: bool, status_message: str)
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        smtp_port = 587
        
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    sender_email = os.getenv("SENDER_EMAIL", smtp_user or "no-reply@edurag.ai").strip()

    subject = "🎓 EduRAG AI Assistant - Your Password Has Been Reset"
    
    body = f"""Hello {username},

An Administrator has generated a temporary password for your EduRAG AI Assistant account.

Here are your new login details:
------------------------------------------
Username: {username}
Email: {to_email}
Temporary Password: {temp_password}
------------------------------------------

Please log in at your earliest convenience and update your password under Settings.

Best regards,
EduRAG AI Assistant Team
"""

    # If real SMTP credentials are provided in .env
    if smtp_user and smtp_password:
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, [to_email], msg.as_string())
            server.quit()
            logger.info(f"Email sent successfully to {to_email}")
            return True, f"📧 Email successfully sent to {to_email}."
        except Exception as e:
            logger.error(f"SMTP delivery error to {to_email}: {e}")
            return False, f"Password reset in database, but SMTP email delivery failed ({e})."
    else:
        # Simulated email mode if SMTP keys are not yet configured in .env
        logger.info(f"[EMAIL SIMULATION] Sent temp password to {to_email}")
        return True, f"📧 Email notification dispatched to {to_email}. (To send real emails, set SMTP_USER & SMTP_PASSWORD in .env)"
