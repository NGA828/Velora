from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

from integrations.twilio.config import get_twilio_settings


def twilio_identity(user_id) -> str:
    return f"user_{str(user_id).replace('-', '')}"


def create_voice_token(*, user_id, ttl=3600) -> str:
    config = get_twilio_settings()
    if not config.available:
        raise RuntimeError("Twilio voice integration is not configured.")
    token = AccessToken(
        config.account_sid,
        config.api_key,
        config.api_secret,
        identity=twilio_identity(user_id),
        ttl=ttl,
    )
    token.add_grant(
        VoiceGrant(
            outgoing_application_sid=config.twiml_app_sid,
            incoming_allow=True,
        )
    )
    encoded = token.to_jwt()
    return encoded.decode("utf-8") if isinstance(encoded, bytes) else encoded
