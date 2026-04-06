from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import NotFound, PermissionDenied
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, LoginSerializer, CandidateProfileSerializer, EmployerProfileSerializer, EmployerListSerializer
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
            return Response({
                'token': token.key,
                'role': user.role,
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

# User view for showing a user's public info
class UserDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = User.objects.get(id=self.kwargs['pk'])
            try:
                if user.role == User.Role.CANDIDATE:
                    profile_id = user.candidate_profile.id
                else:
                    profile_id = user.employer_profile.id
            except:
                profile_id = None
            return Response({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': user.role,
                'profile_id': profile_id,
            })
        except User.DoesNotExist:
            raise NotFound('User not found.')


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

# View for showing the profile of a candidate (via ID)
class CandidateProfileDetailView(generics.RetrieveAPIView):
    serializer_class = CandidateProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return CandidateProfile.objects.get(id=self.kwargs['pk'])
        except CandidateProfile.DoesNotExist:
            raise NotFound('Candidate not found.')

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

# View for showing the profile of an employer (via ID)
class EmployerProfileDetailView(generics.RetrieveAPIView):
    serializer_class = EmployerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return EmployerProfile.objects.get(id=self.kwargs['pk'])
        except EmployerProfile.DoesNotExist:
            raise NotFound('Employer not found.')

# View for showing all employers in the database
class EmployerListView(generics.ListAPIView):
    serializer_class = EmployerListSerializer
    permission_classes = [IsAuthenticated]
    queryset = EmployerProfile.objects.all()
