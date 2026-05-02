from django.db import models
from users.models import User
from jobs.models import JobPosting

# Create your models here.

# these will be the chats
class InterviewSession(models.Model):
    user = models.ForeignKey(User , on_delete=models.CASCADE ,related_name='interview_session' )
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='interview_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=50, default='')

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.job_posting.title}"

# these will be the chat messages
class InterviewMessage(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        Assistant = 'assistant', 'Assistant'

    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
