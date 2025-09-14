from django.contrib.auth import get_user_model
from django.db import transaction,  IntegrityError
from rest_framework import serializers
from .models import *
from rest_framework.validators import UniqueValidator
from rest_framework.exceptions import ValidationError

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    full_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "full_name", "email", "password"]

    def create(self, validated_data):
        # Handle full_name → split into first_name, last_name
        full_name = validated_data.pop("full_name", None)
        if full_name and not (validated_data.get("first_name") and validated_data.get("last_name")):
            parts = full_name.strip().split(" ", 1)
            validated_data["first_name"] = parts[0]
            validated_data["last_name"] = parts[1] if len(parts) > 1 else ""

        return User.objects.create_user(
            username=validated_data["email"],  # email as username
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            password=validated_data["password"],
        )


class EmployeeStatusSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = EmployeeStatus
        fields = "__all__"


class EmployeeNestedMinimalSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ["id", "user"]

    def get_user(self, obj):
        return {
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
            "email": obj.user.email,
        }
class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
    
    phone = serializers.CharField(
        required=True,
        validators=[UniqueValidator(
            queryset=Employee.objects.all(),
            message="This phone number is already registered."
        )]
    )

    class Meta:
        model = Employee
        fields = "__all__"
        extra_kwargs = {
            "dob": {"required": True},
            "gender": {"required": True},
            "address": {"required": True},
        }

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop("user")

        # Check if user email already exists
        if User.objects.filter(email=user_data["email"]).exists():
            raise ValidationError({"email": ["This email is already registered."]})

        # Create user
        user = UserSerializer().create(user_data)

        # Create employee
        try:
            employee = Employee.objects.create(user=user, **validated_data)
        except IntegrityError as e:
            if "employee_employee_phone_e5a81acb_uniq" in str(e):
                raise ValidationError({"phone": ["This phone number is already registered."]})
            raise e
        return employee

    def validate(self, data):
        user_data = data.get("user", {})
        first_name = user_data.get("first_name")
        last_name = user_data.get("last_name")
        department = data.get("department")

        # Validate unique full name per department
        if first_name and last_name and department:
            qs = Employee.objects.filter(
                user__first_name__iexact=first_name,
                user__last_name__iexact=last_name,
                department=department,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "This name already exists in this department."}
                )

        return data

    # @transaction.atomic
    # def create(self, validated_data):
    #     user_data = validated_data.pop("user")
    #     user = UserSerializer().create(user_data)
        
    #     try:
    #         employee = Employee.objects.create(user=user, **validated_data)
    #     except IntegrityError as e:
    #         if "employee_employee_phone_e5a81acb_uniq" in str(e):
    #             raise ValidationError({"phone": ["This phone number is already registered."]})
    #         raise e  # re-raise other IntegrityErrors
    #     return employee

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
class DepartmentSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Department
        fields = "__all__"

    def create(self, validated_data: dict) -> Department:
        hr = validated_data.pop("hr", None)
        department = Department.objects.create(**validated_data)
        if hr:
            department.hr = hr
            department.save()
        return department

    def update(self, instance, validated_data: dict):
        instance.name = validated_data.get("name", instance.name)
        if "hr" in validated_data:
            instance.hr = validated_data.get("hr")
        instance.save()
        return instance


class DepartmentNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["name", "description"]


class EmployeeProfileSerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())

    class Meta:
        model = EmployeeProfile
        fields = [
            "employee",
            "profile_photo",
            "citizenship",
            "contact_agreement",
        ]

class LeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leave
        fields = "__all__"
        read_only_fields = ["leave_reason"]

class WorkinghourSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHour
        fields = "__all__"
        read_only_fields = ["day_of_week"]

class EmployeeScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSchedule
        fields = "__all__"
        read_only_fields = ['availability']
        