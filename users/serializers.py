from rest_framework import serializers
from .models import User, CandidateProfile, EmployerProfile, WorkExperience, Education, Skill, Certification, Project

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ['username', 'password', 'role', 'first_name', 'last_name', 'email']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            role=validated_data['role'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            email=validated_data.get('email', ''),
        )
        if user.role == User.Role.CANDIDATE:
            CandidateProfile.objects.create(user=user)
        elif user.role == User.Role.EMPLOYER:
            EmployerProfile.objects.create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


# Candidate sub-models 

class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = WorkExperience
        fields = '__all__'
        # candidate is set automatically from the logged-in user, not from request body
        read_only_fields = ['candidate']

    def validate(self, data):
        start = data.get('start_date', getattr(self.instance, 'start_date', None))
        end   = data.get('end_date',   getattr(self.instance, 'end_date', None))
        if end and start and end < start:
            raise serializers.ValidationError({'end_date': 'End date cannot be before start date.'})
        return data


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Education
        fields = '__all__'
        read_only_fields = ['candidate']


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Skill
        fields = '__all__'
        read_only_fields = ['candidate']


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Certification
        fields = '__all__'
        read_only_fields = ['candidate']

    def validate(self, data):
        issue  = data.get('issue_date',  getattr(self.instance, 'issue_date', None))
        expiry = data.get('expiry_date', getattr(self.instance, 'expiry_date', None))
        if expiry and issue and expiry < issue:
            raise serializers.ValidationError({'expiry_date': 'Expiry date cannot be before issue date.'})
        return data


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Project
        fields = '__all__'
        read_only_fields = ['candidate']

    def validate(self, data):
        start = data.get('start_date', getattr(self.instance, 'start_date', None))
        end   = data.get('end_date',   getattr(self.instance, 'end_date', None))
        if end and start and end < start:
            raise serializers.ValidationError({'end_date': 'End date cannot be before start date.'})
        return data


# Profile serializers

class AvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['avatar']

class CandidateProfileSerializer(serializers.ModelSerializer):
    # Nested read-only: returns full profile in one GET
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    licenses = CertificationSerializer(many=True, read_only=True)
    projects = ProjectSerializer(many=True, read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_email(self, obj):
        return obj.user.email
    
    class Meta:
        model  = CandidateProfile
        fields = [
            'id', 'user', 'phone', 'location', 'bio', 'cv', 'score',
            'full_name', 'email' ,'work_experiences', 'educations',
            'skills', 'licenses', 'projects',
        ]
        read_only_fields = ['user', 'score']


class EmployerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EmployerProfile
        fields = '__all__'
        read_only_fields = ['user']


class UserNameSerializer(serializers.ModelSerializer):
    """Minimal — just name fields, used by the /me/name/ endpoint."""
    class Meta:
        model  = User
        fields = ['id', 'username', 'first_name', 'last_name']