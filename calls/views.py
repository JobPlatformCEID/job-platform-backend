from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from livekit import api as livekit_api
from .models import Room
from .serializers import RoomSerializer
from users.models import User

class RoomListCreateView(generics.ListCreateAPIView):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Room.objects.all().order_by('meeting_date')

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('Only employers can create rooms.')
        meeting_date = serializer.validated_data.get('meeting_date')
        if meeting_date and meeting_date < timezone.now():
            raise ValidationError('Meeting date cannot be in the past.')
        serializer.save(host=self.request.user)

class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return Room.objects.get(pk=self.kwargs.get('pk'))
        except Room.DoesNotExist:
            raise NotFound('Room not found.')

    def update(self, request, *args, **kwargs):
        room = self.get_object()
        if room.host != request.user:
            raise PermissionDenied('Only the host can update this room.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        room = self.get_object()
        if room.host != request.user:
            raise PermissionDenied('Only the host can delete this room.')
        return super().destroy(request, *args, **kwargs)

class RoomTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            room = Room.objects.get(pk=pk)
        except Room.DoesNotExist:
            raise NotFound('Room not found.')

        if room.meeting_date > timezone.now():
            raise ValidationError('Meeting has not started yet.')

        is_host = room.host == request.user

        token = livekit_api.AccessToken(
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
        )
        token.with_identity(str(request.user.id))
        token.with_name(request.user.username)
        token.with_grants(livekit_api.VideoGrants(
            room_join=True,
            room=str(room.id),
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
            room_admin=is_host,
        ))

        return Response({
            'token': token.to_jwt(),
            'url': settings.LIVEKIT_URL,
            'room_name': str(room.id),
            'is_host': is_host,
        })
