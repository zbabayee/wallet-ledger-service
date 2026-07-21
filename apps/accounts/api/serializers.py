from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
import re

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'mobile',
            'first_name',
            'last_name',
            'full_name',
            'date_joined',
            'last_login',
            'is_active',
        )
        read_only_fields = (
            'id',
            'date_joined',
            'last_login',
            'is_active',
        )

    def get_full_name(self, obj):
        return {obj.first_name + " " + obj.last_name}


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'mobile',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
        )

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Password and confirm password doesn't match"})
        try:
            validate_password(data['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        if data.get('email'):
            if User.objects.filter(email=data['email']).exists():
                raise serializers.ValidationError({"email": "Email already exists"})
        if data.get('mobile'):
            if User.objects.filter(mobile=data['mobile']).exists():
                raise serializers.ValidationError({"mobile": "mobile already exists"})
        return data



class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'mobile',
        )

    def validate_email(self, value):
        if value:
            if User.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
                raise serializers.ValidationError("Email already exists")
        return value

    def validate_mobile(self, value):
        if value:
            if User.objects.exclude(pk=self.instance.pk).filter(mobile=value).exists():
                raise serializers.ValidationError("mobile already exists")
        return value


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    mobile = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        username = data.get('username')
        email = data.get('email')
        mobile = data.get('mobile')
        password = data.get('password')

        if not any([username, email, mobile]):
            raise serializers.ValidationError("Invalid Inputs")

        user = None
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                pass

        if not user and email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                pass

        if not user and mobile:
            try:
                user = User.objects.get(mobile=mobile)
            except User.DoesNotExist:
                pass

        if not user:
            raise serializers.ValidationError("Invalid Inputs")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid Username/Password")

        if not user.is_active:
            raise serializers.ValidationError("Invalid Username/Password")

        data['user'] = user
        return data


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)

    def validate_refresh(self, value):
        try:
            RefreshToken(value)
        except Exception:
            raise serializers.ValidationError("Invalid Token")
        return value