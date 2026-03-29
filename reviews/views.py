from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from .models import Review
from .serializers import ReviewSerializer
from users.models import User, EmployerProfile , CandidateProfile , WorkExperience

class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        employer_id = self.kwargs.get('employer_id')
        return Review.objects.filter(employer=employer_id)

    def perform_create(self, serializer):
        try:
            employer = EmployerProfile.objects.get(pk=self.kwargs.get('employer_id'))
        except EmployerProfile.DoesNotExist:
            raise NotFound('Employer not found.')

        # someone cant review themselves
        if employer.user == self.request.user:
            raise PermissionDenied('You cannot review your own company.')
        
        # We agreed that employers shouldn't review other employers
        if self.request.user.role ==  User.Role.EMPLOYER :
            raise PermissionDenied('Employers cannot review other Employers')
        
        # check users work experience to make sure he worked there in the past
        try:
            candidate_profile = CandidateProfile.objects.get(user=self.request.user)
        except CandidateProfile.DoesNotExist:
            raise PermissionDenied('Only candidates can leave reviews.')
        
        if not WorkExperience.objects.filter(candidate=candidate_profile,company=employer.company_name).exists():
            raise PermissionDenied('You can only review companies you have worked at.')
        
        # you can only leave one review if you want a second one delete the last you made
        if Review.objects.filter(employer=employer, owner=self.request.user).exists():
            raise PermissionDenied('You have already reviewed this employer.')

        serializer.save(employer=employer, owner=self.request.user)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            review = Review.objects.get(pk=self.kwargs.get('pk'))
        except Review.DoesNotExist:
            raise NotFound('Review not found.')

        if self.request.method != 'GET':
            if review.owner != self.request.user:
                raise PermissionDenied('You can only edit your own reviews.')

        return review

    def update(self, request, *args, **kwargs):
        review = self.get_object()
        review.edited = True
        review.save()
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        review = self.get_object()
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)