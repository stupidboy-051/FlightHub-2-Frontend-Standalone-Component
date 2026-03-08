from django.core.management.base import BaseCommand

from telemetry_app.alarm_dashboard_cache import refresh_alarm_dashboard_cache


class Command(BaseCommand):
    help = "刷新告警大屏聚合缓存（30/90/365 天）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            nargs="*",
            type=int,
            default=[30, 90, 365],
            help="统计范围（天），默认: 30 90 365",
        )

    def handle(self, *args, **options):
        days_list = options.get("days") or [30, 90, 365]
        self.stdout.write(self.style.NOTICE(f"开始刷新告警大屏缓存: days={days_list}"))
        results = refresh_alarm_dashboard_cache(days_list)
        self.stdout.write(self.style.SUCCESS(f"刷新完成，共更新 {len(results)} 条缓存记录"))
