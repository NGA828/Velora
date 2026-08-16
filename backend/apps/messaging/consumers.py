from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.messaging.realtime import user_group


class UserEventsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not user.is_active:
            await self.close(code=4401)
            return
        self.group_name = user_group(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connection.ready"})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def user_event(self, event):
        await self.send_json({"type": event["event_type"], "payload": event["payload"]})
