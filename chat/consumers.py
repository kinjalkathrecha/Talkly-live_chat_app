from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message, UserProfile
import json
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        # Fetch room to check privacy
        await self.verify_room_access()
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        await self.update_user_status(True)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_status",
                "user": self.user.username,
                "status": "online"
            }
        )
        
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "channel_name": self.channel_name
        }))

    async def disconnect(self, close_code):
        await self.update_user_status(False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_status",
                "user": self.user.username,
                "status": "offline"
            }
        )

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message")
        user = self.scope["user"]

        if message:
            await self.save_message(self.room_name, message, user)

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
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "user": event["user"],
            "sender_channel_name": event["sender_channel_name"]
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            "type": "user_status",
            "user": event["user"],
            "status": event["status"]
        }))

    async def verify_room_access(self):
        access_granted = await self.check_access(self.room_name, self.user)
        if not access_granted:
            await self.close()

    @database_sync_to_async
    def check_access(self, room_name, user):
        try:
            room = Room.objects.get(name=room_name)
            if room.is_private:
                return user in room.participants.all()
            return True
        except Room.DoesNotExist:
            return True 
        
    @database_sync_to_async
    def save_message(self, room_name, content, user):
        room, created = Room.objects.get_or_create(name=room_name)
        if user.is_authenticated:
            Message.objects.create(room=room, content=content, user=user)
        else:
            Message.objects.create(room=room, content=content)

    @database_sync_to_async
    def update_user_status(self, is_online):
        UserProfile.objects.filter(user=self.user).update(
            is_online=is_online,
            last_seen=timezone.now()
        )
