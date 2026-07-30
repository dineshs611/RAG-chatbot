import smtplib
import socket
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("EduRAG.Emailer")

def test_smtp_connection(server_host, port, username, password, sender_email) -> tuple:
    """
    Test connection to SMTP server and return diagnostic results.
    Returns (success: bool, detail_message: str)
    """
    if not username or not password:
        return False, "⚠️ Missing Username or Password. Please fill in both fields."
        
    try:
        port = int(port)
    except ValueError:
        port = 587

    try:
        if port == 465:
            # SSL Connection
            server = smtplib.SMTP_SSL(server_host, port, timeout=12)
        else:
            # TLS Connection (Port 587 / 25)
            server = smtplib.SMTP(server_host, port, timeout=12)
            server.starttls()
            
        server.login(username, password)
        server.quit()
        return True, f"✅ Connection Successful! Verified SMTP authentication for {username}."
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Auth error: {e}")
        return False, (
            "❌ Authentication Failed (535 Error).\n\n"
            "If using Gmail or Outlook, you CANNOT use your normal login password.\n"
            "You MUST generate a 16-character 'App Password' from your Google Account Security settings."
        )
    except (socket.timeout, TimeoutError):
        return False, f"❌ Connection Timed Out connecting to {server_host}:{port}. Check server host and port."
    except Exception as e:
        return False, f"❌ SMTP Connection Error: {e}"

def send_password_reset_email(to_email: str, username: str, temp_password: str) -> tuple:
    """
    Sends a temporary password reset email to a student.
    Returns (success: bool, status_message: str)
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        smtp_port = 587
        
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    sender_email = os.getenv("SENDER_EMAIL", smtp_user or "no-reply@edurag.ai").strip()

    if not to_email or "@" not in to_email:
        return False, f"❌ Invalid recipient email address: '{to_email}'."

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

    # If SMTP credentials are configured
    if smtp_user and smtp_password:
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=12)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=12)
                server.starttls()

            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, [to_email], msg.as_string())
            server.quit()
            logger.info(f"Email sent successfully to {to_email}")
            return True, f"📧 Email successfully delivered to student inbox ({to_email})."
        except smtplib.SMTPAuthenticationError as e:
            err_msg = (
                f"❌ Could not send email to {to_email} due to Authentication Error (535).\n"
                "Google/Outlook requires a 16-character 'App Password' instead of your regular password."
            )
            logger.error(err_msg)
            return False, err_msg
        except Exception as e:
            err_msg = f"❌ Failed to send email to {to_email}: {e}"
            logger.error(err_msg)
            return False, err_msg
    else:
        # Simulation Mode
        msg = f"⚠️ Email Simulation Mode: Password set to '{temp_password}'. (To send real emails to {to_email}, configure SMTP_USER & SMTP_PASSWORD above)."
        logger.info(msg)
        return False, msg
