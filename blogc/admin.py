from django.contrib import admin
from .models import BlogCategory, BlogPost, Comment, Like, UserProfile

class BlogPostAdmin(admin.ModelAdmin):
    # This ensures the file upload works properly
    class Meta:
        model = BlogPost

admin.site.register(BlogPost, BlogPostAdmin)
admin.site.register(BlogCategory)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(UserProfile)
