# queues/models.py
from django.db import models
from django.utils import timezone


class QueueJob(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    job_type = models.CharField(max_length=50)
    payload = models.JSONField()
    priority = models.IntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    retry_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    scheduled_for = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job_type} ({self.status}) - {self.user.email}"


class Queue(models.Model):
    name = models.CharField(max_length=50)
    timeout = models.PositiveIntegerField(default=60)
    max_retries = models.PositiveIntegerField(default=3)
    backoff = models.PositiveIntegerField(default=5)
    priority = models.PositiveSmallIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
