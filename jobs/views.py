from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from .models import JobPosting, JobApplication
from .serializers import JobPostingSerializer, JobApplicationSerializer , JobApplicationStatusSerializer
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
        #make sure that the user that tries to update the job is an employer
        if request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('Only employers can update job postings.')

        #make sure that other employers can't update jobs created by other employers
        job = self.get_object()
        if job.employer != request.user.employer_profile:
            raise PermissionDenied('Only the employer that made the job posting can update it.')
        
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('Only employers can delete job postings.')
        
        #make sure that other employers can't delete jobs created by other employers
        job = self.get_object()
        if job.employer != request.user.employer_profile:
            raise PermissionDenied('Only the employer that made the job posting can delete it.')
        
        return super().destroy(request, *args, **kwargs)

class JobApplicationListView(generics.ListAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            if self.request.user.role == User.Role.EMPLOYER:
                # Employer sees all applications for their job postings
                return JobApplication.objects.filter(job__employer=self.request.user.employer_profile)
            else:
                # Candidate sees only their own applications
                return JobApplication.objects.filter(candidate=self.request.user.candidate_profile)
        except Exception:
            raise NotFound('Profile not found.')

class JobApplyView(generics.CreateAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.CANDIDATE:
            raise PermissionDenied('Only candidates can apply for jobs.')
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        try:
            job_id = self.kwargs.get('pk')
            job = JobPosting.objects.get(pk=job_id)
            serializer.save(
                candidate=self.request.user.candidate_profile,
                job=job
            )
        except JobPosting.DoesNotExist:
            raise NotFound('Job posting not found.')
        except IntegrityError:
            raise ValidationError('You have already applied for this job.')
        except Exception:
            raise NotFound('Candidate profile not found.')

class JobApplicationStatusView(generics.UpdateAPIView):
    serializer_class = JobApplicationStatusSerializer
    permission_classes = [IsAuthenticated]

    #extend the drfs code 
    #we do a security check before we update the status
    def get_object(self):
        if self.request.user.role != User.Role.EMPLOYER:
            raise PermissionDenied('only employers can update application status.')
        
        try:
            application = JobApplication.objects.get(pk=self.kwargs.get('pk'))
        except JobApplication.DoesNotExist :
            raise NotFound('Application does not exist.')
        
        if application.job.employer != self.request.user.employer_profile:
            raise PermissionDenied('Only the employer that owns this application can update it')
        
        return application
    
