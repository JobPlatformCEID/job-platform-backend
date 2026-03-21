from django.db import models
from users.models import User , CandidateProfile, EmployerProfile
from mptt.models import MPTTModel, TreeForeignKey

# Job Posting model: Employer creates it publicly for all candidates
class JobPosting(models.Model):
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name='job_postings')
    title = models.CharField(max_length=100)
    description = models.TextField()
    requirements = models.TextField(blank=True)
    salary_min = models.PositiveIntegerField(blank=True, null=True)
    salary_max = models.PositiveIntegerField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    is_remote = models.BooleanField(default=False)
    contract_type = models.CharField(max_length=20, choices=[
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('freelance', 'Freelance'),
        ('internship', 'Internship'),
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

# Job application model: Candidate creates it for a specific job posting
class JobApplication(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    # Prevent duplicate applications to a job by the same person
    class Meta:
        unique_together = (('candidate','job'),)

# Job comment model : users with past work experience in that role in that company can comment on a job posting
# NOTE: when a posting is deleted all of its comments should go too , but if a user is gone his comments can stay
class JobComment(MPTTModel):
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='comments')
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='job_comment_owner')
    parent_comment = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    class MPTTMeta:
        order_insertion_by = ['created_at']
