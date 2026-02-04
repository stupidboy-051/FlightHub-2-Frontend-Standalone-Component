# telemetry_app/filters.py
import django_filters
from django.db.models import Q
from .models import Alarm, AlarmCategory, WaylineImage


class AlarmFilter(django_filters.FilterSet):
    """告警信息过滤器"""

    category_name = django_filters.CharFilter(
        field_name='category__name',
        lookup_expr='icontains'
    )
    category_code = django_filters.CharFilter(
        field_name='category__code',
        lookup_expr='exact'
    )
    start_date = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    end_date = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    status = django_filters.ChoiceFilter(choices=Alarm.STATUS_CHOICES)
    wayline_id = django_filters.CharFilter(field_name='wayline__wayline_id', lookup_expr='icontains')
    wayline_name = django_filters.CharFilter(field_name='wayline__name', lookup_expr='icontains')
    wayline = django_filters.NumberFilter(field_name='wayline', lookup_expr='exact')
    # 🔥 新增：按巡检任务过滤（通过 source_image 关联）
    source_task = django_filters.NumberFilter(
        field_name='source_image__inspect_task',
        lookup_expr='exact'
    )
    task_uuid = django_filters.CharFilter(
        field_name='image_url',
        lookup_expr='icontains'
    )
    # 🔥 新增：按检测类型过滤（通过 wayline 的 detect_type 或 category 的 code）
    detect_type = django_filters.CharFilter(method='filter_detect_type')

    def filter_detect_type(self, queryset, name, value):
        if not value:
            return queryset
            
        value = value.lower()
        variants_map = {
            "rail": {"rail", "track"},
            "contactline": {"contactline", "catenary", "overhead", "insulator", "pole"},
            "bridge": {"bridge"},
            "protected_area": {"protected_area", "protection_zone", "protection_area"},
        }
        
        variants = set()
        for k, v in variants_map.items():
            if value in v or value == k:
                variants.update(v)
                variants.add(k)
        
        if not variants:
            variants = {value}
            
        q = Q()
        for v in variants:
            q |= Q(wayline__detect_type__iexact=v)
            q |= Q(category__code__iexact=v)
            
        return queryset.filter(q)

    class Meta:
        model = Alarm
        fields = [
            'status', 'handler', 'category', 'wayline', 'wayline_id', 'wayline_name',
            'start_date', 'end_date', 'category_name', 'category_code', 'source_task',
            'task_uuid', 'detect_type'
        ]


class WaylineImageFilter(django_filters.FilterSet):
    """航线图片过滤器"""

    wayline = django_filters.NumberFilter(field_name='wayline', lookup_expr='exact')
    wayline_id = django_filters.CharFilter(field_name='wayline__wayline_id', lookup_expr='exact')

    class Meta:
        model = WaylineImage
        fields = ['wayline', 'wayline_id']
