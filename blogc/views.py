# views.py
from rest_framework import generics, status, viewsets, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import RetrieveAPIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.text import slugify
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from .models import BlogCategory, BlogPost, Comment, Like, UserProfile
from .serializers import (
    RegisterSerializer, UserSerializer,
    BlogCategorySerializer, BlogPostListSerializer,
    BlogPostDetailSerializer, BlogPostCreateSerializer,
    CommentSerializer, BlogCategoryDetailSerializer, LikeSerializer
)
from .permissions import IsBlogAdmin, IsAuthorOrReadOnly
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# for testing for the image display
from django.http import JsonResponse
from django.views import View
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.storage import default_storage
from .storage_backends import MediaStorage

def debug_storage(request):
    # Test default storage
    default_storage_class = str(default_storage.__class__)
    
    # Test custom storage
    try:
        custom_storage = MediaStorage()
        custom_storage_class = str(custom_storage.__class__)
        custom_bucket = getattr(custom_storage, 'bucket_name', 'N/A')
    except Exception as e:
        custom_storage_class = f"Error: {e}"
        custom_bucket = "N/A"
    
    return JsonResponse({
        'settings_default_storage': getattr(settings, 'DEFAULT_FILE_STORAGE', 'NOT SET'),
        'actual_default_storage': default_storage_class,
        'custom_storage_class': custom_storage_class,
        'custom_bucket': custom_bucket,
    })

class S3TestView(View):
    def get(self, request):
        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            
            # Test listing buckets
            response = s3.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            
            # Test if our bucket exists
            bucket_exists = settings.AWS_STORAGE_BUCKET_NAME in buckets
            
            return JsonResponse({
                'status': 'success',
                'buckets': buckets,
                'target_bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'bucket_exists': bucket_exists,
                'region': settings.AWS_S3_REGION_NAME
            })
            
        except ClientError as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e),
                'error_code': e.response['Error']['Code']
            }, status=500)

# Add to views.py
class DebugImageView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        posts = BlogPost.objects.all()
        data = []
        for post in posts:
            data.append({
                'id': post.id,
                'title': post.title,
                'image_url': post.image.url if post.image else None,
                'image_starts_with_http': post.image.url.startswith('http') if post.image else False,
                'absolute_url': request.build_absolute_uri(post.image.url) if post.image else None
            })
        return Response(data)
# ----------------- Registration -----------------
@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ['post', 'options']

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email_or_username = attrs.get("email") or attrs.get("username")
        password = attrs.get("password")

        user = None
        if email_or_username and password:
            user = authenticate(request=self.context.get('request'),
            email=email_or_username, password=password)
            if not user:
                user = authenticate(request=self.context.get('request'),
                username=email_or_username, password=password)

        if not user:
            raise serializers.ValidationError(
                self.error_messages['no_active_account'], code='no_active_account'
            )

        refresh = self.get_token(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }


class PublicTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = MyTokenObtainPairSerializer
    authentication_classes = []


class PublicTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []


# ----------------- Categories -----------------
# class CategoryListView(generics.ListCreateAPIView):
#     queryset = BlogCategory.objects.all()  # Remove the filter initially
#     serializer_class = BlogCategorySerializer
    
#     def get_permissions(self):
#         if self.request.method == 'GET':
#             return [AllowAny()]
#         return [IsAuthenticated(), IsBlogAdmin()]
    
#     def get_queryset(self):
#         # Only exclude if the category exists
#         if BlogCategory.objects.filter(name='Test Category').exists():
#             return BlogCategory.objects.exclude(name='Test Category')
#         return BlogCategory.objects.all()
class CategoryListView(generics.ListCreateAPIView):
    serializer_class = BlogCategorySerializer
    permission_classes = [AllowAny]  # Start with simplest permissions
    
    def get_queryset(self):
        try:
            return BlogCategory.objects.all()
        except Exception as e:
            print(f"Database error: {e}")
            return BlogCategory.objects.none()
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in category list: {str(e)}")
            return Response(
                {"error": "Unable to fetch categories", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Admin-only Category detail
class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    permission_classes = [IsAuthenticated, IsBlogAdmin]


# Public Category detail (read-only)
class PublicCategoryDetailView(generics.RetrieveAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategoryDetailSerializer
    permission_classes = [AllowAny]


# List all categories (readonly)
class BlogCategoryViewSet(ReadOnlyModelViewSet):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    permission_classes = [AllowAny]


# Public: list posts in a category
class CategoryPostsView(generics.ListAPIView):
    serializer_class = BlogPostListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        category_id = self.kwargs["pk"]
        return BlogPost.objects.filter(category_id=category_id, published=True)


# ----------------- Blog Posts -----------------
@method_decorator(csrf_exempt, name='dispatch')
class PostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.select_related('author', 'category').all()
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'content', 'category__name', 'author__username']
    ordering_fields = ['created_at', 'updated_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'latest']:
            permission_classes = [AllowAny]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated, IsBlogAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
        else:
            permission_classes = [IsAuthenticated]
        return [p() for p in permission_classes]

    def get_serializer_class(self):
        if self.action in ['list', 'latest', 'my_posts']:
            return BlogPostListSerializer
        elif self.action == 'retrieve':
            return BlogPostDetailSerializer
        return BlogPostCreateSerializer

    def perform_create(self, serializer):
        title = serializer.validated_data.get('title')
        base_slug = slugify(title)
        slug = base_slug

        # Ensure unique slug
        counter = 1
        while BlogPost.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        category_id = self.request.data.get('category_id')
        category = BlogCategory.objects.filter(pk=category_id).first()
        if not category:
            raise ValidationError({'category_id': 'This field is required'})
        serializer.save(
            author=self.request.user,
            category=category,
            slug=slug
        )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            print("Error creating post:", str(e))
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = BlogPostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = BlogPostDetailSerializer(instance, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        qs = BlogPost.objects.filter(published=True).order_by('-created_at')[:5]
        serializer = BlogPostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-posts')
    def my_posts(self, request):
        qs = BlogPost.objects.filter(author=request.user).order_by('-created_at')
        serializer = BlogPostListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

class CheckUserPermissionsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        try:
            profile = user.profile
            return Response({
                'username': user.username,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'profile_exists': True,
                'profile_role': profile.role,
                'is_blog_admin': profile.is_blog_admin,
                'has_create_permission': profile.is_blog_admin
            })
        except UserProfile.DoesNotExist:
            return Response({
                'username': user.username,
                'profile_exists': False,
                'has_create_permission': False
            })

# ----------------- Comments -----------------
# ADD THIS COMBINED VIEW:
@method_decorator(csrf_exempt, name='dispatch')
class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        post_id = self.kwargs['post_id']
        return Comment.objects.filter(post__id=post_id, active=True).order_by('created_at')

    def perform_create(self, serializer):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(BlogPost, pk=post_id)
        serializer.save(user=self.request.user, post=post)

@method_decorator(csrf_exempt, name='dispatch')
class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]

    def perform_update(self, serializer):
        prof = getattr(self.request.user, "profile", None)
        if self.request.user != serializer.instance.user and not (prof and prof.is_blog_admin):
            raise PermissionDenied("You do not have permission to edit this comment")
        serializer.save()

    def perform_destroy(self, instance):
        prof = getattr(self.request.user, "profile", None)
        if self.request.user != instance.user and not (prof and prof.is_blog_admin):
            raise PermissionDenied("You do not have permission to delete this comment")
        instance.delete()


# ----------------- Likes -----------------
@method_decorator(csrf_exempt, name='dispatch')
class ToggleLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(BlogPost, pk=post_id)
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if created:
            return Response({'message': 'liked'}, status=status.HTTP_201_CREATED)
        like.delete()
        return Response({'message': 'unliked'}, status=status.HTTP_200_OK)
