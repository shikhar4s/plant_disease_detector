from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from plant_doctor_ai.images import read_image, preview_data_uri
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, max_length=128)
    confirm_password = serializers.CharField(write_only=True, max_length=128)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'password', 'confirm_password']

    def validate_email(self, email):
        email = email.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return email

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        try:
            password_validation.validate_password(attrs['password'],
                User(email=attrs['email'], full_name=attrs['full_name']))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True)

    def validate(self, data):
        email = data['email'].strip()
        existing = User.objects.filter(email__iexact=email).only('email').first()
        user = authenticate(email=existing.email if existing else email.lower(), password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        data['user'] = user
        return data


class ProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='full_name', read_only=True)
    photo_url = serializers.CharField(source='photo_preview', read_only=True)
    photo = serializers.FileField(write_only=True, required=False)
    saved_analyses = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'full_name', 'date_joined', 'photo_url', 'photo',
                  'total_uploads', 'total_analyzed', 'saved_analyses']
        read_only_fields = ['id', 'email', 'date_joined', 'total_uploads', 'total_analyzed']

    def get_saved_analyses(self, obj):
        return obj.analyses.count()

    def validate_photo(self, photo):
        return preview_data_uri(read_image(photo, max_bytes=3 * 1024 * 1024), size=256)

    def update(self, instance, validated_data):
        photo = validated_data.pop('photo', None)
        if photo is not None:
            instance.photo_preview = photo
        return super().update(instance, validated_data)
