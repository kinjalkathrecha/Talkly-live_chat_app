from django.urls import path
from .views import (
    RoomDetailView, 
    StartDMView, 
    AddContactView, 
    StartDMByPhoneView,
)

urlpatterns = [
    path("add-contact/", AddContactView.as_view(), name="add_contact"),
    path("dm/<str:username>/", StartDMView.as_view(), name="start_dm"),
    path("dm/phone/<str:phone>/", StartDMByPhoneView.as_view(), name="start_dm_by_phone"),
    
    path("<slug:room_name>/", RoomDetailView.as_view(), name="room"),
]