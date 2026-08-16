from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def user_group(user_id) -> str:
    return f"user_{str(user_id).replace('-', '')}"


def publish_user_event(*, user_id, event_type: str, payload: dict) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        user_group(user_id),
        {"type": "user.event", "event_type": event_type, "payload": payload},
    )
