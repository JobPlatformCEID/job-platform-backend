from django.urls import path
from .views import RoomListCreateView, RoomDetailView, join_call

urlpatterns = [
    path('calls/', RoomListCreateView.as_view()),
    path('calls/<int:pk>/', RoomDetailView.as_view()),
    path('calls/<int:room_id>/join/', join_call, name='join_call'),
]