from django.conf import settings
from django.http import JsonResponse
from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from care_kutumba.api.viewsets import BeneficiaryViewSet


def ping(request):
    return JsonResponse({"status": "OK", "plugin": "care_kutumba"})


router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register(r"beneficiary", BeneficiaryViewSet, basename="kutumba-beneficiary")

urlpatterns = [
    path("ping/", ping, name="care-kutumba-ping"),
    *router.urls,
]
