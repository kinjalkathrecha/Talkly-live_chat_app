from django.urls import path
from .views import (
    RoomDetailView, 
    StartDMView, 
    AddContactView, 
    StartDMByPhoneView,
    CreateGroupView,
    AddGroupMemberView
)

urlpatterns = [
    path("add-contact/", AddContactView.as_view(), name="add_contact"),
    path("dm/<str:username>/", StartDMView.as_view(), name="start_dm"),
    path("dm/phone/<str:phone>/", StartDMByPhoneView.as_view(), name="start_dm_by_phone"),
    path("create-group/", CreateGroupView.as_view(), name="create_group"),
    path("group/<str:room_name>/add-member/", AddGroupMemberView.as_view(), name="add_group_member"),
    
    path("<slug:room_name>/", RoomDetailView.as_view(), name="room"),
]