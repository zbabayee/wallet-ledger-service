from django.urls import path, include
from rest_framework.routers import DefaultRouter

from wallets.api.views import WalletViewSet

router = DefaultRouter()
router.register(r"", WalletViewSet, basename="wallet")

urlpatterns = [
    path("", include(router.urls)),
]
