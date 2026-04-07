from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Room
from .serializers import RoomCreateSerializer, RoomDetailSerializer
from users.models import User
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .livekit_utils import generate_token, LIVEKIT_PUBLIC_URL

class RoomListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RoomCreateSerializer
        return RoomDetailSerializer

    def get_queryset(self):
        return Room.objects.all()

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('Only employers can create rooms.')
        
        meeting_date = serializer.validated_data.get('meeting_date')
        if meeting_date and meeting_date < timezone.now():
            raise ValidationError('Meeting cannot be in the past.')
    
        serializer.save(host=self.request.user)

class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RoomDetailSerializer
    queryset = Room.objects.all()

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def join_call(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    token = generate_token(room.room_name, request.user.username, is_host=False)
    return JsonResponse({
        'livekit_url': LIVEKIT_PUBLIC_URL,
        'livekit_token': token
    })
