from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message, UserProfile, Notification
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
        last_seen = timezone.now()
        await self.update_user_status(False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_status",
                "user": self.user.username,
                "status": "offline",
                "last_seen": "Just now" # Initial offline status
            }
        )

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")
        message = data.get("message")
        user = self.scope["user"]

        if msg_type == "message_delivered":
            message_id = data.get("message_id")
            icon_html = await self.update_message_status(message_id, "delivered")
            if icon_html:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_status_update",
                        "message_id": message_id,
                        "status": "delivered",
                        "status_icon_html": icon_html,
                        "user": user.username
                    }
                )

        elif msg_type == "message_seen":
            message_id = data.get("message_id")
            icon_html = await self.update_message_status(message_id, "seen")
            if icon_html:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_status_update",
                        "message_id": message_id,
                        "status": "seen",
                        "status_icon_html": icon_html,
                        "user": user.username
                    }
                )

        elif msg_type == "edit_message":
            message_id = data.get("message_id")
            new_content = data.get("message")
            success = await self.edit_message_db(message_id, new_content)
            if success:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_edited",
                        "message_id": message_id,
                        "message": new_content,
                        "user": user.username
                    }
                )

        elif msg_type == "delete_message":
            message_id = data.get("message_id")
            success = await self.delete_message_db(message_id)
            if success:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_deleted",
                        "message_id": message_id,
                        "user": user.username
                    }
                )

        elif message:
            saved_msg = await self.save_message(self.room_name, message, user)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "user": user.username if user.is_authenticated else "Anonymous",
                    "id": saved_msg.id,
                    "status_icon_html": await self.get_message_icon(saved_msg.id),
                    "sender_channel_name": self.channel_name
                }
            )

            # Send a global notification to other participants in the room
            participants = await self.get_room_participants(self.room_name)
            for participant in participants:
                if participant.id != user.id:
                    # Create Notification in DB and get unread count
                    unread_count = await self.create_notification(participant, saved_msg)

                    notify_group = f"notify_{participant.id}"
                    await self.channel_layer.group_send(
                        notify_group,
                        {
                            "type": "global_notification",
                            "message": message,
                            "sender": user.username if user.is_authenticated else "Anonymous",
                            "room_name": self.room_name,
                            "unread_count": unread_count
                        }
                    )
        
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "user": event["user"],
            "id": event["id"],
            "status": "sent",
            "status_icon_html": event["status_icon_html"],
            "sender_channel_name": event["sender_channel_name"]
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            "type": "message_edited",
            "message_id": event["message_id"],
            "message": event["message"],
            "user": event["user"]
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            "type": "message_deleted",
            "message_id": event["message_id"],
            "user": event["user"]
        }))

    async def message_status_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "message_status_update",
            "message_id": event["message_id"],
            "status": event.get("status"),
            "status_icon_html": event["status_icon_html"],
            "user": event["user"]
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            "type": "user_status",
            "user": event["user"],
            "status": event["status"],
            "last_seen": event.get("last_seen", "")
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
            return Message.objects.create(room=room, content=content, user=user)
        else:
            return Message.objects.create(room=room, content=content)

    @database_sync_to_async
    def get_message_icon(self, message_id):
        try:
            return Message.objects.get(id=message_id).status_icon_html
        except Message.DoesNotExist:
            return ""

    @database_sync_to_async
    def create_notification(self, user, message):
        Notification.objects.create(user=user, message=message)
        # Return the total unread count for this user in this room
        return Notification.objects.filter(user=user, message__room=message.room, is_read=False).count()

    @database_sync_to_async
    def update_message_status(self, message_id, status):
        try:
            message = Message.objects.get(id=message_id)
            updated = False
            # Only upgrade status, don't downgrade
            if status == 'delivered' and message.status == 'sent':
                message.status = status
                message.delivered_at = timezone.now()
                message.save()
                updated = True
            elif status == 'seen' and message.status in ['sent', 'delivered']:
                message.status = status
                if not message.delivered_at:
                    message.delivered_at = timezone.now()
                message.seen_at = timezone.now()
                message.save()
                updated = True
            
            if updated:
                return message.status_icon_html
            return None
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def edit_message_db(self, message_id, new_content):
        try:
            message = Message.objects.get(id=message_id, user=self.user)
            if not message.is_deleted:
                message.content = new_content
                message.is_edited = True
                message.save()
                return True
            return False
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def delete_message_db(self, message_id):
        try:
            message = Message.objects.get(id=message_id, user=self.user)
            message.is_deleted = True
            message.save()
            return True
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def update_user_status(self, is_online):
        UserProfile.objects.filter(user=self.user).update(
            is_online=is_online,
            last_seen=timezone.now()
        )

    @database_sync_to_async
    def get_room_participants(self, room_name):
        try:
            room = Room.objects.get(name=room_name)
            return list(room.participants.all())
        except Room.DoesNotExist:
            return []

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f"notify_{self.user.id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def global_notification(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification",
            "message": event["message"],
            "sender": event["sender"],
            "room_name": event["room_name"],
            "unread_count": event.get("unread_count", 0)
        }))
