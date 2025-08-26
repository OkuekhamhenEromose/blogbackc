from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, APITestCase, APIClient
from django.urls import reverse
from .models import UserProfile, BlogCategory
from .permissions import IsBlogAdmin

class PermissionTests(TestCase):
    def setUp(self):
        # Create users - signals will automatically create profiles
        self.admin_user = User.objects.create_user(
            username='admin', 
            email='admin@test.com', 
            password='testpass123'
        )
        self.regular_user = User.objects.create_user(
            username='user', 
            email='user@test.com', 
            password='testpass123'
        )
        
        # Refresh users from database to ensure profiles are loaded
        self.admin_user.refresh_from_db()
        self.regular_user.refresh_from_db()
        
        # Update the profiles that were automatically created
        self.admin_user.profile.role = 'admin'
        self.admin_user.profile.is_blog_admin = True
        self.admin_user.profile.save()
        
        self.regular_user.profile.role = 'user'
        self.regular_user.profile.is_blog_admin = False
        self.regular_user.profile.save()

    def test_admin_permissions(self):
        permission = IsBlogAdmin()
        request = APIRequestFactory().get('/')
        request.user = self.admin_user
        
        self.assertTrue(permission.has_permission(request, None))
        
    def test_regular_user_permissions(self):
        permission = IsBlogAdmin()
        request = APIRequestFactory().get('/')
        request.user = self.regular_user
        
        self.assertFalse(permission.has_permission(request, None))
        
    def test_user_without_profile(self):
        # Create a user without triggering signals
        from django.db.models.signals import post_save
        
        # Temporarily disconnect the signal
        post_save.disconnect(receiver=None, sender=User, dispatch_uid='ensure_user_profile')
        
        try:
            user_no_profile = User.objects.create_user(
                username='noprofile', 
                email='noprofile@test.com', 
                password='testpass123'
            )
            
            permission = IsBlogAdmin()
            request = APIRequestFactory().get('/')
            request.user = user_no_profile
            
            self.assertFalse(permission.has_permission(request, None))
        finally:
            # Reconnect the signal
            from . import signals
            post_save.connect(signals.ensure_user_profile, sender=User)


class PostCreationTests(APITestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin', 
            email='admin@test.com', 
            password='testpass123'
        )
        self.admin_user.refresh_from_db()
        self.admin_user.profile.role = 'admin'
        self.admin_user.profile.is_blog_admin = True
        self.admin_user.profile.save()
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='user', 
            email='user@test.com', 
            password='testpass123'
        )
        self.regular_user.refresh_from_db()
        self.regular_user.profile.role = 'user'
        self.regular_user.profile.is_blog_admin = False
        self.regular_user.profile.save()
        
        # Create a category
        self.category = BlogCategory.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.client = APIClient()
    
    def test_admin_can_create_post(self):
        """Test that admin users can create posts"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'title': 'Test Post',
            'content': 'Test content',
            'category_id': self.category.id,
            'published': True
        }
        
        # Try different URL patterns if one doesn't work
        try:
            response = self.client.post(reverse('blogpost-list'), data)
        except:
            try:
                response = self.client.post(reverse('post-list'), data)
            except:
                response = self.client.post('/api/posts/', data)
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], 'Test Post')
    
    def test_regular_user_cannot_create_post(self):
        """Test that regular users cannot create posts"""
        self.client.force_authenticate(user=self.regular_user)
        
        data = {
            'title': 'Test Post',
            'content': 'Test content',
            'category_id': self.category.id,
            'published': True
        }
        
        # Try different URL patterns if one doesn't work
        try:
            response = self.client.post(reverse('blogpost-list'), data)
        except:
            try:
                response = self.client.post(reverse('post-list'), data)
            except:
                response = self.client.post('/api/posts/', data)
        
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_unauthenticated_user_cannot_create_post(self):
        """Test that unauthenticated users cannot create posts"""
        data = {
            'title': 'Test Post',
            'content': 'Test content',
            'category_id': self.category.id,
            'published': True
        }
        
        # Try different URL patterns if one doesn't work
        try:
            response = self.client.post(reverse('blogpost-list'), data)
        except:
            try:
                response = self.client.post(reverse('post-list'), data)
            except:
                response = self.client.post('/api/posts/', data)
        
        self.assertEqual(response.status_code, 401)  # Unauthorized