from django.urls import path
from .views import index,room

urlpatterns = [
    path("<slug:room_name>/",room, name="room"),
]