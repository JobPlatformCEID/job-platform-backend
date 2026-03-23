from rest_framework import serializers
from .models import Conversation, Message
from users.models import User

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender', 'conversation', 'created_at', 'is_read']

class ConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'created_at', 'last_message', 'other_user']
        read_only_fields = ['created_at', 'participants']

    def get_last_message(self, obj):
        last = obj.messages.last()
        if last:
            return MessageSerializer(last).data
        return None

    def get_other_user(self, obj):
        request = self.context.get('request')
        other = obj.participants.exclude(id=request.user.id).first()
        if other:
            return {'id': other.id, 'username': other.username}
        return None
