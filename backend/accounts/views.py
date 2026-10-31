import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import generics, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from core.api import IsTrainer, AuthThrottle, ServiceUnavailable
from core.models import audit
from .models import User, Invitation
from .serializers import (UserSerializer, LoginSerializer, InviteSerializer, AcceptInvitationSerializer,
                          StudentUpdateSerializer, ResetSerializer, ConfirmResetSerializer, ChangePasswordSerializer)


def check_password(password, user):
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({'password': exc.messages})


def email_link(subject, body, email):
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email])
    except Exception:
        raise ServiceUnavailable('Email delivery failed. Check SMTP configuration and retry.')


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [AuthThrottle]


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh', ''))
            if str(token['user_id']) != str(request.user.pk):
                raise serializers.ValidationError('Invalid refresh token.')
            token.blacklist()
        except TokenError:
            raise serializers.ValidationError('Invalid refresh token.')
        return Response(status=204)


class StudentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsTrainer]
    serializer_class = StudentUpdateSerializer

    def create(self, request):
        data = InviteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        email = data.validated_data['email']
        password = secrets.token_urlsafe(18)
        try:
            with transaction.atomic():
                invitation = Invitation.objects.select_for_update().filter(email=email).first()
                if User.objects.filter(email=email).exists() or (invitation and invitation.trainer_id != request.user.id):
                    raise serializers.ValidationError({'email': 'This email already has an account or access request.'})
                student = User.objects.create_user(email, password, name=data.validated_data['name'],
                                                   trainer=request.user, role='student', is_active=True)
                if invitation:
                    invitation.delete()  # An old invitation must not activate a second account.
                audit(request.user, 'student.access_granted', student)
        except IntegrityError:
            raise serializers.ValidationError({'email': 'This email already has an account.'})
        return Response({'student': self.get_serializer(student).data, 'initial_password': password,
                         'detail': 'Access granted. No email was sent. Share the sign-in details directly.'},
                        status=201, headers={'Cache-Control': 'no-store'})

    @action(detail=True, methods=['post'], url_path='reset-access')
    def reset_access(self, request, pk=None):
        student = self.get_object()
        password = secrets.token_urlsafe(18)
        student.set_password(password)
        student.save(update_fields=['password', 'updated_at'])
        audit(request.user, 'student.password_reset_by_trainer', student)
        return Response({'student': self.get_serializer(student).data, 'initial_password': password,
                         'detail': 'Password reset. No email was sent.'}, headers={'Cache-Control': 'no-store'})

    def get_queryset(self):
        qs = User.objects.filter(trainer=self.request.user, role='student').order_by('name', 'id')
        q = self.request.query_params.get('search', '')
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q))
        return qs

    def partial_update(self, request, pk=None):
        student = self.get_object()
        serializer = self.get_serializer(student, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request.user, 'student.updated', student, active=student.is_active)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def invitations(self, request):
        records = Invitation.objects.filter(trainer=request.user, accepted_at=None).order_by('-created_at')
        return Response(list(records.values('id', 'name', 'email', 'expires_at')))

    @action(detail=False, methods=['post'])
    def invite(self, request):
        data = InviteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        email = data.validated_data['email']
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'An account already exists with this email.'})
        token = secrets.token_urlsafe(48)
        with transaction.atomic():
            invitation = Invitation.objects.filter(email=email).first()
            if invitation and invitation.trainer_id != request.user.id:
                raise serializers.ValidationError({'email': 'An invitation already exists.'})
            invitation, _ = Invitation.objects.update_or_create(email=email, defaults={
                'trainer': request.user, 'name': data.validated_data['name'],
                'token_hash': hashlib.sha256(token.encode()).hexdigest(),
                'expires_at': timezone.now() + timedelta(days=3), 'accepted_at': None})
            email_link('Your SkillForge AI invitation',
                       f'Join your classroom: {settings.FRONTEND_URL}/accept-invitation?token={token}\nThis link expires in 3 days.', email)
            audit(request.user, 'invitation.sent', invitation)
        return Response({'detail': 'Invitation sent.', 'email': email}, status=201)


class AcceptInvitationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        data = AcceptInvitationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            token_hash = hashlib.sha256(data.validated_data['token'].encode()).hexdigest()
            invitation = Invitation.objects.select_for_update().filter(token_hash=token_hash, accepted_at=None, expires_at__gt=timezone.now()).first()
            if not invitation or not invitation.trainer.is_active:
                raise serializers.ValidationError('This invitation is invalid or expired.')
            user = User(email=invitation.email, name=invitation.name, trainer=invitation.trainer)
            check_password(data.validated_data['password'], user)
            user.set_password(data.validated_data['password'])
            try:
                user.save()
            except IntegrityError:
                raise serializers.ValidationError('This invitation has already been accepted.')
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=['accepted_at'])
            audit(user, 'invitation.accepted', invitation)
        return Response({'detail': 'Account activated. You can now sign in.'}, status=201)


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        data = ResetSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = User.objects.filter(email=data.validated_data['email'].strip().lower(), is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            email_link('Reset your SkillForge AI password', f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}', user.email)
        return Response({'detail': 'If this account exists, a reset link has been sent.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        data = ConfirmResetSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(data.validated_data['uid'])), is_active=True)
        except (ValueError, TypeError, OverflowError, UnicodeError, User.DoesNotExist):
            raise serializers.ValidationError('Invalid reset link.')
        if not default_token_generator.check_token(user, data.validated_data['token']):
            raise serializers.ValidationError('Invalid or expired reset link.')
        check_password(data.validated_data['password'], user)
        user.set_password(data.validated_data['password'])
        user.save(update_fields=['password'])
        audit(user, 'password.reset', user)
        return Response({'detail': 'Password updated.'})


class ChangePasswordView(APIView):
    throttle_classes = [AuthThrottle]

    def post(self, request):
        data = ChangePasswordSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(data.validated_data['current_password']):
            raise serializers.ValidationError({'current_password': 'The current password is incorrect.'})
        password = data.validated_data['password']
        check_password(password, user)
        if password == data.validated_data['current_password']:
            raise serializers.ValidationError({'password': 'Choose a different password.'})
        user.set_password(password)
        user.save(update_fields=['password', 'updated_at'])
        audit(user, 'password.changed', user)
        return Response({'detail': 'Password updated. Sign in again with your new password.'})
