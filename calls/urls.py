from django.urls import path
from . import views

urlpatterns = [
    path("calls/",          views.calls_list,   name="calls-list"),
    path("calls/<int:pk>/", views.calls_detail, name="calls-detail"),
    path("calls/<int:pk>/join/", views.calls_join, name="calls-join"),
]