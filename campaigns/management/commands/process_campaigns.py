# campaigns/management/commands/process_campaigns.py
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from campaigns.models import Campaign
from campaigns.tasks import send_campaign_emails, retry_failed_emails, check_campaign_status
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process and send scheduled campaigns, retry failed emails, and update campaign statuses'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit-per-campaign',
            type=int,
            default=100,
            help='Limit number of emails to send per campaign per run (default: 100)'
        )
        parser.add_argument(
            '--max-retries',
            type=int,
            default=3,
            help='Maximum number of retry attempts for failed emails (default: 3)'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously (daemon mode)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Interval in seconds between runs in continuous mode (default: 60)'
        )
        parser.add_argument(
            '--only-retry',
            action='store_true',
            help='Only retry failed emails, don\'t send new ones'
        )
        parser.add_argument(
            '--only-check-status',
            action='store_true',
            help='Only check and update campaign statuses'
        )
        parser.add_argument(
            '--campaign-id',
            type=int,
            help='Process only a specific campaign ID'
        )
    
    def handle(self, *args, **options):
        limit = options['limit_per_campaign']
        max_retries = options['max_retries']
        continuous = options['continuous']
        interval = options['interval']
        only_retry = options['only_retry']
        only_check_status = options['only_check_status']
        campaign_id = options['campaign_id']
        
        if continuous:
            self.stdout.write(self.style.SUCCESS(
                f'Starting continuous campaign processor (interval: {interval}s)...'
            ))
            try:
                while True:
                    self._process_run(limit, max_retries, only_retry, only_check_status, campaign_id)
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\nStopped by user'))
        else:
            self._process_run(limit, max_retries, only_retry, only_check_status, campaign_id)
    
    def _process_run(self, limit, max_retries, only_retry, only_check_status, campaign_id):
        """Execute a single processing run."""
        start_time = timezone.now()
        self.stdout.write(f"Processing campaigns at {start_time}")
        
        # Initialize counters
        total_sent = 0
        total_failed = 0
        campaigns_processed = 0
        retried_count = 0
        retry_success_count = 0
        status_checked = 0
        
        try:
            # 1. CHECK AND UPDATE CAMPAIGN STATUSES
            if not only_retry:
                status_checked = self._check_campaign_statuses(campaign_id)
            
            # 2. RETRY FAILED EMAILS
            if not only_check_status:
                retried_count, retry_success_count = self._retry_failed_emails(max_retries, campaign_id)
            
            # 3. SEND NEW CAMPAIGNS
            if not only_retry and not only_check_status:
                campaigns, sent, failed = self._send_new_campaigns(limit, campaign_id)
                campaigns_processed = len(campaigns)
                total_sent += sent
                total_failed += failed
            
            # Calculate duration
            duration = (timezone.now() - start_time).total_seconds()
            
            # Display summary
            self._display_summary(
                duration, campaigns_processed, total_sent, total_failed,
                retried_count, retry_success_count, status_checked
            )
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error in processing run: {str(e)}"))
            logger.error(f"Error in campaign processing: {str(e)}", exc_info=True)
    
    def _check_campaign_statuses(self, campaign_id=None):
        """Check and update campaign statuses."""
        self.stdout.write("Checking campaign statuses...")
        
        if campaign_id:
            campaigns = Campaign.objects.filter(id=campaign_id)
        else:
            # Get campaigns that are active or have recipients
            campaigns = Campaign.objects.filter(
                Q(status__in=['active', 'draft', 'paused']) |
                Q(messages__recipients__isnull=False)
            ).distinct()
        
        count = 0
        for campaign in campaigns:
            try:
                check_campaign_status(campaign.id)
                count += 1
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"Error checking campaign {campaign.id}: {str(e)}"))
        
        self.stdout.write(f"  Checked {count} campaigns")
        return count
    
    def _retry_failed_emails(self, max_retries, campaign_id=None):
        """Retry sending failed emails."""
        self.stdout.write(f"Retrying failed emails (max retries: {max_retries})...")
        
        try:
            retried_count, success_count = retry_failed_emails(campaign_id, max_retries)
            self.stdout.write(f"  Retried {retried_count} emails, {success_count} successful")
            return retried_count, success_count
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error retrying failed emails: {str(e)}"))
            return 0, 0
    
    def _send_new_campaigns(self, limit, campaign_id=None):
        """Send emails for campaigns that are ready to send."""
        self.stdout.write(f"Sending new campaigns (limit: {limit} per campaign)...")
        
        now = timezone.now()
        
        # Build query for campaigns that should be sent
        query = Q(
            status='active',
            scheduled_at__lte=now
        )
        
        if campaign_id:
            query &= Q(id=campaign_id)
        
        campaigns = Campaign.objects.filter(query).distinct()
        
        total_sent = 0
        total_failed = 0
        processed_campaigns = []
        
        for campaign in campaigns:
            try:
                # Check if campaign has message and recipients
                if not campaign.has_message_content():
                    self.stdout.write(self.style.WARNING(
                        f"  Campaign {campaign.id} ({campaign.name}) has no message content"
                    ))
                    continue
                
                if not campaign.has_recipients():
                    self.stdout.write(self.style.WARNING(
                        f"  Campaign {campaign.id} ({campaign.name}) has no recipients"
                    ))
                    continue
                
                self.stdout.write(f"  Processing: {campaign.name} (ID: {campaign.id})")
                
                # Send emails for this campaign
                sent, failed = send_campaign_emails(campaign.id, limit)
                
                total_sent += sent
                total_failed += failed
                processed_campaigns.append(campaign)
                
                if sent > 0 or failed > 0:
                    self.stdout.write(f"    Sent: {sent}, Failed: {failed}")
                else:
                    self.stdout.write(f"    No emails to send")
                    
                # Check if campaign is now completed
                if campaign.get_sent_count() >= campaign.get_recipient_count() > 0:
                    self.stdout.write(self.style.SUCCESS(
                        f"    Campaign completed!"
                    ))
                    
            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f"  Error processing campaign {campaign.id}: {str(e)}"
                ))
                logger.error(f"Error processing campaign {campaign.id}: {str(e)}", exc_info=True)
        
        self.stdout.write(f"  Processed {len(processed_campaigns)} campaigns")
        return processed_campaigns, total_sent, total_failed
    
    def _display_summary(self, duration, campaigns_processed, total_sent, total_failed,
                        retried_count, retry_success_count, status_checked):
        """Display summary of processing run."""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("PROCESSING SUMMARY")
        self.stdout.write("="*50)
        
        self.stdout.write(f"Duration: {duration:.2f} seconds")
        self.stdout.write(f"Campaigns processed: {campaigns_processed}")
        self.stdout.write(f"Campaign statuses checked: {status_checked}")
        self.stdout.write(f"Emails sent: {total_sent}")
        self.stdout.write(f"Emails failed: {total_failed}")
        self.stdout.write(f"Failed emails retried: {retried_count}")
        self.stdout.write(f"Retry successes: {retry_success_count}")
        
        if total_sent > 0 or retry_success_count > 0:
            self.stdout.write(self.style.SUCCESS("Run completed successfully!"))
        elif total_failed > 0:
            self.stdout.write(self.style.WARNING("Run completed with some failures"))
        else:
            self.stdout.write(self.style.WARNING("No emails were sent"))