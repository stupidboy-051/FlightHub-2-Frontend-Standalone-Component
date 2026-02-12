import time
from typing import Optional

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import NotSupportedError
from django.utils import timezone as django_timezone

from telemetry_app.models import InspectImage
from telemetry_app.views import normalize_detect_code, process_single_image, safe_save


def _claim_next_pending_image(task_id: Optional[int] = None) -> Optional[InspectImage]:
    qs = (
        InspectImage.objects.select_related("inspect_task", "inspect_task__detect_category")
        .filter(detect_status="pending")
        .order_by("created_at", "id")
    )
    if task_id is not None:
        qs = qs.filter(inspect_task_id=task_id)

    with transaction.atomic():
        try:
            img = qs.select_for_update(skip_locked=True).first()
        except NotSupportedError:
            img = qs.select_for_update().first()

        if not img:
            return None

        updated = (
            InspectImage.objects.filter(id=img.id, detect_status="pending")
            .update(detect_status="processing")
        )
        if updated != 1:
            return None

        img.detect_status = "processing"
        return img


class Command(BaseCommand):
    help = "串行消费 pending 图片并调用算法检测（一次只处理一张）"

    def add_arguments(self, parser):
        parser.add_argument("--task-id", type=int, default=None, help="只处理指定任务ID")
        parser.add_argument("--idle-sleep", type=float, default=None, help="无任务时休眠秒数")
        parser.add_argument("--once", action="store_true", help="处理一张图片后退出")

    def handle(self, *args, **options):
        task_id = options.get("task_id")
        idle_sleep = options.get("idle_sleep")
        once = bool(options.get("once"))

        if idle_sleep is None:
            idle_sleep = float(getattr(settings, "DETECT_WORKER_IDLE_SLEEP", 2))

        if getattr(settings, "ENABLE_AUTO_TRIGGER_DETECT", True):
            self.stdout.write(
                self.style.WARNING(
                    "检测Worker已启动，但 ENABLE_AUTO_TRIGGER_DETECT=True。若同时开启自动分发，可能重复触发检测。"
                )
            )

        detect_url = getattr(settings, "FASTAPI_DETECT_URL", "http://localhost:8088/detect")

        self.stdout.write(self.style.SUCCESS("Detect Worker 启动：串行检测模式（一次只处理一张）"))

        while True:
            img = _claim_next_pending_image(task_id=task_id)
            if not img:
                if once:
                    return
                time.sleep(idle_sleep)
                continue

            task = img.inspect_task
            if task and not task.started_at:
                task.started_at = django_timezone.now()
                safe_save(task, update_fields=["started_at"])

            algo_type = (
                normalize_detect_code(task.detect_category.code)
                if task and task.detect_category
                else "rail"
            )

            process_single_image(img, task, detect_url, algo_type)

            if once:
                return
