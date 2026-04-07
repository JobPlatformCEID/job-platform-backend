from django.db import models
from django.utils import timezone
from users.models import User

# a room can only be created by an employer 
# so effectively only employers can create rooms
class Room(models.Model):
    room_name = models.CharField(max_length=100)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    meeting_date = models.DateTimeField()
    description = models.TextField()
    is_active = models.BooleanField(default=False)

    def is_time_to_start(self):
        """Check if the meeting time has arrived"""
        return timezone.now() >= self.meeting_date
