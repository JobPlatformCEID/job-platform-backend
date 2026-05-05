from rest_framework import serializers
from .models import User, CandidateProfile, EmployerProfile, WorkExperience, Education, Skill

# Register serializer: Get username, password, role from JSON and create the user
# After that, also create CandidateProfile or EmployerProfile based on role.
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
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

# User serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role', 'avatar']
        read_only_fields = ['id', 'username', 'role']

# Login serializer: Simple serializer for username and password
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class CandidateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateProfile
        fields = '__all__'
        read_only_fields = ['user' , 'score']

class EmployerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerProfile
        fields = '__all__'
        read_only_fields = ['user']

class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = '__all__'
        read_only_fields = ['candidate']

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = '__all__'
        read_only_fields = ['candidate']

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = '__all__'
        read_only_fields = ['candidate']

class EmployerListSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = EmployerProfile
        fields = ['id', 'company_name', 'location', 'website', 'user', 'avatar']

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.user.avatar and request:
            return request.build_absolute_uri(obj.user.avatar.url)
        return None
