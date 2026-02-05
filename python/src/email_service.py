#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Email service for sending validation reports."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from models import ValidationReport
from report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email reports."""
    
    def __init__(
        self,
        smtp_server: str = "localhost",
        smtp_port: int = 25,
        from_address: str = "recovery-validation@cyberres.com"
    ):
        """Initialize email service.
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            from_address: From email address
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.from_address = from_address
        self.report_generator = ReportGenerator()
    
    def send_validation_report(
        self,
        report: ValidationReport,
        recipient: str,
        include_text: bool = True
    ) -> bool:
        """Send validation report via email.
        
        Args:
            report: Validation report to send
            recipient: Email recipient address
            include_text: Include plain text version
        
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Recovery Validation Report - {report.result.resource_type.value.upper()} - {report.result.overall_status.value}"
            msg['From'] = self.from_address
            msg['To'] = recipient
            
            # Generate reports
            if include_text:
                text_report = self.report_generator.generate_text_report(report)
                text_part = MIMEText(text_report, 'plain')
                msg.attach(text_part)
            
            html_report = self.report_generator.generate_html_report(report)
            html_part = MIMEText(html_report, 'html')
            msg.attach(html_part)
            
            # Send email
            logger.info(f"Sending validation report to {recipient}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.send_message(msg)
            
            logger.info(f"Validation report sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def send_simple_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        is_html: bool = False
    ) -> bool:
        """Send a simple email.
        
        Args:
            recipient: Email recipient address
            subject: Email subject
            body: Email body
            is_html: Whether body is HTML
        
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            msg = MIMEText(body, 'html' if is_html else 'plain')
            msg['Subject'] = subject
            msg['From'] = self.from_address
            msg['To'] = recipient
            
            logger.info(f"Sending email to {recipient}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

# Made with Bob
