from django.db import models
from users.models import User

# a room can only be created by an employer 
# so effectively only employers can create rooms
class Room(models.Model):
    room_name = models.CharField(max_length=100)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    meeting_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=False)
    participants = models.ManyToManyField(User , related_name='participants_room')

    def __str__(self):
        return self.room_name
