from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import InterviewSession, Message
import logging
from .serializers import (
    InterviewSessionSerializer, 
    InterviewSessionDetailSerializer, 
    MessageSerializer,
)

logger = logging.getLogger(__name__)

class InterviewSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = InterviewSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InterviewSession.objects.filter(user = self.request.user)
    
    def perform_create(self , serializer):
        session = serializer.save(user=self.request.user)
        # Generic openning message maybe this will change (but later)
        opening = 'how may i assist you today'
        Message.objects.create(session=session , role=Message.Role.Assistant , content = opening)

class InterviewSessionDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InterviewSessionDetailSerializer

    def get_queryset(self):
        return InterviewSession.objects.filter(user=self.request.user)

class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    # find the session were in
    def get_session(self):
        return generics.get_object_or_404(
            InterviewSession,
            id=self.kwargs['session_id'],
            user=self.request.user
        )

    # get all the messages
    def get_queryset(self):
        return self.get_session().messages.all()

    def create(self, request, *args, **kwargs):
        session = self.get_session()

        content = request.data.get('content')

        if not content :
            logger.error("containt cant be empty")
            return Response({"error": "content is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Save user message
        user_msg = Message.objects.create(
            session=session,
            role=Message.Role.USER,
            content=request.data.get('content')
        )

        return Response(MessageSerializer(user_msg).data, status=status.HTTP_201_CREATED)
    