"""Income URL configuration."""
from rest_framework.routers import DefaultRouter

from .views import IncomeViewSet

router = DefaultRouter()
router.register(r"income", IncomeViewSet, basename="income")
urlpatterns = router.urls
