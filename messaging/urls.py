from django.urls import path
from .views import ConversationListCreateView, ConversationDeleteView, MessageListView, MessageDeleteView

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view()),
    path('conversations/<int:pk>/', ConversationDeleteView.as_view()),
    path('conversations/<int:pk>/messages/', MessageListView.as_view()),
    path('conversations/<int:pk>/messages/<int:message_pk>/', MessageDeleteView.as_view()),
]
