from django.db import models
from django.contrib.auth.models import User

class Room(models.Model):
    name = models.CharField(max_length=255,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
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

    class Meta:
        ordering = ("timestamp",)

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'}: {self.content[:20]}"