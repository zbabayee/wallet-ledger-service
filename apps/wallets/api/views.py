from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response

from .serializers import WalletCreateSerializer, WalletSerializer, WalletUpdateSerializer
from ..models import Wallet


@extend_schema_view(
    list=extend_schema(
        description="Retrieve all wallets belonging to the authenticated user.",
        summary="List user wallets",
        tags=["Wallets"],
    ),
    create=extend_schema(
        description="Create a new wallet for the authenticated user.",
        summary="Create wallet",
        tags=["Wallets"],
        examples=[
            OpenApiExample(
                "Valid wallet creation",
                value={
                    "currency": "550e8400-e29b-41d4-a716-446655440000",  # فرض UUID
                    "label": "My savings",
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        description="Get details of a specific wallet.",
        summary="Retrieve wallet",
        tags=["Wallets"],
    ),
    partial_update=extend_schema(
        description="Update wallet label. Only the label can be modified.",
        summary="Update wallet label",
        tags=["Wallets"],
        examples=[
            OpenApiExample(
                "Update label",
                value={"label": "New label"},
                request_only=True,
            ),
        ],
    ),
    destroy=extend_schema(
        description="Deletion of wallets is not allowed.",
        summary="Delete wallet (not allowed)",
        tags=["Wallets"],
        responses={405: OpenApiResponse(description="Method not allowed")},
    ),
)
class WalletViewSet(viewsets.ModelViewSet):
        permission_classes = [permissions.IsAuthenticated]
        http_method_names = ["get", "post", "patch", "head", "options"]
        lookup_field = "pk"

        def get_queryset(self):
            return (
                Wallet.objects.filter(user=self.request.user)
                .select_related("currency")
                .order_by("-created_at")
            )

        def get_serializer_class(self):
            if self.action == "create":
                return WalletCreateSerializer
            elif self.action in ("update", "partial_update"):
                return WalletUpdateSerializer
            return WalletSerializer

        def perform_create(self, serializer):
            serializer.save(user=self.request.user)

        def destroy(self, request, *args, **kwargs):
            return Response(
                {"detail": "Deletion of wallets is not allowed."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )