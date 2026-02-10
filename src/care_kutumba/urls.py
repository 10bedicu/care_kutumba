from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from care_kutumba.api.viewsets import BeneficiaryViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register(r"beneficiary", BeneficiaryViewSet, basename="kutumba-beneficiary")

urlpatterns = router.urls
