from rest_framework import serializers
from .models import Post, PostImage, Comment, Like

class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = '__all__'
        read_only_fields = ['post', 'created_at']

class PostSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    is_liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_full_name(self, obj):
        name = f'{obj.user.first_name} {obj.user.last_name}'.strip()
        return name if name else obj.user.username

    def get_is_liked_by_me(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.user.avatar.url) if request else obj.user.avatar.url
        return None

class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = ['user', 'post', 'created_at', 'updated_at']

    def get_full_name(self, obj):
        name = f'{obj.user.first_name} {obj.user.last_name}'.strip()
        return name if name else obj.user.username

    def get_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.user.avatar.url) if request else obj.user.avatar.url
        return None

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = '__all__'
        read_only_fields = ['user', 'post', 'created_at']
