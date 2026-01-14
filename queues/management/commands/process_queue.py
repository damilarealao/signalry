# queues/management/commands/process_queue.py
from django.core.management.base import BaseCommand
from queues.services import run_message_queue

class Command(BaseCommand):
    help = "Process queued messages"

    def handle(self, *args, **options):
        result = run_message_queue()
        self.stdout.write(self.style.SUCCESS(
            f"Processed={result['processed']} "
            f"Sent={result['sent']} "
            f"Failed={result['failed']}"
        ))
