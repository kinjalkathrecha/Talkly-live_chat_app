from django.urls import path
from .views import index, room, start_dm, add_contact,start_dm_by_phone

urlpatterns = [
    path("add-contact/", add_contact, name="add_contact"),
    path("dm/<str:username>/", start_dm, name="start_dm"),
    path("dm/phone/<str:phone>/", start_dm_by_phone, name="start_dm_by_phone"),
    path("<slug:room_name>/", room, name="room"),
]