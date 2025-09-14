import django_filters
from .models import Employee
import django_filters
from django.db.models import Q
from .models import Employee
class EmployeeFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(method='filter_by_name')

    class Meta:
        model = Employee
        fields = ['employee_code', 'department', 'username', 'name']

    def filter_by_name(self, queryset, name, value):
        return queryset.filter(
            Q(user__first_name__icontains=value) | Q(user__last_name__icontains=value)
        )
    class Meta: 
        model=Employee 
        fields=[]