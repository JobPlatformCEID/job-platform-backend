from django.urls import path
from .views import ReviewListCreateView, ReviewDetailView

urlpatterns = [
    path('reviews/<int:employer_id>/', ReviewListCreateView.as_view()),
    path('reviews/<int:employer_id>/<int:pk>/', ReviewDetailView.as_view()),
]