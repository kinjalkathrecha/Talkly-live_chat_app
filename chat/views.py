from django.shortcuts import render
from .models import Room

# Create your views here.
def index(request):
    return render(request, "index.html")

def room(request, room_name):
    room, created = Room.objects.get_or_create(name=room_name)
    messages = room.messages.all().order_by('timestamp')
    

    if messages.count() > 50:
        messages = messages[messages.count()-50:]

    return render(request, "room.html", {
        "room_name": room_name,
        "messages": messages,
    })
    