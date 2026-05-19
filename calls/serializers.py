from rest_framework import serializers
from .models import Room

class RoomSerializer(serializers.ModelSerializer):
    host_username = serializers.CharField(source='host.username', read_only=True)
    is_participant = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ['id', 'room_name', 'description', 'is_active', 'meeting_date', 'created_at', 'host', 'host_username', 'is_participant']
        read_only_fields = ['host', 'created_at', 'is_active']

    def get_is_participant(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.participants.filter(id=request.user.id).exists()
        return False
