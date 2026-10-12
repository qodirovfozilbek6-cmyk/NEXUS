
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
):
    if not init_data or not bot_token:
        return None

    try:
        pairs = parse_qsl(
            init_data,
            keep_blank_values=True,
            strict_parsing=True,
        )
        data = dict(pairs)

        # Takroriy kalitlar bilan soxtalashtirishni rad etamiz.
        if len(data) != len(pairs):
            return None

        received_hash = data.pop("hash", None)
        if not received_hash:
            return None

        auth_date = int(data.get("auth_date", "0"))
        now = int(time.time())

        if auth_date <= 0 or auth_date > now + 60:
            return None

        if now - auth_date > max_age_seconds:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(data.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(
            expected_hash, received_hash
        ):
            return None

        user_raw = data.get("user")
        if not user_raw:
            return None

        user = json.loads(user_raw)
        if not isinstance(user, dict) or not user.get("id"):
            return None

        return user

    except (ValueError, TypeError, json.JSONDecodeError):
        return None

# Telegram Login Widget (ordinary browser) validation.
def validate_telegram_login(payload: dict, bot_token: str, max_age_seconds: int = 86400):
    """Verify Telegram Login Widget data before trusting the browser identity."""
    if not isinstance(payload, dict) or not bot_token:
        return None
    try:
        data = {str(k): str(v) for k, v in payload.items() if k != "hash"}
        received_hash = payload.get("hash")
        if not isinstance(received_hash, str) or not received_hash:
            return None
        auth_date = int(data.get("auth_date", "0"))
        now = int(time.time())
        if auth_date <= 0 or auth_date > now + 60 or now - auth_date > max_age_seconds:
            return None
        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
        secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            return None
        telegram_id = int(data.get("id", "0"))
        if telegram_id <= 0 or not data.get("first_name"):
            return None
        return {
            "id": telegram_id,
            "first_name": data.get("first_name", ""),
            "username": data.get("username") or None,
        }
    except (TypeError, ValueError, OverflowError):
        return None


def _session_secret(bot_token: str) -> bytes:
    return hmac.new(bot_token.encode("utf-8"), b"NEXUS_BROWSER_SESSION_V1", hashlib.sha256).digest()


def create_browser_session(telegram_id: int, bot_token: str, lifetime_seconds: int = 7 * 86400) -> str:
    """Create a short-lived signed token; cookie itself is HttpOnly and Secure."""
    import base64
    payload = json.dumps({"id": int(telegram_id), "exp": int(time.time()) + lifetime_seconds}, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    signature = hmac.new(_session_secret(bot_token), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def validate_browser_session(token: str, bot_token: str):
    import base64
    if not token or not bot_token or "." not in token:
        return None
    try:
        encoded, received_signature = token.rsplit(".", 1)
        expected_signature = hmac.new(_session_secret(bot_token), encoded.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_signature, received_signature):
            return None
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        telegram_id = int(payload.get("id", 0))
        expiry = int(payload.get("exp", 0))
        if telegram_id <= 0 or expiry <= int(time.time()):
            return None
        return {"id": telegram_id, "exp": expiry}
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None
