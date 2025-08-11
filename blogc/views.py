from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from django.contrib.auth.models import User, Group
from .models import Category, Post, Comment, Like
from .serializers import (
    CategorySerializer, PostListSerializer, PostDetailSerializer,
    PostCreateUpdateSerializer, CommentSerializer, LikeSerializer
)
from .permissions import IsAdminGroup, IsAuthorOrAdmin
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

# Categories
class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]  # optionally restrict creation to admin group
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminGroup()]
        return [permissions.IsAuthenticated()]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminGroup]


# Posts (public listing only for authenticated users)
class PostListView(generics.ListAPIView):
    queryset = Post.objects.filter(is_published=True).select_related('author','category').prefetch_related('comments','likes')
    serializer_class = PostListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'author__username', 'category__name']
    ordering_fields = ['created_at', 'likes_count']
    pagination_class = None  # add pagination if you wish


class AdminPostListCreateView(generics.ListCreateAPIView):
    """
    Admins create posts; admin sees only their posts in admin dashboard.
    """
    serializer_class = PostListSerializer
    permission_classes = [IsAdminGroup]

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user).select_related('category')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateUpdateSerializer
        return PostListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostDetailView(generics.RetrieveAPIView):
    queryset = Post.objects.select_related('author','category').prefetch_related('comments','likes')
    serializer_class = PostDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'  # friendly URLs


class PostUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    permission_classes = [IsAuthorOrAdmin]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PostCreateUpdateSerializer
        return PostDetailSerializer


# Comments - authenticated users can comment on published posts
class CommentCreateView(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        post_id = self.request.data.get('post')
        post = get_object_or_404(Post, id=post_id, is_published=True)
        serializer.save(user=self.request.user, post=post)


class CommentListView(generics.ListAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        post_slug = self.kwargs.get('post_slug')
        post = get_object_or_404(Post, slug=post_slug, is_published=True)
        return post.comments.filter(approved=True)


class CommentDeleteView(generics.DestroyAPIView):
    queryset = Comment.objects.all()
    permission_classes = [IsAuthorOrAdmin]


# Likes
class LikeCreateDestroyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_slug):
        post = get_object_or_404(Post, slug=post_slug, is_published=True)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if created:
            return Response({'detail': 'liked'}, status=status.HTTP_201_CREATED)
        return Response({'detail': 'already liked'}, status=status.HTTP_200_OK)

    def delete(self, request, post_slug):
        post = get_object_or_404(Post, slug=post_slug)
        Like.objects.filter(user=request.user, post=post).delete()
        return Response({'detail': 'unliked'}, status=status.HTTP_200_OK)


# Latest posts endpoint (for dashboard widgets)
class LatestPostsView(generics.ListAPIView):
    serializer_class = PostListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Post.objects.filter(is_published=True).order_by('-created_at')[:5]
