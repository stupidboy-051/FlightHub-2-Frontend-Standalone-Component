from datetime import timedelta

from django.utils import timezone

from .models import Alarm, AlarmDashboardStats


DETECT_TYPE_LABELS = [
    ("rail", "铁路"),
    ("contactline", "接触网"),
    ("bridge", "桥梁"),
    ("protected_area", "保护区"),
]

DETECT_TYPE_ALIASES = {
    "rail": ["rail", "railway", "rail_line", "rail-line", "railway_line", "track"],
    "contactline": [
        "contactline",
        "contact_line",
        "contact-line",
        "catenary",
        "catenary_line",
        "contactwire",
        "insulator",
        "pole",
        "overhead",
    ],
    "bridge": ["bridge", "bridge_line", "bridge-line"],
    "protected_area": [
        "protected_area",
        "protected-area",
        "protectedarea",
        "protected",
        "protected-zone",
        "protectedzone",
        "protection_zone",
        "protection_area",
    ],
}

SERIES_COLORS = [
    "#20A4F3",
    "#FF6B6B",
    "#7C3AED",
    "#16A34A",
    "#F59E0B",
    "#0EA5E9",
    "#EF4444",
    "#14B8A6",
    "#8B5CF6",
    "#F97316",
    "#22C55E",
    "#C026D3",
]

HANDLED_STATUSES = {
    "COMPLETED",
    "DONE",
    "FINISHED",
    "RESOLVED",
    "CLOSED",
    "PROCESSED",
    "HANDLED",
}


def _normalize_text(value):
    return str(value or "").strip().lower()


def _detect_type_from_text(text):
    raw = _normalize_text(text)
    if not raw:
        return None
    if raw in dict(DETECT_TYPE_LABELS):
        return raw
    for key, aliases in DETECT_TYPE_ALIASES.items():
        if raw in aliases:
            return key
    compact = raw.replace(" ", "")
    if "铁路" in compact:
        return "rail"
    if "接触网" in compact or "接触线" in compact:
        return "contactline"
    if "桥梁" in compact:
        return "bridge"
    if "保护区" in compact or "防护区" in compact:
        return "protected_area"
    return None


def _resolve_category_detect_type(category):
    current = category
    while current:
        key = _detect_type_from_text(getattr(current, "code", None))
        if key:
            return key
        key = _detect_type_from_text(getattr(current, "name", None))
        if key:
            return key
        current = getattr(current, "parent", None)
    return None


def _resolve_alarm_detect_type(alarm):
    if alarm is None:
        return None
    if getattr(alarm, "category", None):
        key = _resolve_category_detect_type(alarm.category)
        if key:
            return key
    if getattr(alarm, "wayline", None) and getattr(alarm.wayline, "detect_type", None):
        key = _detect_type_from_text(alarm.wayline.detect_type)
        if key:
            return key
    return None


def _is_handled_alarm(alarm):
    for attr in ["handled", "is_processed", "processed", "is_handled", "isHandled"]:
        val = getattr(alarm, attr, None)
        if val is True or val == 1 or val == "1":
            return True
    status = _normalize_text(getattr(alarm, "status", None)).upper()
    return status in HANDLED_STATUSES


def _start_of_day(dt):
    local = timezone.localtime(dt)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def _end_of_day(dt):
    local = timezone.localtime(dt)
    return local.replace(hour=23, minute=59, second=59, microsecond=999999)


def resolve_window(range_days, now=None):
    days = int(range_days) if range_days else 30
    days = max(days, 1)
    now = now or timezone.now()
    end = _end_of_day(now)
    start = _start_of_day(now - timedelta(days=days - 1))
    return start, end


def build_detect_type_series(alarms):
    counts = {key: 0 for key, _ in DETECT_TYPE_LABELS}
    for alarm in alarms:
        key = _resolve_alarm_detect_type(alarm)
        if not key or key not in counts:
            continue
        counts[key] += 1
    series = []
    for idx, (key, name) in enumerate(DETECT_TYPE_LABELS):
        series.append(
            {
                "id": key,
                "name": name,
                "value": counts.get(key, 0),
                "color": SERIES_COLORS[idx % len(SERIES_COLORS)],
            }
        )
    total = sum(counts.values())
    return total, series


def build_handle_rate_series(alarms):
    totals = {key: 0 for key, _ in DETECT_TYPE_LABELS}
    handled = {key: 0 for key, _ in DETECT_TYPE_LABELS}
    for alarm in alarms:
        key = _resolve_alarm_detect_type(alarm)
        if not key or key not in totals:
            continue
        totals[key] += 1
        if _is_handled_alarm(alarm):
            handled[key] += 1
    series = []
    for idx, (key, name) in enumerate(DETECT_TYPE_LABELS):
        total = totals.get(key, 0)
        done = handled.get(key, 0)
        series.append(
            {
                "id": key,
                "name": name,
                "total": total,
                "handled": done,
                "rate": int(round((done / total) * 100)) if total else 0,
                "color": SERIES_COLORS[idx % len(SERIES_COLORS)],
            }
        )
    total = sum(totals.values())
    return total, series


def compute_alarm_dashboard_stats(range_days, metric, now=None):
    start, end = resolve_window(range_days, now=now)
    alarms = (
        Alarm.objects.filter(created_at__range=(start, end))
        .select_related("category", "category__parent", "wayline")
        .order_by("id")
    )
    if metric == "handle_rate":
        total, series = build_handle_rate_series(alarms.iterator())
    else:
        total, series = build_detect_type_series(alarms.iterator())
    return {
        "metric": metric,
        "range_days": int(range_days),
        "total": total,
        "series": series,
        "window_start": start,
        "window_end": end,
    }


def upsert_alarm_dashboard_stats(range_days, metric, now=None):
    payload = compute_alarm_dashboard_stats(range_days, metric, now=now)
    obj, _ = AlarmDashboardStats.objects.update_or_create(
        metric=payload["metric"],
        range_days=payload["range_days"],
        defaults={
            "total": payload["total"],
            "series": payload["series"],
            "window_start": payload["window_start"],
            "window_end": payload["window_end"],
        },
    )
    return obj


def refresh_alarm_dashboard_stats(range_days_list=None, metrics=None, now=None):
    days_list = range_days_list or [30, 90, 365]
    metric_list = metrics or ["detect_type", "handle_rate"]
    results = []
    for days in days_list:
        for metric in metric_list:
            results.append(upsert_alarm_dashboard_stats(days, metric, now=now))
    return results
