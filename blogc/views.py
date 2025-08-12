from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import BlogCategory, BlogPost, Comment, Like, UserProfile
from .serializers import (
    RegisterSerializer, UserSerializer,
    BlogCategorySerializer, BlogPostListSerializer,
    BlogPostDetailSerializer, BlogPostCreateSerializer,
    CommentSerializer, LikeSerializer
)
from .permissions import IsBlogAdmin, IsAuthorOrReadOnly

# ----------------- Registration -----------------
@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = []  # Anyone can register
    authentication_classes = []


# ----------------- Categories -----------------
class CategoryListView(generics.ListCreateAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    permission_classes = [IsAuthenticated, IsBlogAdmin]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    permission_classes = [IsAuthenticated, IsBlogAdmin]


# ----------------- Blog Posts -----------------
@method_decorator(csrf_exempt, name='dispatch')
class PostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.select_related('author', 'category').all()
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'content', 'category__name', 'author__username']
    ordering_fields = ['created_at', 'updated_at']

    def get_permissions(self):
        permission_classes = [IsAuthenticated]
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes.append(IsAuthorOrReadOnly)
        return [p() for p in permission_classes]

    def get_serializer_class(self):
        if self.action in ['list', 'latest', 'my_posts']:
            return BlogPostListSerializer
        elif self.action == 'retrieve':
            return BlogPostDetailSerializer
        return BlogPostCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

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
