from django.contrib import admin
from .models import (
    Room,
    Message,
    UserProfile,
    Contact,
    Notification
)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'content', 'timestamp')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user','is_online','last_seen')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('user','first_name','phone_number')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user','message','is_read','created_at')