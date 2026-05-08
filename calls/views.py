from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from livekit import api as livekit_api
from .models import Room
from .serializers import RoomSerializer
from users.models import User
from django.db import models
from django.shortcuts import get_object_or_404

EXPIRY_HOURS = 24

class RoomListCreateView(generics.ListCreateAPIView):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        expiry_threshold = timezone.now() - timedelta(hours=EXPIRY_HOURS)
        return Room.objects.filter(
            models.Q(host=user) | models.Q(participants=user)
        ).exclude(
            models.Q(meeting_date__isnull=False, meeting_date__lt=expiry_threshold) |
            models.Q(meeting_date__isnull=True, created_at__lt=expiry_threshold)
        ).distinct().order_by('meeting_date')

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('Only employers can create rooms.')
        meeting_date = serializer.validated_data.get('meeting_date')
        if meeting_date and meeting_date < timezone.now():
            raise ValidationError('Meeting date cannot be in the past.')
        room = serializer.save(host=self.request.user)
        # Host is always a participant and since only an employer can create a room
        # this line essentially auto adds the host to the meeting
        room.participants.add(self.request.user)


class RoomParticipantView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        room.participants.add(request.user)
        return Response({'status': 'added'})

    def delete(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        room.participants.remove(request.user)
        return Response({'status': 'removed'})


class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        if not hasattr(self, '_room'):
            try:
                self._room = Room.objects.get(pk=self.kwargs.get('pk'))
            except Room.DoesNotExist:
                raise NotFound('Room not found.')
        return self._room

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

        if room.meeting_date and room.meeting_date > timezone.now():
            raise ValidationError('Meeting has not started yet.')

        if room.meeting_date and room.meeting_date < timezone.now() - timedelta(hours=EXPIRY_HOURS):
            raise ValidationError('This meeting has expired.')

        is_host = room.host == request.user
        is_participant = room.participants.filter(id=request.user.id).exists()
        if not is_host and not is_participant:
            raise PermissionDenied('You are not a participant of this meeting.')

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