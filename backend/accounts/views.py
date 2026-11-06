from django.db import transaction, IntegrityError
from rest_framework import generics, serializers, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenRefreshView
from core.api import AuthThrottle
from core.access import IsStaffRole, IsManager, visible_students
from core.models import audit
from .models import User
from .serializers import UserSerializer, InviteSerializer, StudentUpdateSerializer, AccessRefreshSerializer


class AccessRefreshView(TokenRefreshView):
    serializer_class = AccessRefreshSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        from .serializers import EmailLoginSerializer
        data = EmailLoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = User.objects.filter(email=data.validated_data['email'].strip().lower(), is_active=True).first()
        if not user:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('This email does not have active access. Contact your trainer or sales team.')
        refresh = RefreshToken.for_user(user)
        audit(user, 'account.email_login', user)
        return Response({'access': str(refresh.access_token), 'refresh': str(refresh),
                         'user': UserSerializer(user).data}, headers={'Cache-Control': 'no-store'})


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


class StudentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffRole]
    serializer_class = StudentUpdateSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        from django.db.models import Q
        q = self.request.query_params.get('search', '')
        return visible_students(self.request.user).filter(Q(name__icontains=q) | Q(email__icontains=q)).order_by('name', 'id')

    @transaction.atomic
    def create(self, request):
        data = InviteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            student = User.objects.create_user(**data.validated_data, role='student',
                trainer=request.user if request.user.role == 'trainer' else None)
        except IntegrityError:
            raise serializers.ValidationError({'email': 'This email already has an account.'})
        audit(request.user, 'student.access_granted', student)
        return Response({'student': self.get_serializer(student).data,
                         'detail': 'Access granted. Sign in with this email only. No email was sent.'}, status=201)

    def perform_update(self, serializer):
        student = serializer.save()
        if not student.is_active:
            student.set_unusable_password()  # Revoke existing JWT sessions as well.
            student.save(update_fields=['password'])
        audit(self.request.user, 'student.updated', student)


class StaffViewSet(viewsets.ModelViewSet):
    permission_classes = [IsManager]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_serializer_class(self):
        from .serializers import StaffSerializer
        return StaffSerializer

    def get_queryset(self):
        roles = ['trainer', 'sales', 'admin'] if self.request.user.role == 'admin' else ['trainer']
        return User.objects.filter(role__in=roles).order_by('name', 'id')

    def perform_create(self, serializer):
        user = serializer.save()
        user.set_unusable_password()
        user.save(update_fields=['password'])
        audit(self.request.user, 'staff.access_granted', user)

    def perform_update(self, serializer):
        user = serializer.save()
        if not user.is_active:
            user.set_unusable_password()
            user.save(update_fields=['password'])
        audit(self.request.user, 'staff.updated', user)
