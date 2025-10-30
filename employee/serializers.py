from django.contrib.auth import get_user_model
from django.db import transaction,  IntegrityError
from rest_framework import serializers
from .models import *
from rest_framework.validators import UniqueValidator
from rest_framework.exceptions import ValidationError

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    full_name = serializers.CharField(read_only = True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "full_name", "email", "password"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Compute full name dynamically
        data["full_name"] = instance.get_full_name()
        return data

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            password=validated_data["password"],
        )


# class EmployeeStatusSerializer(serializers.ModelSerializer):
#     is_active = serializers.BooleanField(required=False, default=False)

#     class Meta:
#         model = EmployeeStatus
#         fields = "__all__"


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
    def validate_phone(self, value):
        if not isinstance(value, int):
            raise serializers.ValidationError("Phone must be a number, not a string")
        if not 9600000000 <= value <= 9899999999:
            raise serializers.ValidationError("Phone must be a valid 10-digit Nepali number")
        return value
    class Meta:
        model = Employee
        fields = "__all__"
        ready_only_fileds = ["status"]
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

class EmployeeAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fieds = "__all__"
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
    # Update all relevant fields
        for field in ['name', 'description', 'department_code', 'is_active', 'hr']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
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
        read_only_fields = ["leave_reason"]  # user cannot modify this directly

    def validate(self, data):
        today = timezone.now().date()
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and start_date < today:
            raise serializers.ValidationError({"start_date": "Start date cannot be in the past."})

        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})
        return data

class WorkinghourSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHour
        fields = "__all__"
        read_only_fields = ["day_of_week"]

class EmployeeScheduleSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField(read_only = True)
    class Meta:
        model = EmployeeSchedule
        fields = ['id', 'employee', 'employee_name', 'availability']
        read_only_fields = ['id', 'employee_name']
    def get_employee_name(self, obj):
        if obj.employee and obj.employee.user:
            return f"{obj.employee.user.first_name} {obj.employee.user.last_name}"
        return None
