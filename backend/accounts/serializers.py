from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password
from rest_framework.exceptions import AuthenticationFailed
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'is_active', 'bio', 'created_at']
        read_only_fields = ['id', 'email', 'role', 'is_active', 'created_at']


class AccessRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        token = self.token_class(attrs['refresh'])
        user = User.objects.filter(pk=token.get(api_settings.USER_ID_CLAIM), is_active=True).first()
        if not user or token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
            raise AuthenticationFailed('Access has been revoked. Sign in again.')
        return super().validate(attrs)


class InviteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class StudentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'is_active', 'bio', 'created_at']
        read_only_fields = ['id', 'email', 'created_at']


class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'is_active', 'bio', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        actor = self.context['request'].user
        role = attrs.get('role', getattr(self.instance, 'role', 'trainer'))
        if role not in (['trainer', 'sales'] if actor.role == 'admin' else ['trainer']):
            if not (self.instance and self.instance.pk == actor.pk and role == 'admin' and attrs.get('is_active', True)):
                raise serializers.ValidationError('Only the admin can manage sales access. The single admin cannot be disabled or created here.')
        if self.instance and role != self.instance.role:
            raise serializers.ValidationError('Staff roles cannot be changed.')
        if self.instance and attrs.get('email', self.instance.email).strip().lower() != self.instance.email:
            raise serializers.ValidationError('An existing sign-in email cannot be changed.')
        return attrs

    def validate_email(self, value):
        value = value.strip().lower()
        qs = User.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('This email already has access.')
        return value
