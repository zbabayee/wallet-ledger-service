from django.db import models
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from transactions.api.serializers import (
    DepositSerializer,
    TransactionSerializer,
    TransferSerializer,
    WithdrawSerializer,
)
from transactions.models import Transaction, TransactionStatus
from transactions.services.transaction_service import (
    deposit,
    transfer,
    withdraw,
)


class DepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=DepositSerializer,
        responses={
            201: TransactionSerializer,
            200: TransactionSerializer,
            400: OpenApiResponse(description="Validation or business error"),
        },
        description="Deposit funds into a wallet. Idempotent via idempotency_key.",
        examples=[
            OpenApiExample(
                "Valid deposit",
                value={
                    "wallet": 1,
                    "amount": "150.00",
                    "idempotency_key": "deposit-001",
                    "description": "Salary deposit",
                },
                request_only=True,
            ),
        ],
        tags=["Transactions"],
    )
    def post(self, request):
        serializer = DepositSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        txn, replayed = deposit(
            wallet_id=data["wallet"].id,
            amount=data["amount"],
            idempotency_key=data["idempotency_key"],
            user=request.user,
            description=data.get("description", ""),
        )

        if txn.status == TransactionStatus.FAILED:
            return Response(
                TransactionSerializer(txn).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            TransactionSerializer(txn).data,
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )


class WithdrawView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=WithdrawSerializer,
        responses={
            201: TransactionSerializer,
            200: TransactionSerializer,
            400: OpenApiResponse(description="Validation or business error"),
        },
        description="Withdraw funds from a wallet. Idempotent via idempotency_key.",
        tags=["Transactions"],
    )
    def post(self, request):
        serializer = WithdrawSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        txn, replayed = withdraw(
            wallet_id=data["wallet"].id,
            amount=data["amount"],
            idempotency_key=data["idempotency_key"],
            user=request.user,
            description=data.get("description", ""),
        )

        if txn.status == TransactionStatus.FAILED:
            return Response(
                TransactionSerializer(txn).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            TransactionSerializer(txn).data,
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )


class TransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=TransferSerializer,
        responses={
            201: TransactionSerializer,
            200: TransactionSerializer,
            400: OpenApiResponse(description="Validation or business error"),
        },
        description=(
            "Transfer funds between two wallets. "
            "Both wallets must use the same currency. "
            "Idempotent via idempotency_key."
        ),
        tags=["Transactions"],
    )
    def post(self, request):
        serializer = TransferSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        txn, replayed = transfer(
            from_wallet_id=data["from_wallet"].id,
            to_wallet_id=data["to_wallet"].id,
            amount=data["amount"],
            idempotency_key=data["idempotency_key"],
            user=request.user,
            description=data.get("description", ""),
        )

        if txn.status == TransactionStatus.FAILED:
            return Response(
                TransactionSerializer(txn).data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            TransactionSerializer(txn).data,
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description="Retrieve transaction history for the authenticated user.",
        tags=["Transactions"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        return (
            Transaction.objects.filter(
                models.Q(from_wallet__user=user)
                | models.Q(to_wallet__user=user)
            )
            .select_related(
                "from_wallet",
                "to_wallet",
            )
            .order_by("-created_at")
        )