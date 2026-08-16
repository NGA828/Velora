from twilio.request_validator import RequestValidator

from integrations.twilio.config import get_twilio_settings


def webhook_url(request) -> str:
    config = get_twilio_settings()
    if config.webhook_base_url:
        return f"{config.webhook_base_url}{request.get_full_path()}"
    return request.build_absolute_uri()


def valid_twilio_signature(request) -> bool:
    config = get_twilio_settings()
    if not config.auth_token:
        return False
    signature = request.headers.get("X-Twilio-Signature", "")
    return RequestValidator(config.auth_token).validate(
        webhook_url(request),
        request.POST.dict(),
        signature,
    )
