from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from .models import Room, UserProfile, Contact
from .forms import UserSignUpForm, AddContactForm

@login_required
def index(request):
    user_rooms = Room.objects.filter(
        is_private=True, 
        participants=request.user,
    ).distinct()
    
    rooms_with_last_msg = []
    for room in user_rooms:
        last_msg = room.last_message
        other = room.get_other_user(request.user)
        display_name = None
        
        if isinstance(other, User):
            phone = getattr(other, 'profile', None).phone_number if hasattr(other, 'profile') and other.profile else None
            contact = Contact.objects.filter(user=request.user, phone_number=phone).first() if phone else None
            if contact:
                display_name = f"{contact.first_name} {contact.last_name}".strip()
            else:
                display_name = other.username
        elif other: 
            contact = Contact.objects.filter(user=request.user, phone_number=other).first()
            if contact:
                display_name = f"{contact.first_name} {contact.last_name}".strip()
            else:
                display_name = other

        rooms_with_last_msg.append({
            'room': room,
            'last_message': last_msg,
            'other_user': other,
            'display_name': display_name
        })
    
    rooms_with_last_msg.sort(key=lambda x: x['last_message'].timestamp if x['last_message'] else x['room'].created_at, reverse=True)

    my_contacts = Contact.objects.filter(user=request.user)
    
    contacts_with_users = []
    for contact in my_contacts:
        # Dynamically check if this phone number belongs to a registered user
        profile = UserProfile.objects.filter(phone_number=contact.phone_number).first()
        contacts_with_users.append({
            'contact': contact,
            'linked_user': profile.user if profile else None
        })

    return render(request, "index.html", {
        "recent_chats": rooms_with_last_msg,
        "contacts_data": contacts_with_users
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
    
    display_name = room.name
    if room.is_private:
        other = room.get_other_user(request.user)
        if isinstance(other, User):
            phone = getattr(other.profile, 'phone_number', None) if hasattr(other, 'profile') else None
            contact = Contact.objects.filter(user=request.user, phone_number=phone).first() if phone else None
            if contact:
                display_name = f"{contact.first_name} {contact.last_name}".strip()
            else:
                display_name = other.username
        elif other:
            contact = Contact.objects.filter(user=request.user, phone_number=other).first()
            if contact:
                display_name = f"{contact.first_name} {contact.last_name}".strip()
            else:
                display_name = other

    return render(request, "room.html", {
        "room_name": room_name,
        "display_name": display_name,
        "other_user_display_name": display_name if room.is_private else None,
        "messages": messages,
        "participants": participants,
    })

@login_required
def add_contact(request):
    error = None
    if request.method == 'POST':
        form = AddContactForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            phone = form.cleaned_data.get('phone_number')
            
            try:
                # Save the personal contact
                contact, _ = Contact.objects.get_or_create(
                    user=request.user, 
                    phone_number=phone,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name
                    }
                )
                return redirect('start_dm_by_phone', phone=phone)
            except Exception as e:
                print(f"Error saving contact: {e}")
                error = "An error occurred while saving the contact."
    
    return render(request, "add_contact.html", {"error": error})

@login_required
def start_dm(request, username):
    other_user = User.objects.get(username=username)
    user_ids = sorted([request.user.id, other_user.id])
    room_name = f"dm_{user_ids[0]}_{user_ids[1]}"
    
    room, created = Room.objects.get_or_create(name=room_name, is_private=True)
    if created:
        room.participants.add(request.user, other_user)
        room.receiver_phone = None 
        room.save()
    
    return redirect('room', room_name=room_name)

@login_required
def start_dm_by_phone(request, phone):
    profile = UserProfile.objects.filter(phone_number=phone).first()
    if profile:
        return redirect('start_dm', username=profile.user.username)
    
    room_name = f"dm_phone_{request.user.id}_{phone}"
    
    room, created = Room.objects.get_or_create(
        name=room_name, 
        is_private=True,
        defaults={'receiver_phone': phone}
    )
    if created:
        room.participants.add(request.user)
    
    return redirect('room', room_name=room_name)

def signup(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = UserSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserSignUpForm()
    return render(request, 'registration/signup.html', {'form': form})