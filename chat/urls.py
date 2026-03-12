from django.urls import path
from .views import index, room, search_users, start_dm

urlpatterns = [
    path("search/", search_users, name="search_users"),
    path("dm/<str:username>/", start_dm, name="start_dm"),
    path("<slug:room_name>/", room, name="room"),
]