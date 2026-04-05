from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.views import APIView
from django.contrib.auth import authenticate

from .models import User, CandidateProfile, EmployerProfile, WorkExperience, Education, Skill, Certification, Project
from .serializers import (
    RegisterSerializer, LoginSerializer,
    CandidateProfileSerializer, EmployerProfileSerializer,
    WorkExperienceSerializer, EducationSerializer,
    SkillSerializer, CertificationSerializer,
    ProjectSerializer, UserNameSerializer, AvatarSerializer
)


# ── Auth Views ────────────────────────────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    serializer_class   = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(generics.GenericAPIView):
    serializer_class   = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'role': user.role})
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """DELETE /auth/logout/ — deletes the user's token, invalidating the session."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── User Views ────────────────────────────────────────────────────────────────

class UserNameView(generics.RetrieveAPIView):
    """GET /me/name/ — returns just the logged-in user's name fields."""
    serializer_class   = UserNameSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# ── Profile Views ─────────────────────────────────────────────────────────────

class CandidateProfileView(generics.RetrieveUpdateAPIView):
    serializer_class   = CandidateProfileSerializer
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
    serializer_class   = EmployerProfileSerializer
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

class CandidateSubModelMixin:
    permission_classes = [IsAuthenticated]

    def get_candidate(self):
        if self.request.user.role != User.Role.CANDIDATE:
            raise PermissionDenied('You are not a candidate.')
        try:
            return self.request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            raise NotFound('Candidate profile not found.')


# ── Work Experience ───────────────────────────────────────────────────────────

class WorkExperienceListCreateView(CandidateSubModelMixin, generics.ListCreateAPIView):
    """
    GET  /work-experience/      → list all work experiences
    POST /work-experience/      → add a new one
    """
    serializer_class = WorkExperienceSerializer

    def get_queryset(self):
        return WorkExperience.objects.filter(candidate=self.get_candidate()).order_by('-start_date')

    def perform_create(self, serializer):
        serializer.save(candidate=self.get_candidate())


class WorkExperienceDetailView(CandidateSubModelMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /work-experience/{id}/  → retrieve
    PATCH  /work-experience/{id}/  → update
    DELETE /work-experience/{id}/  → delete
    """
    serializer_class = WorkExperienceSerializer

    def get_queryset(self):
        return WorkExperience.objects.filter(candidate=self.get_candidate())


# Education

class EducationListCreateView(CandidateSubModelMixin, generics.ListCreateAPIView):
    serializer_class = EducationSerializer

    def get_queryset(self):
        return Education.objects.filter(candidate=self.get_candidate())

    def perform_create(self, serializer):
        serializer.save(candidate=self.get_candidate())


class EducationDetailView(CandidateSubModelMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EducationSerializer

    def get_queryset(self):
        return Education.objects.filter(candidate=self.get_candidate())


# Skills

class SkillListCreateView(CandidateSubModelMixin, generics.ListCreateAPIView):
    serializer_class = SkillSerializer

    def get_queryset(self):
        return Skill.objects.filter(candidate=self.get_candidate())

    def perform_create(self, serializer):
        serializer.save(candidate=self.get_candidate())


class SkillDetailView(CandidateSubModelMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SkillSerializer

    def get_queryset(self):
        return Skill.objects.filter(candidate=self.get_candidate())


# Certifications

class CertificationListCreateView(CandidateSubModelMixin, generics.ListCreateAPIView):
    serializer_class = CertificationSerializer

    def get_queryset(self):
        return Certification.objects.filter(candidate=self.get_candidate())

    def perform_create(self, serializer):
        serializer.save(candidate=self.get_candidate())


class CertificationDetailView(CandidateSubModelMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CertificationSerializer

    def get_queryset(self):
        return Certification.objects.filter(candidate=self.get_candidate())


# Projects

class ProjectListCreateView(CandidateSubModelMixin, generics.ListCreateAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.filter(candidate=self.get_candidate())

    def perform_create(self, serializer):
        serializer.save(candidate=self.get_candidate())


class ProjectDetailView(CandidateSubModelMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.filter(candidate=self.get_candidate())
    
class AvatarUpdateView(generics.UpdateAPIView):
    serializer_class   = AvatarSerializer
    permission_classes = [IsAuthenticated]
    http_method_names  = ['patch']

    def get_object(self):
        return self.request.user