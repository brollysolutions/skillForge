from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'is_active', 'bio', 'created_at']
        read_only_fields = ['id', 'email', 'role', 'is_active', 'created_at']


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        attrs['email'] = attrs.get('email', '').strip().lower()
        result = super().validate(attrs)
        result['user'] = UserSerializer(self.user).data
        return result


class InviteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=200)
    password = serializers.CharField(max_length=128, write_only=True)


class StudentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'is_active', 'bio', 'created_at']
        read_only_fields = ['id', 'email', 'created_at']


class ResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ConfirmResetSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=200)
    password = serializers.CharField(max_length=128)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(max_length=128, write_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
