from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.contrib.postgres.fields import ArrayField
import uuid
import json

class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.JSONField(null=True, blank=True)
    version = models.IntegerField(default=1)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_time})"

class EventPermission(models.Model):
    class Role(models.TextChoices):
        OWNER = 'OWNER', _('Owner')
        EDITOR = 'EDITOR', _('Editor')
        VIEWER = 'VIEWER', _('Viewer')

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_permissions')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('event', 'user')
        indexes = [
            models.Index(fields=['event', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.role} - {self.event.title}"

class EventVersion(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    data = models.JSONField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    change_reason = models.TextField(blank=True)

    class Meta:
        unique_together = ('event', 'version_number')
        ordering = ['-version_number']
        indexes = [
            models.Index(fields=['event', 'version_number']),
        ]

    def __str__(self):
        return f"{self.event.title} - Version {self.version_number}"

class EventChangeLog(models.Model):
    class ChangeType(models.TextChoices):
        CREATE = 'CREATE', _('Create')
        UPDATE = 'UPDATE', _('Update')
        DELETE = 'DELETE', _('Delete')
        SHARE = 'SHARE', _('Share')
        PERMISSION_CHANGE = 'PERMISSION_CHANGE', _('Permission Change')

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='changelog')
    version = models.ForeignKey(EventVersion, on_delete=models.CASCADE, related_name='changelog_entries')
    change_type = models.CharField(max_length=20, choices=ChangeType.choices)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    changed_at = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField()  # Stores the diff of changes
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['event', 'changed_at']),
            models.Index(fields=['change_type']),
        ]

    def __str__(self):
        return f"{self.change_type} - {self.event.title} - {self.changed_at}"

class EventConflict(models.Model):
    class ResolutionStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        RESOLVED = 'RESOLVED', _('Resolved')
        IGNORED = 'IGNORED', _('Ignored')

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='conflicts')
    conflicting_event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='conflicted_by')
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_status = models.CharField(
        max_length=10,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.PENDING
    )
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='resolved_conflicts'
    )

    class Meta:
        unique_together = ('event', 'conflicting_event')
        indexes = [
            models.Index(fields=['event', 'conflicting_event']),
            models.Index(fields=['resolution_status']),
        ]

    def __str__(self):
        return f"Conflict between {self.event.title} and {self.conflicting_event.title}"
