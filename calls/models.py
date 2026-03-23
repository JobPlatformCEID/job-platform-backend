from django.db import models
from users import User , EmployerProfile

# a room can only be created by an employer 
# so effectively only employers can create rooms
class Room(models.Model):
    room_name = models.CharField(max_length=100)
    host = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name='hosted_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    meeting_date = models.DateTimeField()
    description = models.TextField()
    is_active = models.BooleanField(default=False)
