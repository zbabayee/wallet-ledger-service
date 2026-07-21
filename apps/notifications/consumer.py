import json

from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time wallet notifications.
    Each authenticated user joins a private group:
        user_<user_id>
    Transfers send messages to the recipient's group.
    """
    async def connect(self):
        user = self.scope["user"]

        if user.is_anonymous:
            await self.close(code=4401)
            return
        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def wallet_notification(self, event):
        """
        Called by channel_layer.group_send(...)
        event = {
            "type": "wallet_notification",
            "data": {...}
        }
        """
        await self.send(
            text_data=json.dumps(event["data"])
        )