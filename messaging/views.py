from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from users.models import User

# Create your views here.
class ConversationListCreateView(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)

    def create(self, request, *args, **kwargs):
        other_user_id = request.data.get('user_id')
        if not other_user_id:
            raise ValidationError('user_id is required.')
        try:
            other_user = User.objects.get(pk=other_user_id)
        except User.DoesNotExist:
            raise NotFound('User not found.')
        if other_user == request.user:
            raise ValidationError('You cannot start a conversation with yourself.')
        existing = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        )
        if existing.exists():
            serializer = self.get_serializer(existing.first())
            return Response(serializer.data, status=status.HTTP_200_OK)
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs.get('pk')
        try:
            conversation = Conversation.objects.get(pk=conversation_id)
        except Conversation.DoesNotExist:
            raise NotFound('Conversation not found.')
        if self.request.user not in conversation.participants.all():
            raise PermissionDenied('You are not a participant of this conversation.')
        return Message.objects.filter(conversation=conversation)

class ConversationDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            conversation = Conversation.objects.get(pk=self.kwargs.get('pk'))
        except Conversation.DoesNotExist:
            raise NotFound('Conversation not found.')
        if self.request.user not in conversation.participants.all():
            raise PermissionDenied('You are not a participant of this conversation.')
        return conversation

class MessageDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only allow querying messages from conversations the user is participating in
        return Message.objects.filter(conversation__participants=self.request.user)

    def get_object(self):
        try:
            message = self.get_queryset().get(
                pk=self.kwargs.get('message_pk'),
                conversation_id=self.kwargs.get('pk')
            )
        except Message.DoesNotExist:
            raise NotFound('Message not found.')
        if message.sender != self.request.user:
            raise PermissionDenied('You can only delete your own messages.')
        return message
