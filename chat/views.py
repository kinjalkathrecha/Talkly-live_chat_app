from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import User
from .models import Room, UserProfile

# Create your views here.
@login_required
def index(request):
    user_rooms = Room.objects.filter(
        is_private=True, 
        participants=request.user,
        messages__isnull=False
    ).distinct()
    
    rooms_with_last_msg = []
    for room in user_rooms:
        last_msg = room.last_message
        rooms_with_last_msg.append({
            'room': room,
            'last_message': last_msg,
            'other_user': room.get_other_user(request.user)
        })
    
    rooms_with_last_msg.sort(key=lambda x: x['last_message'].timestamp if x['last_message'] else room.created_at, reverse=True)

    contacts = User.objects.exclude(id=request.user.id)

    return render(request, "index.html", {
        "recent_chats": rooms_with_last_msg,
        "contacts": contacts
    })

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

    participants = room.participants.all() if room.is_private else []

    return render(request, "room.html", {
        "room_name": room_name,
        "messages": messages,
        "participants": participants,
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
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})