from rest_framework import serializers
from .models import InterviewSession, InterviewMessage

# send and get messages
class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewMessage
        fields = ['id', 'role', 'content', 'created_at']
        read_only_fields = ['id' , 'created_at']

# create a session
class InterviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSession
        fields = ['id', 'title', 'job_role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

# see details of a session (includes full message history now)
class InterviewSessionDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewSession
        fields = ['id', 'title', 'job_role', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['id', 'created_at', 'updated_at', 'job_role']