from slowapi import Limiter
from slowapi.util import get_remote_address


def get_user_id_or_ip(request):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from app.auth import decode_access_token
            payload = decode_access_token(token)
            return payload.get("sub", get_remote_address(request))
        except Exception:
            return get_remote_address(request)
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_id_or_ip)