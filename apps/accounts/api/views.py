from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse, extend_schema_view
from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from common.tools import get_client_ip
from .permissions import IsSelfOrAdmin
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    LoginSerializer, TokenResponseSerializer, LogoutSerializer
)
from ..services.user_services import UserService, AuthService

User = get_user_model()


@extend_schema(
    tags=["Authentication"],
    summary="Register new user",
    description="Create a new user and return JWT access and refresh tokens.",
    request=UserCreateSerializer,
    responses={
        201: TokenResponseSerializer,
        400: OpenApiResponse(description="Validation Error"),
    },
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response_data = UserService.register_user(serializer.validated_data)
        return Response(
            response_data,
            status=status.HTTP_201_CREATED
        )


@extend_schema(
    tags=["Authentication"],
    summary="User login",
    description="Authenticate user and return JWT tokens.",
    request=LoginSerializer,
    responses={
        200: TokenResponseSerializer,
        400: OpenApiResponse(description="Invalid credentials"),
    },
)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        response_data = AuthService.login_user(
            user=user,
            request=request
        )
        return Response(
            response_data,
            status=status.HTTP_200_OK
        )

@extend_schema(
    tags=["Authentication"],
    summary="User logout",
    description="Blacklist refresh token and logout user.",
    request=LogoutSerializer,
    responses={
        200: OpenApiResponse(
            description="Successfully logged out"
        ),
        400: OpenApiResponse(
            description="Invalid Token"
        ),
    },
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid( raise_exception=True)
        try:
            response_data = AuthService.logout_user(serializer.validated_data["refresh"])
        except ValueError as e:
            return Response({"error": str(e) }, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            response_data,
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Users"],
    summary="List users",
    description="Retrieve list of users. Admin can see all users, normal users see active users only.",
    responses={
        200: UserSerializer(many=True),
    },
)
class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'date_joined']
    search_fields = ['username', 'email', 'mobile', 'first_name', 'last_name']
    ordering_fields = ['id', 'username', 'date_joined', 'last_login']
    ordering = ['-date_joined']

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(is_active=True)


@extend_schema_view(
    retrieve=extend_schema(
        tags=["Users"],
        summary="Get user details",
        responses={
            200: UserSerializer,
        },
    ),

    update=extend_schema(
        tags=["Users"],
        summary="Update user",
        request=UserUpdateSerializer,
        responses={
            200: UserSerializer,
        },
    ),

    partial_update=extend_schema(
        tags=["Users"],
        summary="Partial update user",
        request=UserUpdateSerializer,
        responses={
            200: UserSerializer,
        },
    ),

    destroy=extend_schema(
        tags=["Users"],
        summary="Deactivate user",
        description="Soft delete user by setting is_active=False.",
        responses={
            204: OpenApiResponse(
                description="User deactivated successfully"
            ),
        },
    ),
)
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSelfOrAdmin]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
        return instance


@extend_schema_view(
    retrieve=extend_schema(
        tags=["Profile"],
        summary="Get current user profile",
        responses={
            200: UserSerializer,
        },
    ),

    update=extend_schema(
        tags=["Profile"],
        summary="Update current user profile",
        request=UserUpdateSerializer,
        responses={
            200: UserSerializer,
        },
    ),

    partial_update=extend_schema(
        tags=["Profile"],
        summary="Partial update current user profile",
        request=UserUpdateSerializer,
        responses={
            200: UserSerializer,
        },
    ),
)
class UserMeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer

    def perform_update(self, serializer):
        serializer.save()
