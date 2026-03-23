from django.urls import path
from .views import RoomListCreateView, RoomDetailView

urlpatterns = [
    path('calls/', RoomListCreateView.as_view()),
    path('calls/<int:pk>/', RoomDetailView.as_view()),
]