from rest_framework import serializers
from django.db.models import Avg
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ['owner', 'created_at','edited']

class EmployerReviewSummarySerializer(serializers.Serializer):
    score = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    reviews = ReviewSerializer(many=True, read_only=True)

    def get_score(self, obj):
        result = obj.reviews.aggregate(avg=Avg('score'))['avg']
        return round(result, 2) if result else 0

    def get_review_count(self, obj):
        return obj.reviews.count()