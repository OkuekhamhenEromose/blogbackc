from django.urls import path
from .views import (
    CategoryListCreateView, CategoryDetailView,
    PostListView, PostDetailView, AdminPostListCreateView, PostUpdateDestroyView,
    CommentCreateView, CommentListView, CommentDeleteView,
    LikeCreateDestroyView, LatestPostsView
)

urlpatterns = [
    # categories
    path('categories/', CategoryListCreateView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),

    # public posts listing (authenticated only)
    path('posts/', PostListView.as_view(), name='post-list'),
    path('posts/latest/', LatestPostsView.as_view(), name='post-latest'),
    path('posts/<slug:slug>/', PostDetailView.as_view(), name='post-detail'),

    # admin dashboard posts (create & list own posts)
    path('admin/posts/', AdminPostListCreateView.as_view(), name='admin-post-list-create'),
    path('admin/posts/<slug:slug>/', PostUpdateDestroyView.as_view(), name='admin-post-update-destroy'),

    # comments
    path('posts/<slug:post_slug>/comments/', CommentListView.as_view(), name='comments-list'),
    path('comments/create/', CommentCreateView.as_view(), name='comments-create'),
    path('comments/<int:pk>/', CommentDeleteView.as_view(), name='comments-delete'),

    # likes
    path('posts/<slug:post_slug>/like/', LikeCreateDestroyView.as_view(), name='post-like'),
]
