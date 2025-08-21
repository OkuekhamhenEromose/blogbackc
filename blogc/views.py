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


# ----------------- Registration -----------------
@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


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
class CategoryListView(generics.ListCreateAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsBlogAdmin()]


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
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
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
        category = None
        if category_id:
            try:
                category = BlogCategory.objects.get(pk=category_id)
            except BlogCategory.DoesNotExist:
                raise ValidationError({'category_id': 'Invalid category ID'})
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


# ----------------- Comments -----------------
@method_decorator(csrf_exempt, name='dispatch')
class CommentCreateView(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(BlogPost, pk=post_id)
        serializer.save(user=self.request.user, post=post)


@method_decorator(csrf_exempt, name='dispatch')
class CommentListView(generics.ListAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        post_id = self.kwargs['post_id']
        return Comment.objects.filter(post__id=post_id, active=True).order_by('created_at')


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
