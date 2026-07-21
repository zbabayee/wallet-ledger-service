from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .serializers import WalletCreateSerializer, WalletSerializer
from ..models import Wallet


class WalletListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Wallet.objects.filter(user=self.request.user)
            .select_related("currency")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        return WalletSerializer if self.request.method == "GET" else WalletCreateSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        output = WalletSerializer(serializer.instance)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)
