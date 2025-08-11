from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, PostViewSet, CategoryListView, CategoryDetailView,
    CommentCreateView, CommentListView, ToggleLikeView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')

urlpatterns = [
    # Registration & auth
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # returns access + refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Categories
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),

    # Posts + extra actions
    path('', include(router.urls)),

    # Comments
    path('posts/<int:post_id>/comments/', CommentListView.as_view(), name='post-comments'),
    path('posts/<int:post_id>/comments/add/', CommentCreateView.as_view(), name='add-comment'),

    # Likes
    path('posts/<int:post_id>/like-toggle/', ToggleLikeView.as_view(), name='toggle-like'),
]
