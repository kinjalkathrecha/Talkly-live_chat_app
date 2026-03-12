from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import User
from .models import Room

# Create your views here.
@login_required
def index(request):
    return render(request, "index.html")

@login_required
def room(request, room_name):
    try:
        room = Room.objects.get(name=room_name)
        if room.is_private and request.user not in room.participants.all():
            return redirect('index')
    except Room.DoesNotExist:
        room = Room.objects.create(name=room_name)

    messages = room.messages.all().order_by('timestamp')

    if messages.count() > 50:
        messages = messages[messages.count()-50:]

    return render(request, "room.html", {
        "room_name": room_name,
        "messages": messages,
    })

@login_required
def search_users(request):
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)
    else:
        users = User.objects.none()
    
    return render(request, "search.html", {"users": users, "query": query})

@login_required
def start_dm(request, username):
    other_user = User.objects.get(username=username)
    user_ids = sorted([request.user.id, other_user.id])
    room_name = f"dm_{user_ids[0]}_{user_ids[1]}"
    
    room, created = Room.objects.get_or_create(name=room_name, is_private=True)
    if created:
        room.participants.add(request.user, other_user)
    
    return redirect('room', room_name=room_name)

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
    