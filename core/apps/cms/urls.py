from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CollectionView

router = DefaultRouter()
router.register("collection", CollectionView, basename="collection")
urlpatterns = [path("", include(router.urls))]
