from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from .models import Room
from .serializers import RoomCreateSerializer, RoomDetailSerializer
from users.models import User

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