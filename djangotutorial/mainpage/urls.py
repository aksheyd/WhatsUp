from django.urls import path

from . import views

app_name = "mainpage"
urlpatterns = [
    path("", views.index, name="index"),
    path("<str:state_code>/", views.state, name="state")
]