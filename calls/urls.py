from django.urls import path
from .views import RoomListCreateView, RoomDetailView, RoomTokenView

urlpatterns = [
    path('calls/', RoomListCreateView.as_view()),
    path('calls/<int:pk>/', RoomDetailView.as_view()),
    path('calls/<int:pk>/token/', RoomTokenView.as_view()),
]