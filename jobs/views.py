from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from .models import JobPosting, JobApplication
from .serializers import JobPostingSerializer, JobApplicationSerializer
from users.models import User

class JobPostingListCreateView(generics.ListCreateAPIView):
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return JobPosting.objects.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('Only employers can create job postings.')
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        try:
            serializer.save(employer=self.request.user.employer_profile)
        except Exception:
            raise NotFound('Employer profile not found.')

class JobPostingDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]
    queryset = JobPosting.objects.all()

    def update(self, request, *args, **kwargs):
        if request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('Only employers can update job postings.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('Only employers can delete job postings.')
        return super().destroy(request, *args, **kwargs)

class JobApplicationListView(generics.ListAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('Only employers can view applications.')
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            return JobApplication.objects.filter(job__employer=self.request.user.employer_profile)
        except Exception:
            raise NotFound('Employer profile not found.')

class JobApplyView(generics.CreateAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.CANDIDATE:
            raise PermissionDenied('Only candidates can apply for jobs.')
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.CANDIDATE:
            raise PermissionDenied('Only candidates can apply for jobs.')
        try:
            job_id = self.kwargs.get('pk')
            job = JobPosting.objects.get(pk=job_id)
            serializer.save(
                candidate=self.request.user.candidate_profile,
                job=job
            )
        except JobPosting.DoesNotExist:
            raise NotFound('Job posting not found.')
        except Exception:
            raise NotFound('Candidate profile not found.')

