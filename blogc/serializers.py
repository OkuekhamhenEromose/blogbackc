from rest_framework import serializers
from django.contrib.auth.models import User, Group
from django.utils.text import slugify
from rest_framework.validators import UniqueValidator
from django.contrib.auth import authenticate

from .models import BlogCategory, BlogPost, Comment, Like, UserProfile
from .utils import SendMail

# -------------------
# Registration Serializer
# -------------------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    role = serializers.ChoiceField(
        write_only=True,
        choices=[('admin', 'admin'), ('user', 'user')],
        default='user',
        required=False
    )

    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    class Meta:
        model = User
        fields = ('username', 'password', 'first_name', 'last_name', 'email', 'role')

    def create(self, validated_data):
        role = validated_data.pop('role','user')
        password = validated_data.pop('password')
        email = validated_data.get('email')
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # Create profile
        UserProfile.objects.create(
            user=user,
            role=role,
            is_blog_admin=(role == 'admin')
        )

        # Assign to group
        group_name = 'BLOG_ADMIN' if role == 'admin' else 'BLOG_USER'
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
        SendMail(email)
        return user
# -------------------
# User Serializer
# -------------------
class UserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        default='admin',
        required=False
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'email', 'role']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        role = validated_data.pop('role', 'admin')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        UserProfile.objects.create(user=user, role=role, is_blog_admin=(role == 'admin')) 
        return user

# Add to serializers.py
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'),
                              email=email, password=password)
            if not user:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")
            
        data['user'] = user
        return data
    
# -------------------
# Category Serializer
# -------------------
class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ('id', 'name', 'slug')


# -------------------
# Blog Post Serializers
# -------------------
class BlogPostListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = BlogCategorySerializer(read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)

    class Meta:
        model = BlogPost
        fields = (
            'id', 'title', 'slug', 'author', 'category', 'published',
            'created_at', 'likes_count', 'comments_count'
        )


class BlogPostDetailSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = BlogCategorySerializer(read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = (
            'id', 'title', 'slug', 'author', 'category', 'content',
            'published', 'created_at', 'updated_at', 'likes_count', 'comments'
        )

    def get_comments(self, obj):
        qs = obj.comments.filter(active=True)
        return CommentSerializer(qs, many=True).data


class BlogPostCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(write_only=True, required=False)
    slug = serializers.SlugField(required=False)

    class Meta:
        model = BlogPost
        fields = ('title', 'slug', 'category_id', 'content', 'published')

    def validate(self, data):
        if not data.get('slug'):
            data['slug'] = slugify(data['title'])
        return data

    def create(self, validated_data):
        category_id = validated_data.pop('category_id', None)
        request = self.context.get('request')
        user = request.user  # logged-in user

        category = None
        if category_id:
            try:
                category = BlogCategory.objects.get(pk=category_id)
            except BlogCategory.DoesNotExist:
                raise serializers.ValidationError({'category_id': 'Invalid category'})

        return BlogPost.objects.create(
            category=category,
            **validated_data
        )


# -------------------
# Comment Serializer
# -------------------
class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'post', 'user', 'body', 'created_at')
        read_only_fields = ('id', 'user', 'post', 'created_at')


# -------------------
# Like Serializer
# -------------------
class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ('id', 'post', 'user', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')
