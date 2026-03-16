from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Room(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_private = models.BooleanField(default=False)
    participants = models.ManyToManyField(User, related_name="rooms", blank=True)
    receiver_phone = models.CharField(max_length=15, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def last_message(self):
        return self.messages.order_by('-timestamp').first()

    def get_other_user(self, current_user):
        if self.is_private:
            other_user = self.participants.exclude(id=current_user.id).first()
            if other_user:
                return other_user
            return self.receiver_phone
        return None

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"

class Message(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
 
    STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('seen', 'Seen'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("timestamp",)

    @property
    def status_icon_html(self):
        if self.status == 'sent':
            return '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="15" fill="currentColor" viewBox="0 0 16 16"><path d="M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 0 1 .02-.022z"/></svg>'
        elif self.status == 'delivered':
            return '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="15" fill="currentColor" viewBox="0 0 16 16"><path d="M12.354 4.354a.5.5 0 0 0-.708-.708L5 10.293 1.854 7.146a.5.5 0 1 0-.708.708l3.5 3.5a.5.5 0 0 0 .708 0l7-7zm-4.208 7-.896-.897.707-.707.543.543 6.646-6.647a.5.5 0 0 1 .708.708l-7 7a.5.5 0 0 1-.708 0z"/><path d="m5.354 7.146.896.897-.707.707-.897-.896a.5.5 0 1 1 .708-.708z"/></svg>'
        elif self.status == 'seen':
            return '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="15" fill="#80ccff" viewBox="0 0 16 16"><path d="M12.354 4.354a.5.5 0 0 0-.708-.708L5 10.293 1.854 7.146a.5.5 0 1 0-.708.708l3.5 3.5a.5.5 0 0 0 .708 0l7-7zm-4.208 7-.896-.897.707-.707.543.543 6.646-6.647a.5.5 0 0 1 .708.708l-7 7a.5.5 0 0 1-.708 0z"/><path d="m5.354 7.146.896.897-.707.707-.897-.896a.5.5 0 1 1 .708-.708z"/></svg>'
        return ''

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} ({self.status}): {self.content[:20]}"

class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contacts")
    first_name = models.CharField(max_length=100, default="")
    last_name = models.CharField(max_length=100, blank=True, default="")
    phone_number = models.CharField(max_length=15,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'phone_number')

    def __str__(self):
        return f"{self.user.username} -> {self.first_name} {self.last_name} ({self.phone_number})"


@receiver(post_save, sender=UserProfile)
def claim_pending_rooms(sender, instance, created, **kwargs):
    if instance.phone_number:
        # Find rooms where this phone number is the receiver
        pending_rooms = Room.objects.filter(receiver_phone=instance.phone_number, is_private=True)
        for room in pending_rooms:
            room.participants.add(instance.user)
            # Once claimed, we clear receiver_phone
            room.receiver_phone = None
            room.save()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()