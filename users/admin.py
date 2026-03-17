from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, CandidateProfile, EmployerProfile, WorkExperience, Education, Skill

# Custom User model
admin.site.register(User, UserAdmin)
admin.site.register(CandidateProfile)
admin.site.register(EmployerProfile)
admin.site.register(WorkExperience)
admin.site.register(Education)
admin.site.register(Skill)
