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
        from_address: str = "recovery-validation@cyberres.com",
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = False
    ):
        """Initialize email service.
        
        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            from_address: From email address
            smtp_username: SMTP username for authentication (optional)
            smtp_password: SMTP password for authentication (optional)
            use_tls: Whether to use TLS encryption
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.from_address = from_address
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.report_generator = ReportGenerator()
        
        # Log SMTP configuration for debugging
        logger.info(f"EmailService initialized:")
        logger.info(f"  SMTP Server: {self.smtp_server}")
        logger.info(f"  SMTP Port: {self.smtp_port}")
        logger.info(f"  From Address: {self.from_address}")
        logger.info(f"  Use TLS: {self.use_tls}")
        logger.info(f"  Has Username: {bool(self.smtp_username)}")
        logger.info(f"  Has Password: {bool(self.smtp_password)}")
    
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
            logger.info(f"SMTP Details {self.smtp_server}")
            logger.info(f"Sending validation report to {recipient}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                    logger.debug("TLS enabled for SMTP connection")
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                    logger.info("SMTP authentication successful")
                
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
                if self.use_tls:
                    server.starttls()
                    logger.debug("TLS enabled for SMTP connection")
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                    logger.debug("SMTP authentication successful")
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def send_detailed_report(
        self,
        report_text: str,
        recipient: str,
        subject: str,
        resource_host: str
    ) -> bool:
        """Send detailed markdown report via email.
        
        Args:
            report_text: Markdown formatted report text
            recipient: Email recipient address
            subject: Email subject
            resource_host: Resource hostname for context
        
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_address
            msg['To'] = recipient
            
            # Plain text version (markdown)
            text_part = MIMEText(report_text, 'plain')
            msg.attach(text_part)
            
            # HTML version (convert markdown to HTML)
            html_content = self._markdown_to_html(report_text, resource_host)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            logger.info(f"Sending detailed report to {recipient}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                    logger.debug("TLS enabled for SMTP connection")
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                    logger.debug("SMTP authentication successful")
                
                server.send_message(msg)
            
            logger.info(f"Detailed report sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending detailed report: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending detailed report: {e}")
            return False
    
    def _markdown_to_html(self, markdown_text: str, resource_host: str) -> str:
        """Convert markdown report to HTML with styling.
        
        Args:
            markdown_text: Markdown formatted text
            resource_host: Resource hostname
        
        Returns:
            HTML formatted report
        """
        # Simple markdown to HTML conversion
        html = markdown_text
        
        # Convert headers
        html = html.replace('# ', '<h1>').replace('\n\n', '</h1>\n\n')
        html = html.replace('## ', '<h2>').replace('\n', '</h2>\n', html.count('## '))
        html = html.replace('### ', '<h3>').replace('\n', '</h3>\n', html.count('### '))
        
        # Convert bold
        import re
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        
        # Convert checkmarks and status
        html = html.replace('✅', '<span style="color: green;">✅</span>')
        html = html.replace('🔴', '<span style="color: red;">🔴</span>')
        html = html.replace('⚠️', '<span style="color: orange;">⚠️</span>')
        html = html.replace('ℹ️', '<span style="color: blue;">ℹ️</span>')
        
        # Convert tables (basic)
        lines = html.split('\n')
        in_table = False
        html_lines = []
        
        for line in lines:
            if '|' in line and not line.strip().startswith('#'):
                if not in_table:
                    html_lines.append('<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">')
                    in_table = True
                
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if all(c.replace('-', '').strip() == '' for c in cells):
                    continue  # Skip separator line
                
                html_lines.append('<tr>')
                for cell in cells:
                    html_lines.append(f'<td>{cell}</td>')
                html_lines.append('</tr>')
            else:
                if in_table:
                    html_lines.append('</table>')
                    in_table = False
                html_lines.append(line)
        
        if in_table:
            html_lines.append('</table>')
        
        html = '\n'.join(html_lines)
        
        # Wrap in HTML template
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 30px;
                }}
                h3 {{
                    color: #7f8c8d;
                }}
                table {{
                    margin: 20px 0;
                    font-size: 14px;
                }}
                td {{
                    padding: 8px;
                }}
                tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}
                .header {{
                    background-color: #3498db;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    margin: -20px -20px 20px -20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="color: white; border: none; margin: 0;">Recovery Validation Report</h1>
                <p style="margin: 5px 0;">Resource: {resource_host}</p>
            </div>
            <div class="content">
                {html}
            </div>
        </body>
        </html>
        """
        
        return html_template

# Made with Bob
