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

        if email:
            try:
                SendMail(email)
            except Exception as e:
                print(f"Email sending failed: {e}")

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
    image = serializers.SerializerMethodField()
    def get_image(self, obj):
        if obj.image:
            # If the URL is already absolute (S3), return as is
            if obj.image.url.startswith('http'):
                return obj.image.url
            # Otherwise, build absolute URL for local files
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None
    
    class Meta:
        model = BlogPost
        fields = (
            'id', 'title', 'slug', 'author', 'category', 'published',
            'created_at', 'likes_count', 'comments_count', 'content', 'image'
        )
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        if rep.get('image') and request:
            rep['image'] = request.build_absolute_uri(rep['image'])
        return rep

# for informations in each category
class BlogCategoryDetailSerializer(serializers.ModelSerializer):
    posts = BlogPostListSerializer(many=True, read_only=True)
    total_posts = serializers.IntegerField(source="posts.count", read_only=True)
    total_comments = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()

    class Meta:
        model = BlogCategory
        fields = (
            "id", "name", "slug",
            "total_posts", "total_comments", "total_likes",
            "posts"
        )

    def get_total_comments(self, obj):
        return Comment.objects.filter(post__category=obj).count()

    def get_total_likes(self, obj):
        return Like.objects.filter(post__category=obj).count()


class BlogPostDetailSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = BlogCategorySerializer(read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None
    class Meta:
        model = BlogPost
        fields = (
            'id', 'title', 'slug', 'author', 'category', 'content', 'image',
            'published', 'created_at', 'updated_at', 'likes_count', 'comments'
        )
    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and hasattr(obj.image, "url"):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def get_comments(self, obj):
        qs = obj.comments.filter(active=True)
        return CommentSerializer(qs, many=True).data

class BlogPostCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(
        write_only=True,
        required=True,
        min_value=1,
        help_text="ID of the category"
    )
    image = serializers.ImageField(
        required=False,
        allow_null=True,
        max_length=100
    )

    class Meta:
        model = BlogPost
        fields = ('id', 'title', 'content', 'category_id', 'image', 'published')
        extra_kwargs = {
            'category': {'read_only': True}
        }

    def validate_category_id(self, value):
        if not BlogCategory.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Category does not exist")
        return value

    def create(self, validated_data):
        return super().create(validated_data)
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
