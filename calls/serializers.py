from rest_framework import serializers
from .models import Room

class RoomSerializer(serializers.ModelSerializer):
    host_username = serializers.CharField(source='host.username', read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'room_name', 'description', 'meeting_date', 'created_at', 'host', 'host_username']
        read_only_fields = ['host', 'created_at']
