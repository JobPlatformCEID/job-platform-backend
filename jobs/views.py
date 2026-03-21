from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from .models import JobPosting , JobApplication , JobComment
from users.models import User , WorkExperience , EmployerProfile
from .serializers import (
    JobPostingSerializer, 
    JobApplicationSerializer , 
    JobApplicationStatusSerializer,
    JobCommentSerializer
)


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
    

class JobCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = JobCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        job_id = self.kwargs.get("job_id");
        #none is needed so that only the top level get returned the serializer does the rest
        return JobComment.objects.filter(job = job_id , parent_comment=None)
    
    def perform_create(self, serializer):
        try:
            job_post= JobPosting.objects.get(pk=self.kwargs.get('job_id'))
        except JobPosting.DoesNotExist:
            raise NotFound('job posting does not exist')
        
        if not self.request.data.get('content','').strip():
            raise ValidationError('content of job comment cannot be empty')
        
        parent_id = self.request.data.get('parent_comment')
            
        if parent_id:
            try:
                parent = JobComment.objects.get(pk=parent_id)
            except JobComment.DoesNotExist:
                raise NotFound('parent comment not found')
            
            if parent.job != job_post:
                raise ValidationError('parent comment does not belong to this job posting')
        
        has_experience = WorkExperience.objects.filter(
            candidate__user = self.request.user,
            company__iexact = job_post.employer.company_name,
            title__iexact =  job_post.title
        ).exists()

        # employers in the same company can also leave comments
        is_employer = (
            self.request.user.role == User.Role.EMPLOYER and
            self.request.user.employer_profile.company_name.lower() == job_post.employer.company_name.lower()
        )

        if not has_experience and not is_employer:
            raise PermissionDenied('you must have worked in this role for that company in the past to comment')

        serializer.save(job = job_post , owner= self.request.user)

class JobCommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = JobCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return JobComment.objects.get(pk=self.kwargs.get('comment_id'))
        except JobComment.DoesNotExist:
            raise NotFound('comment not found')

    def update(self, request, *args, **kwargs):
        comment = self.get_object()

        if comment.owner != self.request.user:
            raise PermissionDenied('you are not the owner of this comment you cant edit it')

        comment.edited = True
        comment.save()

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()

        if comment.owner != self.request.user:
            raise PermissionDenied('you are not the owner of this comment you cant delete it')

        #soft delete to not lose indentation in reply section in the ui
        comment.deleted = True
        comment.content = ''
        comment.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    
