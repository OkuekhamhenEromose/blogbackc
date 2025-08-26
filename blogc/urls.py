# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView,
    PublicTokenObtainPairView,
    PublicTokenRefreshView,
    PostViewSet,
    CategoryListView,
    PublicCategoryDetailView,
    AdminCategoryDetailView,
    CommentListCreateView,
    CommentDetailView,
    ToggleLikeView,
    S3TestView,
    DebugImageView
)
from . import views

# Router setup (only for posts, not categories to avoid duplication)
router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', PublicTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', PublicTokenRefreshView.as_view(), name='token_refresh'),

    # Categories
    path('categories/', CategoryListView.as_view(), name='category-list'),  # Public list, POST allowed for admins
    path('categories/<int:pk>/', PublicCategoryDetailView.as_view(), name='category-detail-public'),
    path('admin/categories/<int:pk>/', AdminCategoryDetailView.as_view(), name='category-detail-admin'),

    path('', include(router.urls)),  # Posts CRUD via router

    # Comments
    path('posts/<int:post_id>/comments/', CommentListCreateView.as_view(), name='post-comments'),
    path("comments/<int:pk>/", CommentDetailView.as_view(), name="comment-detail"),

    # Likes
    path('posts/<int:post_id>/like-toggle/', ToggleLikeView.as_view(), name='post-like'),
    # for testing display of images
    path('s3-test/', S3TestView.as_view(), name='s3-test'),
    path('debug/storage', views.debug_storage, name='debug-storage'),
    path('debug-images/', DebugImageView.as_view(), name='debug-images'),
]
