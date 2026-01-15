# campaigns/tasks.py - UPDATED VERSION with tracking pixel
import smtplib
import logging
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.utils import timezone
from django.conf import settings
import socket
import ssl

logger = logging.getLogger(__name__)


def send_campaign_emails(campaign_id, limit=None):
    """
    SIMPLE VERSION: Send emails for a campaign.
    This runs synchronously in the same thread as the web request.
    """
    try:
        from campaigns.models import Campaign
        campaign = Campaign.objects.get(id=campaign_id)
        
        # Check if campaign should be sent
        if campaign.status != 'active':
            logger.warning(f"Campaign {campaign_id} is not active. Status: {campaign.status}")
            return 0, 0
        
        if campaign.scheduled_at and campaign.scheduled_at > timezone.now():
            logger.warning(f"Campaign {campaign_id} scheduled for future: {campaign.scheduled_at}")
            return 0, 0
        
        # Get the campaign's message
        message = campaign.messages.first()
        if not message:
            logger.error(f"Campaign {campaign_id} has no message")
            return 0, 0
        
        # Ensure message has a UUID for tracking
        if not message.uuid:
            message.uuid = str(uuid.uuid4())
            message.save(update_fields=['uuid'])
            logger.info(f"Generated UUID for message {message.id}: {message.uuid}")
        
        # Get pending recipients
        recipients = message.recipients.filter(status='pending')
        if limit:
            recipients = recipients[:limit]
        
        sent_count = 0
        failed_count = 0
        
        for recipient in recipients:
            try:
                # Send email
                success = send_single_email(recipient)
                
                if success:
                    sent_count += 1
                    recipient.mark_sent()
                    logger.info(f"Sent to {recipient.contact.email}")
                else:
                    failed_count += 1
                    recipient.mark_failed("Send failed")
                    logger.error(f"Failed to send to {recipient.contact.email}")
                    
            except Exception as e:
                failed_count += 1
                recipient.mark_failed(str(e))
                logger.error(f"Error sending to {recipient.contact.email}: {str(e)}")
        
        # Simple status update
        if sent_count > 0 and failed_count == 0:
            campaign.status = 'completed'
            campaign.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"Campaign {campaign_id}: Sent {sent_count}, Failed {failed_count}")
        return sent_count, failed_count
        
    except Exception as e:
        logger.error(f"Error sending campaign {campaign_id}: {str(e)}")
        return 0, 0


def send_single_email(recipient):
    """
    Send a single email to a recipient with tracking pixel.
    """
    message = recipient.message
    contact = recipient.contact
    campaign = message.campaign
    
    # Get SMTP settings
    smtp_account = message.sender_smtp
    if not smtp_account:
        from smtp.models import SMTPAccount
        smtp_account = SMTPAccount.objects.filter(
            user=campaign.user,
            status='active'
        ).first()
    
    if not smtp_account:
        logger.error(f"No active SMTP account for campaign {campaign.id}")
        return False
    
    try:
        # Create email message
        email_msg = MIMEMultipart('alternative')
        email_msg['Subject'] = message.subject
        
        # Get FROM name from settings or use default
        from_name = getattr(settings, 'EMAIL_FROM_NAME', 'Signalry')
        
        # Format From header properly
        if '@' in smtp_account.smtp_user:
            email_msg['From'] = f'"{from_name}" <{smtp_account.smtp_user}>'
        else:
            # If smtp_user is just username without domain, add domain
            email_msg['From'] = f'"{from_name}" <{smtp_account.smtp_user}@{smtp_account.smtp_host}>'
        
        email_msg['To'] = contact.email
        
        # ===== SMART SITE URL DETECTION =====
        # Use SITE_URL from settings
        site_url = getattr(settings, 'SITE_URL', '')
        
        if not site_url:
            # Try to get it dynamically in development
            if settings.DEBUG:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    server_ip = s.getsockname()[0]
                    s.close()
                    site_url = f'http://{server_ip}:8000'
                    logger.warning(f"No SITE_URL in settings, using auto-detected: {site_url}")
                except:
                    logger.error("Cannot determine site URL for unsubscribe links")
                    return False
            else:
                logger.error("SITE_URL is not configured in settings")
                return False
            
        # Log which URL we're using
        logger.info(f"Using SITE_URL: {site_url}")
        
        # Build unsubscribe URL
        unsubscribe_url = f"{site_url.rstrip('/')}/api/messages/contacts/{contact.pk}/unsubscribe/"
        
        # ===== TRACKING PIXEL URL =====
        # Generate tracking pixel URL with recipient ID
        tracking_pixel_url = f"{site_url.rstrip('/')}/api/messages/t/{message.uuid}.png?recipient={recipient.id}"
        logger.info(f"Tracking pixel URL for recipient {recipient.id}: {tracking_pixel_url}")
        
        # Build email content
        plain_text = message.body_plain
        
        # Add unsubscribe link to plain text
        plain_text += f"\n\n---\nTo unsubscribe, visit: {unsubscribe_url}"
        
        # Create HTML version with tracking pixel
        if message.body_html:
            html_content = message.body_html
            # Add tracking pixel (hidden 1x1 image)
            html_content += f'<img src="{tracking_pixel_url}" width="1" height="1" style="display:none; opacity:0;" alt=""/>'
            # Add unsubscribe link to HTML
            html_content += f'<p style="color: #666; font-size: 12px; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px;">'
            html_content += f'<a href="{unsubscribe_url}" style="color: #666;">Unsubscribe</a>'
            html_content += '</p>'
        else:
            # Create basic HTML from plain text
            # Replace newlines outside the f-string to avoid backslash issues
            html_text = plain_text.replace('\n', '<br>')
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .content {{ background: #f9f9f9; padding: 20px; border-radius: 5px; }}
                    .footer {{ margin-top: 20px; padding-top: 10px; border-top: 1px solid #eee; color: #666; font-size: 12px; }}
                    .tracking-pixel {{ display: none; opacity: 0; }}
                </style>
            </head>
            <body>
                <div class="content">
                    {html_text}
                </div>
                <div class="footer">
                    <a href="{unsubscribe_url}">Unsubscribe</a>
                </div>
                <!-- Tracking Pixel -->
                <img src="{tracking_pixel_url}" width="1" height="1" class="tracking-pixel" alt=""/>
            </body>
            </html>
            """
        
        # Attach both parts
        email_msg.attach(MIMEText(plain_text, 'plain'))
        email_msg.attach(MIMEText(html_content, 'html'))
        
        # Send via SMTP
        return send_via_smtp(smtp_account, email_msg, contact.email)
        
    except Exception as e:
        logger.error(f"Error sending to {contact.email}: {str(e)}", exc_info=True)
        return False


def send_via_smtp(smtp_account, email_msg, to_email):
    """
    Simple SMTP sending.
    """
    try:
        # FIX: SMTPAccount has different field names
        host = smtp_account.smtp_host
        port = smtp_account.smtp_port
        username = smtp_account.smtp_user
        password = smtp_account.get_password()
        
        if not password:
            logger.error(f"Failed to get password for SMTP account {smtp_account.id}")
            return False
        
        # Always use TLS for security (assume port 587 for TLS, 465 for SSL)
        if port == 465:
            # SSL connection
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context) as server:
                server.login(username, password)
                server.send_message(email_msg)
                logger.debug(f"Email sent via SSL to {to_email}")
                return True
        else:
            # TLS connection (default for port 587)
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(username, password)
                server.send_message(email_msg)
                logger.debug(f"Email sent via TLS to {to_email}")
                return True
                
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication error to {to_email}: {str(e)}")
        # Mark SMTP account as failed
        smtp_account.mark_failure()
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error to {to_email}: {str(e)}")
        smtp_account.mark_failure()
        return False
    except Exception as e:
        logger.error(f"Error sending to {to_email}: {str(e)}")
        return False


# Helper function to get current site URL (can be used elsewhere)
def get_current_site_url():
    """
    Get the current site URL for use in templates or other functions.
    """
    site_url = getattr(settings, 'SITE_URL', '')
    if not site_url and settings.DEBUG:
        # Try to get it dynamically in development
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            server_ip = s.getsockname()[0]
            s.close()
            site_url = f'http://{server_ip}:8000'
        except:
            site_url = ''
    return site_url