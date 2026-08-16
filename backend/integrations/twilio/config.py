import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TwilioSettings:
    account_sid: str
    api_key: str
    api_secret: str
    twiml_app_sid: str
    auth_token: str
    webhook_base_url: str

    @property
    def available(self) -> bool:
        return all(
            [
                self.account_sid,
                self.api_key,
                self.api_secret,
                self.twiml_app_sid,
                self.auth_token,
                self.webhook_base_url,
            ]
        )


def get_twilio_settings() -> TwilioSettings:
    return TwilioSettings(
        account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        api_key=os.getenv("TWILIO_API_KEY", ""),
        api_secret=os.getenv("TWILIO_API_SECRET", ""),
        twiml_app_sid=os.getenv("TWILIO_TWIML_APP_SID", ""),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        webhook_base_url=os.getenv("TWILIO_WEBHOOK_BASE_URL", "").rstrip("/"),
    )
