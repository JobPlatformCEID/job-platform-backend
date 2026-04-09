"""API endpoints for video call rooms.

Rooms live in our DB. LiveKit auto-creates them when someone joins with a token.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Room
from .livekit_utils import generate_token, LIVEKIT_PUBLIC_URL


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def calls_list(request):
    if request.method == "GET":
        rooms = Room.objects.all().order_by("-created_at")
        return Response([r.to_dict() for r in rooms])

    # POST — employers only
    if request.user.role != "employer":
        return Response({"detail": "Only employers can create rooms."},
                        status=status.HTTP_403_FORBIDDEN)

    room_name   = request.data.get("room_name", "").strip()
    description = request.data.get("description", "").strip()
    meeting_date = request.data.get("meeting_date", "")

    if not room_name:
        return Response({"detail": "room_name is required."},
                        status=status.HTTP_400_BAD_REQUEST)

    room = Room.objects.create(
        room_name=room_name,
        description=description,
        meeting_date=meeting_date or None,
        host=request.user,
    )
    return Response(room.to_dict(), status=status.HTTP_201_CREATED)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def calls_detail(request, pk):
    try:
        room = Room.objects.get(pk=pk)
    except Room.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(room.to_dict())

    if room.host != request.user:
        return Response({"detail": "Only the host can delete this room."},
                        status=status.HTTP_403_FORBIDDEN)
    room.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def calls_join(request, pk):
    # Return token so user can join the room
    try:
        room = Room.objects.get(pk=pk)
    except Room.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    token = generate_token(
        room_name=str(room.pk),   # use DB id as LiveKit room name — simple & unique
        identity=request.user.username,
    )

    return Response({
        "livekit_url":   LIVEKIT_PUBLIC_URL,
        "livekit_token": token,
        "room_name":     room.room_name,
        "is_host":       room.host == request.user,
    })