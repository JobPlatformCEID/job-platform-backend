"""Utils for creating LiveKit tokens."""

import os
from livekit.api import AccessToken, VideoGrants

LIVEKIT_API_KEY    = os.environ.get("LIVEKIT_API_KEY",    "livekitdev")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "livekitdevsecret1234567890abcdef")
LIVEKIT_PUBLIC_URL = os.environ.get("LIVEKIT_PUBLIC_URL", "ws://localhost:7880")


def generate_token(room_name: str, identity: str) -> str:
    # Token gives publish + subscribe permissions
    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(identity).with_name(identity)
    token.with_grants(VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
    ))
    return token.to_jwt()