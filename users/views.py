from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import NotFound, PermissionDenied
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, LoginSerializer, CandidateProfileSerializer, EmployerProfileSerializer
from .models import User, CandidateProfile, EmployerProfile

# Register View: CreateAPIView provides a post method handler
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

# Login View: Default post method won't work since we need extra things for login
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'role': user.role})
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

# Profile Views: RetrieveUpdateAPIView provides get, put, patch method handlers
# so these can be used for reading profiles and updating them
# Note: We might want to change how get_object and update check for roles later.
class CandidateProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CandidateProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        if self.request.user.role != User.Role.CANDIDATE:
            raise PermissionDenied('You are not a candidate.')
        try:
            return self.request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            raise NotFound('Candidate profile not found.')

    def update(self, request, *args, **kwargs):
        if request.user.role != User.Role.CANDIDATE:
            raise PermissionDenied('You are not a candidate.')
        return super().update(request, *args, **kwargs)

class EmployerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = EmployerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        if self.request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('You are not an employer.')
        try:
            return self.request.user.employer_profile
        except EmployerProfile.DoesNotExist:
            raise NotFound('Employer profile not found.')

    def update(self, request, *args, **kwargs):
        if request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('You are not an employer.')
        return super().update(request, *args, **kwargs)
