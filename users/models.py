from django.db import models
from django.contrib.auth.models import AbstractUser

# Custom User model: Needed because the default one doesn't have Role
class User(AbstractUser):
    class Role(models.TextChoices):
        CANDIDATE = 'candidate', 'Candidate'
        EMPLOYER = 'employer', 'Employer'

    role = models.CharField(max_length=20, choices=Role.choices)

    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name='custom_user_set'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='custom_user_set'
    )

# Profile models for each user role
class CandidateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    cv = models.FileField(upload_to='cvs/', blank=True, null=True)
    score = models.FloatField(default=0)

class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)

# Models for candidate users
class WorkExperience(models.Model):
    class EmploymentType(models.TextChoices):
        FULL_TIME  = 'full_time',  'Full Time'
        PART_TIME  = 'part_time',  'Part Time'
        FREELANCE  = 'freelance',  'Freelance'
        INTERNSHIP = 'internship', 'Internship'
        CONTRACT   = 'contract',   'Contract'

    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='work_experiences')
    title = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    start_date = models.DateField()
    location = models.CharField(max_length=100, blank=True)
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)

class Education(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='educations')
    institution = models.CharField(max_length=100)
    degree = models.CharField(max_length=100)
    field_of_study = models.CharField(max_length=100, blank=True)
    level = models.CharField(max_length=20, choices=[
        ('high_school', 'High School'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('phd', 'PhD'),
    ])
    graduation_date = models.DateField(blank=True, null=True)

class Skill(models.Model):
    class Proficiency(models.TextChoices):
        BEGINNER     = 'beginner',     'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        EXPERT       = 'expert',       'Expert'
 
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=50)
    level = models.CharField(max_length=20, choices=Proficiency.choices, default=Proficiency.BEGINNER)
