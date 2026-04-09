"""
models.py — minimal Room model.
LiveKit auto-creates the room server-side when the first participant joins.
"""

from django.db import models
from django.conf import settings


class Room(models.Model):
    room_name    = models.CharField(max_length=255)
    description  = models.TextField(blank=True)
    meeting_date = models.DateTimeField(null=True, blank=True)
    host         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hosted_rooms",
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            "id":           self.pk,
            "room_name":    self.room_name,
            "description":  self.description,
            "host":         self.host.username,
            "meeting_date": self.meeting_date.isoformat() if self.meeting_date else "",
            "created_at":   self.created_at.isoformat(),
        }

    def __str__(self):
        return self.room_name