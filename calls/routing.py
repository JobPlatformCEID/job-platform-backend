# routing.py
# WebSocket routing has been removed.
# All room/participant management is done via the LiveKit Server API.
# Daphne / Django Channels is still used to serve HTTP, but there are
# no custom WebSocket consumers left in this app.

websocket_urlpatterns = []