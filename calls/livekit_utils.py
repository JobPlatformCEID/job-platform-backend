import os
try:
    from livekit_api import AccessToken, VideoGrants
except ImportError:
    try:
        from livekit import AccessToken, VideoGrants
    except ImportError:
        from livekit.api import AccessToken, VideoGrants

LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_PUBLIC_URL = os.environ.get("LIVEKIT_PUBLIC_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "livekitdev")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "livekitdevsecret1234567890abcdef")

def generate_token(room_name: str, identity: str, is_host: bool = False) -> str:
    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(identity).with_name(identity)
    token.with_grants(VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        room_admin=is_host,
    ))
    return token.to_jwt()