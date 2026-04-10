from django.db import models
from users.models import User

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

# ConversationReadStatus: Needed because each user has its own message up to where they have read
class ConversationReadStatus(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_statuses')
    last_read_message_id = models.IntegerField(default=0)

    class Meta:
        unique_together = (('conversation', 'user'),)

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
