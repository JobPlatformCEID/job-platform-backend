from rest_framework import serializers
from .models import(
    InterviewSession, InterviewMessage
)
from jobs.models import JobPosting

# send and get messages
class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewMessage
        fields = ['id', 'role', 'content', 'created_at']
        read_only_fields = ['id' , 'created_at']

# create a session
class InterviewSessionSerializer(serializers.ModelSerializer):
    job_posting = serializers.PrimaryKeyRelatedField(read_only=True)
    job_title = serializers.CharField(source='job_posting.title', read_only=True)
    job_posting_id = serializers.PrimaryKeyRelatedField(
        source='job_posting',
        queryset=JobPosting.objects.all(),
        write_only=True,
    )

    class Meta:
        model = InterviewSession
        fields = ['id', 'title', 'job_posting', 'job_title', 'job_posting_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

# see details of a session (includes full message history now)
class InterviewSessionDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    job_posting = serializers.PrimaryKeyRelatedField(read_only=True)
    job_title = serializers.CharField(source='job_posting.title', read_only=True)

    class Meta:
        model = InterviewSession
        fields = ['id', 'title', 'job_posting', 'job_title', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['id', 'created_at', 'updated_at', 'job_posting']
