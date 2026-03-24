from django.urls import re_path
from calls.consumers import RoomConsumer 

websocket_urlpatterns = [
    re_path(r'ws/calls/(?P<room_id>\d+)/$', RoomConsumer.as_asgi()),
]
