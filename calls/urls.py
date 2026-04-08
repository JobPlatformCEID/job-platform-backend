from django.urls import path
from .views import RoomListCreateView, RoomDetailView, join_call, admitted_users

urlpatterns = [
    path('calls/', RoomListCreateView.as_view()),
    path('calls/<int:pk>/', RoomDetailView.as_view()),
    path('calls/<int:room_id>/join/', join_call, name='join_call'),
    path('calls/<int:room_id>/admitted/', admitted_users, name='admitted_users'),
]