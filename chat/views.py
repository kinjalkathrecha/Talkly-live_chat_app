from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.contrib.auth.models import User
from .models import Room, UserProfile, Contact
from .forms import UserSignUpForm, AddContactForm
from django.urls import reverse_lazy

class IndexView(LoginRequiredMixin, ListView):
    template_name = "index.html"
    context_object_name = "recent_chats"

    def get_queryset(self):
        # Logic moved from the original index function
        user_rooms = Room.objects.filter(
            participants=self.request.user
        ).distinct()
        
        rooms_with_last_msg = []
        for room in user_rooms:
            last_msg = room.last_message
            if not last_msg:
                continue
                
            if room.is_private:
                other = room.get_other_user(self.request.user)
                display_name = self._get_display_name(other)
            else:
                other = None
                display_name = room.group_name or room.name

            rooms_with_last_msg.append({
                'room': room,
                'last_message': last_msg,
                'other_user': other,
                'display_name': display_name
            })
        
        # Sorting logic
        rooms_with_last_msg.sort(
            key=lambda x: x['last_message'].timestamp if x['last_message'] else x['room'].created_at, 
            reverse=True
        )
        return rooms_with_last_msg

    def _get_display_name(self, other):
        phone = None
        if isinstance(other, User):
            phone = getattr(other, 'profile', None).phone_number if hasattr(other, 'profile') else None
        else:
            phone = other

        if phone:
            contact = Contact.objects.filter(user=self.request.user, phone_number=phone).first()
            if contact:
                return f"{contact.first_name} {contact.last_name}".strip()
        
        return getattr(other, 'username', other)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        my_contacts = Contact.objects.filter(user=self.request.user)
        
        contacts_with_users = []
        for contact in my_contacts:
            profile = UserProfile.objects.filter(phone_number=contact.phone_number).first()
            contacts_with_users.append({
                'contact': contact,
                'linked_user': profile.user if profile else None
            })
        
        context["contacts_data"] = contacts_with_users
        return context


class RoomDetailView(LoginRequiredMixin, View):
    def get(self, request, room_name):
        room, created = Room.objects.get_or_create(name=room_name)
        
        # Security check
        if request.user not in room.participants.all():
            return redirect('index')

        messages = room.messages.all().order_by('timestamp')
        if messages.count() > 50:
            messages = messages[messages.count()-50:]

        display_name = room.name
        if room.is_private:
            index_helper = IndexView()
            index_helper.request = request
            display_name = index_helper._get_display_name(room.get_other_user(request.user))
        else:
            display_name = room.group_name or room.name
            
        available_contacts = []
        if not room.is_private and request.user == room.admin:
            my_contacts = Contact.objects.filter(user=request.user)
            existing_participants_ids = room.participants.values_list('id', flat=True)
            for contact in my_contacts:
                profile = UserProfile.objects.filter(phone_number=contact.phone_number).first()
                if profile and profile.user and profile.user.id not in existing_participants_ids:
                    available_contacts.append({
                        'contact': contact,
                        'user': profile.user
                    })

        return render(request, "room.html", {
            "room_name": room_name,
            "display_name": display_name,
            "other_user_display_name": display_name if room.is_private else None,
            "messages": messages,
            "participants": room.participants.all(),
            "is_group": not room.is_private,
            "is_admin": request.user == room.admin,
            "available_contacts": available_contacts
        })


class AddContactView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "add_contact.html", {"form": AddContactForm()})

    def post(self, request):
        form = AddContactForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data.get('phone_number')
            Contact.objects.get_or_create(
                user=request.user, 
                phone_number=phone,
                defaults={
                    'first_name': form.cleaned_data.get('first_name'),
                    'last_name': form.cleaned_data.get('last_name')
                }
            )
            return redirect('start_dm_by_phone', phone=phone)
        return render(request, "add_contact.html", {"form": form, "error": "Invalid form data."})


class StartDMView(LoginRequiredMixin, View):
    def get(self, request, username):
        other_user = get_object_or_404(User, username=username)
        
        if request.user != other_user:
            existing_room = Room.objects.filter(is_private=True, participants=request.user).filter(participants=other_user).first()
            if existing_room:
                return redirect('room', room_name=existing_room.name)
            
        user_ids = sorted([request.user.id, other_user.id])
        room_name = f"dm_{user_ids[0]}_{user_ids[1]}"
        room, created = Room.objects.get_or_create(name=room_name, is_private=True)
        if created:
            room.participants.add(request.user, other_user)
        
        return redirect('room', room_name=room_name)


class StartDMByPhoneView(LoginRequiredMixin, View):
    def get(self, request, phone):
        profile = UserProfile.objects.filter(phone_number=phone).first()
        if profile:
            return redirect('start_dm', username=profile.user.username)
            
        existing_room = Room.objects.filter(is_private=True, receiver_phone=phone, participants=request.user).first()
        if existing_room:
            return redirect('room', room_name=existing_room.name)
        
        room_name = f"dm_phone_{request.user.id}_{phone}"
        room, created = Room.objects.get_or_create(
            name=room_name, is_private=True, defaults={'receiver_phone': phone}
        )
        if created:
            room.participants.add(request.user)
        
        return redirect('room', room_name=room_name)


class SignUpView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('index')
        return render(request, 'registration/signup.html', {'form': UserSignUpForm()})

    def post(self, request):
        form = UserSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
        return render(request, 'registration/signup.html', {'form': form})
        
from django.utils.crypto import get_random_string

class CreateGroupView(LoginRequiredMixin, View):
    def get(self, request):
        my_contacts = Contact.objects.filter(user=request.user)
        contacts_with_users = []
        for contact in my_contacts:
            profile = UserProfile.objects.filter(phone_number=contact.phone_number).first()
            if profile and profile.user:
                contacts_with_users.append({
                    'contact': contact,
                    'user': profile.user
                })
        return render(request, "create_group.html", {"contacts": contacts_with_users})
        
    def post(self, request):
        group_name = request.POST.get('group_name')
        participant_ids = request.POST.getlist('participants')
        
        if not group_name:
            return redirect('create_group')
            
        room_name = f"group_{get_random_string(10)}"
        
        room = Room.objects.create(
            name=room_name,
            group_name=group_name,
            admin=request.user,
            is_private=False
        )
        room.participants.add(request.user)
        for p_id in participant_ids:
            room.participants.add(p_id)
            
        return redirect('room', room_name=room.name)

class AddGroupMemberView(LoginRequiredMixin, View):
    def post(self, request, room_name):
        room = get_object_or_404(Room, name=room_name)
        if request.user != room.admin:
            return redirect('room', room_name=room_name)
            
        participant_ids = request.POST.getlist('participants')
        for p_id in participant_ids:
            room.participants.add(p_id)
            
        return redirect('room', room_name=room_name)