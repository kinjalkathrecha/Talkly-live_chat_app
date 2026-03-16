from django.contrib import admin
from django.urls import path,include
from chat.views import IndexView,SignUpView
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path("", IndexView.as_view(), name="index"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path('chat/',include("chat.urls"))
]