from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.apps.blog.views.admin import AdminBlogPostView
from core.apps.blog.views.public import BlogPostPublicView

router = DefaultRouter()
router.register("blog", BlogPostPublicView, basename="blog")
router.register("admin/blog", AdminBlogPostView, basename="admin-blog")

urlpatterns = [
    path("", include(router.urls)),
]
