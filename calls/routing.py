from django.urls import re_path
from calls.consumers import VideoCalls

websocket_urlpatterns = [
    re_path(r'ws/calls/(?P<room_id>[\w-]+)/$', VideoCalls.as_asgi()),
]