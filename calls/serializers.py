from rest_framework import serializers
from .models import Room

class RoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'room_name', 'meeting_date', 'description']
        read_only_fields = ['id']

class RoomDetailSerializer(serializers.ModelSerializer):
    host = serializers.StringRelatedField()

    class Meta:
        model = Room
        fields = ['id', 'room_name', 'host', 'meeting_date', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'host', 'is_active', 'created_at']