from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message
import json

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Send connection confirmation with channel name
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "channel_name": self.channel_name
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]
        user = self.scope["user"]

        # Save message to database
        await self.save_message(self.room_name, message, user)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "user": user.username if user.is_authenticated else "Anonymous",
                "sender_channel_name": self.channel_name
            }
        )

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "user": event["user"],
            "sender_channel_name": event["sender_channel_name"]
        }))

    @database_sync_to_async
    def save_message(self, room_name, content, user):
        room, created = Room.objects.get_or_create(name=room_name)
        if user.is_authenticated:
            Message.objects.create(room=room, content=content, user=user)
        else:
            Message.objects.create(room=room, content=content)
