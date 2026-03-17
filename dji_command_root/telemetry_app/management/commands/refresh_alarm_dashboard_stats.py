from django.core.management.base import BaseCommand

from telemetry_app.alarm_dashboard_stats import refresh_alarm_dashboard_stats


class Command(BaseCommand):
    help = "刷新首页告警统计与巡检故障处理率缓存"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            nargs="*",
            type=int,
            default=[30, 90, 365],
            help="统计范围(天)，默认: 30 90 365",
        )
        parser.add_argument(
            "--metric",
            choices=["detect_type", "handle_rate", "all"],
            default="all",
            help="统计类型：detect_type | handle_rate | all",
        )

    def handle(self, *args, **options):
        days_list = options.get("days") or [30, 90, 365]
        metric = options.get("metric") or "all"
        metrics = ["detect_type", "handle_rate"] if metric == "all" else [metric]

        self.stdout.write(
            self.style.NOTICE(
                f"开始刷新告警看板统计缓存: days={days_list}, metrics={metrics}"
            )
        )
        results = refresh_alarm_dashboard_stats(days_list, metrics)
        self.stdout.write(
            self.style.SUCCESS(f"完成刷新，共更新 {len(results)} 条记录")
        )
