from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from care_kutumba.api.viewsets import BeneficiaryViewSet, PatientLinkViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register(r"beneficiary", BeneficiaryViewSet, basename="kutumba-beneficiary")
router.register(r"patient_link", PatientLinkViewSet, basename="kutumba-patient-link")

urlpatterns = router.urls
