from rest_framework import serializers
from .models import Room

class RoomCreateSerializer(serializers.ModelSerializer):
    host = serializers.StringRelatedField(read_only=True)
    host_id = serializers.IntegerField(source='host.id', read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'room_name', 'host', 'host_id', 'meeting_date', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'host', 'host_id', 'is_active', 'created_at']

class RoomDetailSerializer(serializers.ModelSerializer):
    host = serializers.StringRelatedField()
    host_id = serializers.IntegerField(source='host.id', read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'room_name', 'host', 'host_id', 'meeting_date', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'host', 'host_id', 'is_active', 'created_at']