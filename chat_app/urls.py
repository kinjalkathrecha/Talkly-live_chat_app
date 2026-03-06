from django.contrib import admin
from django.urls import path,include
from chat.views import signup,index
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/',signup,name="signup"),
    path("",index,name="index"),
    path('chat/',include("chat.urls"))
]