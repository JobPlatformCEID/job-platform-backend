from django.urls import path
from .views import RoomListCreateView, RoomDetailView, RoomTokenView , RoomParticipantView

urlpatterns = [
    path('calls/', RoomListCreateView.as_view()),
    path('calls/<int:pk>/', RoomDetailView.as_view()),
    path('calls/<int:pk>/token/', RoomTokenView.as_view()),
    path('calls/<int:pk>/participants/', RoomParticipantView.as_view()),
]