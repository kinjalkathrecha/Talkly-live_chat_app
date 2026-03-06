from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Room

# Create your views here.
@login_required
def index(request):
    return render(request, "index.html")

@login_required
def room(request, room_name):
    room, created = Room.objects.get_or_create(name=room_name)
    messages = room.messages.all().order_by('timestamp')
    

    if messages.count() > 50:
        messages = messages[messages.count()-50:]

    return render(request, "room.html", {
        "room_name": room_name,
        "messages": messages,
    })

def signup(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})
    