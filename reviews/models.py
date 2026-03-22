from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import User, EmployerProfile

class Review(models.Model):
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name='reviews')
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    content = models.TextField(null=True, max_length=400, blank=True)
    score = models.SmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(10)])
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)