from rest_framework import serializers
from django.contrib.auth.models import User, Group
from django.utils.text import slugify
from rest_framework.validators import UniqueValidator
from django.contrib.auth import authenticate

from .models import BlogCategory, BlogPost, Comment, Like, UserProfile
# from .utils import SendMail


# -------------------
# Registration Serializer
# -------------------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    role = serializers.ChoiceField(
        write_only=True,
        choices=UserProfile.ROLE_CHOICES,
        default="user",
        required=False
    )

    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    class Meta:
        model = User
        fields = ("username", "password", "first_name", "last_name", "email", "role")

    def create(self, validated_data):
        try:
            print(f"Registration data: {validated_data}")
            role = validated_data.pop("role", "user")
            password = validated_data.pop("password")
            email = validated_data.get("email")

            user = User(**validated_data)
            user.set_password(password)
            user.save()

            print(f"User created: {user.username}")
            
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.is_blog_admin = (role == "admin")
            profile.save()

            print(f"Profile created/updated: {profile}")

            # Assign to group
            group_name = "BLOG_ADMIN" if role == "admin" else "BLOG_USER"
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

            print(f"Added to group: {group_name}")

        # Update profile role + admin flag

        # Send welcome email (optional)
        # if email:
        #     try:
        #         SendMail(email)
        #     except Exception as e:
        #         print(f"Email sending failed: {e}")
            return user
        except Exception as e:
                print(f"Registration failed: {str(e)}")
                raise

# -------------------
# User Serializer
# -------------------
class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    is_blog_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role", "is_blog_admin"]

    def _get_profile(self, obj):
        # Support both attribute names defensively
        return getattr(obj, "profile", None) or getattr(obj, "userprofile", None)

    def get_role(self, obj):
        prof = self._get_profile(obj)
        return getattr(prof, "role", "user") if prof else "user"

    def get_is_blog_admin(self, obj):
        prof = self._get_profile(obj)
        return bool(getattr(prof, "is_blog_admin", False)) if prof else False


# -------------------
# Login Serializer
# -------------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        if email and password:
            try:
                user_obj = User.objects.get(email=email)
                username = user_obj.username
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid email or password.")

            user = authenticate(request=self.context.get("request"), username=username, password=password)
            if not user:
                raise serializers.ValidationError("Invalid email or password.")
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")

        data["user"] = user
        return data


# -------------------
# Category Serializer
# -------------------
class BlogCategorySerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="name", read_only=True)
    class Meta:
        model = BlogCategory
        fields = ("id", "name", "title", "slug")


# -------------------
# Blog Post Serializers
# -------------------
class BlogPostListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = BlogCategorySerializer(read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    comments_count = serializers.IntegerField(source="comments.count", read_only=True)
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        if obj.image:
            try:
                # Get the URL from the storage
                url = obj.image.url
                # Ensure we have a complete URL
                if not url.startswith(('http://', 'https://')):
                    # If URL is relative, try to build absolute URL
                    request = self.context.get('request')
                    if request:
                        url = request.build_absolute_uri(url)
                    else:
                        clean_url = url.lstrip('/')
                        url = f'https://blogbackc.s3.eu-north-1.amazonaws.com/media/{clean_url}'
                
                return url
                
            except Exception as e:
                # Log the error for debugging
                print(f"Error getting image URL for object {obj.id}: {e}")
                return None
        return None

    class Meta:
        model = BlogPost
        fields = (
            "id", "title", "slug", "author", "category", "published",
            "created_at", "likes_count", "comments_count", "content", "image"
        )


class BlogPostDetailSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = BlogCategorySerializer(read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    comments = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        if obj.image:
            try:
                # Get the URL from the storage
                url = obj.image.url             
                # Ensure we have a complete URL
                if not url.startswith(('http://', 'https://')):
                    request = self.context.get('request')
                    if request:
                        url = request.build_absolute_uri(url)
                    else:
                        clean_url = url.lstrip('/')
                        url = f'https://blogbackc.s3.eu-north-1.amazonaws.com/media/{clean_url}'
                
                return url
            except Exception as e:
                print(f"Error getting image URL for object {obj.id}: {e}")
                return None
        return None
    def get_comments(self, obj):
        qs = obj.comments.filter(active=True)
        return CommentSerializer(qs, many=True).data

    # ADD THE MISSING META CLASS
    class Meta:
        model = BlogPost
        fields = (
            "id", "title", "slug", "author", "category", "content", "image",
            "published", "created_at", "updated_at", "likes_count", "comments"
        )

class BlogCategoryDetailSerializer(serializers.ModelSerializer):
    posts = BlogPostListSerializer(many=True, read_only=True)
    total_posts = serializers.IntegerField(source="posts.count", read_only=True)
    total_comments = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()

    class Meta:
        model = BlogCategory
        fields = ("id", "name", "slug", "total_posts", "total_comments", "total_likes", "posts")

    def get_total_comments(self, obj):
        return Comment.objects.filter(post__category=obj).count()

    def get_total_likes(self, obj):
        return Like.objects.filter(post__category=obj).count()        

class BlogPostCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(write_only=True, required=True)
    image = serializers.ImageField(required=False, allow_null=True, max_length=100)

    class Meta:
        model = BlogPost
        fields = ("id", "title", "content", "category_id", "image", "published")

    def validate_category_id(self, value):
        if not BlogCategory.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Category does not exist.")
        return value


# -------------------
# Comment Serializer
# -------------------
class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "post", "user", "body", "created_at")
        read_only_fields = ("id", "user", "post", "created_at")


# -------------------
# Like Serializer
# -------------------
class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ("id", "post", "user", "created_at")
        read_only_fields = ("id", "user", "created_at")
