# authentication/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from employee.models import Employee
from django.utils import timezone
from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError

User = get_user_model()

class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)  # Kept: needed to set password
    full_name = serializers.CharField()
    gender = serializers.ChoiceField(choices=Employee.GENDER_CHOICES, required=False)
    dob = serializers.DateField(required=False)
    phone = serializers.CharField(required=True)
    address = serializers.CharField(required=False)
    position = serializers.CharField(required=False)
    role = serializers.ChoiceField(
        choices=Employee.ROLE_CHOICES,
        default=Employee.EMPLOYEE
    )

    def validate(self, data):
        # Optional: Add password strength validation
        if len(data['password']) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")

        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already in use.")

        return data

    
    def create(self, validated_data):
        full_name = validated_data.pop('full_name').strip()
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        role = validated_data.pop('role', Employee.EMPLOYEE)

        with transaction.atomic():  # atomic block ensures rollback if anything fails
            try:
                # Create user
                user = User.objects.create_user(
                    username=validated_data['email'],
                    email=validated_data['email'],
                    password=validated_data['password'],
                    first_name=first_name,
                    last_name=last_name
                )

                # Create Employee
                employee = Employee.objects.create(
                    user=user,
                    role=role,
                    gender=validated_data.get('gender'),
                    dob=validated_data.get('dob'),
                    phone=validated_data.get('phone'),
                    address=validated_data.get('address', ''),
                    department=None,
                    position=validated_data.get('position', ''),
                    date_of_joining=timezone.now(),
                    # employee_status=None
                )

            except IntegrityError as e:
                # Rollback happens automatically
                if "employee_employee_phone_e5a81acb_uniq" in str(e):
                    raise ValidationError({"phone": ["This phone number is already registered."]})
                if "auth_user_email_key" in str(e):
                    raise ValidationError({"email": ["This email is already registered."]})
                raise e

        return employee
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)