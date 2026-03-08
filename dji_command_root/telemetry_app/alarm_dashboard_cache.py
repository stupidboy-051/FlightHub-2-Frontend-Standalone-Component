from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import datetime, timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from .alarm_dashboard_stats import _is_handled_alarm, _resolve_alarm_detect_type
from .models import Alarm, AlarmDashboardCache, DockStatus, FlightTaskInfo, Wayline


DEFAULT_RANGE_DAYS = [30, 90, 365]

TREND_TYPE_ORDER = ["rail", "contactline", "bridge", "protected_area"]
TYPE_NAME_MAP = {
    "rail": "铁路",
    "contactline": "接触网",
    "bridge": "桥梁",
    "protected_area": "保护区",
}
TYPE_COLOR_MAP = {
    "rail": "#22d3ee",
    "contactline": "#f59e0b",
    "bridge": "#a78bfa",
    "protected_area": "#34d399",
}
SERIES_COLORS = [
    "#22d3ee",
    "#f97316",
    "#a78bfa",
    "#34d399",
    "#f43f5e",
    "#60a5fa",
    "#f59e0b",
    "#4ade80",
]

SAFETY_BASELINE = datetime(2026, 2, 1, 0, 0, 0)


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value, default=0.0):
    try:
        numeric = float(value)
        if numeric != numeric:  # NaN
            return default
        return numeric
    except (TypeError, ValueError):
        return default


def _safe_iso(dt):
    if not dt:
        return None
    return timezone.localtime(dt).isoformat()


def _start_of_day(dt):
    local = timezone.localtime(dt)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def _end_of_day(dt):
    local = timezone.localtime(dt)
    return local.replace(hour=23, minute=59, second=59, microsecond=999999)


def resolve_range_window(range_days, now=None):
    days = max(_to_int(range_days, 30), 1)
    now = now or timezone.now()
    end = _end_of_day(now)
    start = _start_of_day(now - timedelta(days=days - 1))
    return start, end


def _build_detect_type_stats(alarms):
    counts = {key: 0 for key in TREND_TYPE_ORDER}
    for alarm in alarms:
        key = _resolve_alarm_detect_type(alarm)
        if key in counts:
            counts[key] += 1

    series = []
    for idx, key in enumerate(TREND_TYPE_ORDER):
        series.append(
            {
                "id": key,
                "name": TYPE_NAME_MAP.get(key, key),
                "value": counts.get(key, 0),
                "color": TYPE_COLOR_MAP.get(key, SERIES_COLORS[idx % len(SERIES_COLORS)]),
            }
        )

    return {
        "total": sum(counts.values()),
        "series": series,
    }


def _build_handle_rate_stats(alarms):
    totals = {key: 0 for key in TREND_TYPE_ORDER}
    handled = {key: 0 for key in TREND_TYPE_ORDER}

    for alarm in alarms:
        key = _resolve_alarm_detect_type(alarm)
        if key not in totals:
            continue
        totals[key] += 1
        if _is_handled_alarm(alarm):
            handled[key] += 1

    series = []
    for idx, key in enumerate(TREND_TYPE_ORDER):
        total = totals.get(key, 0)
        done = handled.get(key, 0)
        rate = round((done / total) * 100, 1) if total > 0 else 0.0
        series.append(
            {
                "id": key,
                "name": TYPE_NAME_MAP.get(key, key),
                "total": total,
                "handled": done,
                "rate": rate,
                "color": TYPE_COLOR_MAP.get(key, SERIES_COLORS[idx % len(SERIES_COLORS)]),
            }
        )

    return {
        "total": sum(totals.values()),
        "series": series,
    }


def _build_hourly_distribution(alarms):
    bins = [
        {
            "hour": hour,
            "label": f"{hour:02d}:00 - {hour:02d}:59",
            "shortLabel": f"{hour:02d}",
            "value": 0,
            "height": 0.0,
        }
        for hour in range(24)
    ]

    for alarm in alarms:
        if not alarm.created_at:
            continue
        hour = timezone.localtime(alarm.created_at).hour
        if 0 <= hour < 24:
            bins[hour]["value"] += 1

    max_val = max((item["value"] for item in bins), default=0)
    max_val = max(max_val, 1)
    for item in bins:
        item["height"] = round((item["value"] / max_val) * 100, 4)
    return bins


def _build_handle_duration_by_type(alarms):
    stats = defaultdict(lambda: {"sum": 0.0, "count": 0})
    for alarm in alarms:
        if not _is_handled_alarm(alarm):
            continue
        if not alarm.created_at or not alarm.updated_at:
            continue

        diff_ms = (alarm.updated_at - alarm.created_at).total_seconds() * 1000
        if diff_ms < 0:
            continue
        hours = diff_ms / (1000 * 60 * 60)
        if hours > 720:
            continue

        key = _resolve_alarm_detect_type(alarm)
        if key not in TREND_TYPE_ORDER:
            continue

        stats[key]["sum"] += hours
        stats[key]["count"] += 1

    result = {}
    for key, value in stats.items():
        if value["count"] > 0:
            result[key] = round(value["sum"] / value["count"], 6)
    return result


def _build_wayline_stats(alarms, top_n=8):
    counter = defaultdict(int)
    name_map = {}

    for alarm in alarms:
        if alarm.wayline_id:
            key = str(alarm.wayline_id)
            name = (
                alarm.wayline.name
                if getattr(alarm, "wayline", None) and getattr(alarm.wayline, "name", None)
                else key
            )
        else:
            key = "__UNKNOWN__"
            name = "未知航线"
        counter[key] += 1
        if key not in name_map:
            name_map[key] = name

    all_series = sorted(
        [
            {"id": key, "name": name_map.get(key, key), "value": value}
            for key, value in counter.items()
        ],
        key=lambda item: (-item["value"], item["name"]),
    )

    top_n = max(_to_int(top_n, 8), 0)
    top = all_series[:top_n]
    rest = all_series[top_n:]
    rest_sum = sum(item["value"] for item in rest)

    series = []
    for idx, item in enumerate(top):
        series.append(
            {
                "id": item["id"],
                "name": item["name"],
                "value": item["value"],
                "color": SERIES_COLORS[idx % len(SERIES_COLORS)],
            }
        )

    if rest_sum > 0:
        series.append(
            {
                "id": "__OTHER__",
                "name": "其他",
                "value": rest_sum,
                "color": "#94a3b8",
            }
        )

    return {
        "total": sum(counter.values()),
        "series": series,
    }


def _build_wayline_id_maps():
    db_to_biz = {}
    biz_to_db = {}
    for row in Wayline.objects.values("id", "wayline_id"):
        db_key = str(row.get("id") or "").strip()
        biz_key = str(row.get("wayline_id") or "").strip()
        if db_key and biz_key:
            db_to_biz[db_key] = biz_key
            biz_to_db[biz_key] = db_key
    return db_to_biz, biz_to_db


def _expand_wayline_keys(raw_value, db_to_biz, biz_to_db):
    raw_key = str(raw_value or "").strip()
    if not raw_key:
        return set()
    keys = {raw_key}
    mapped_biz = db_to_biz.get(raw_key)
    mapped_db = biz_to_db.get(raw_key)
    if mapped_biz:
        keys.add(mapped_biz)
    if mapped_db:
        keys.add(mapped_db)
    return keys


def _resolve_alarm_wayline_keys(alarm, db_to_biz, biz_to_db):
    keys = set()
    if getattr(alarm, "wayline_id", None):
        keys.update(_expand_wayline_keys(alarm.wayline_id, db_to_biz, biz_to_db))
    if getattr(alarm, "wayline", None) and getattr(alarm.wayline, "wayline_id", None):
        keys.update(_expand_wayline_keys(alarm.wayline.wayline_id, db_to_biz, biz_to_db))
    return keys


def _build_airport_risk_rows(by_airport, task_queryset, dock_field, alarms):
    db_to_biz, biz_to_db = _build_wayline_id_maps()

    counter_by_wayline = defaultdict(lambda: defaultdict(int))
    task_rows = task_queryset.values(dock_field, "wayline_id")
    for row in task_rows:
        dock_sn = str(row.get(dock_field) or "").strip()
        if not dock_sn:
            continue
        keys = _expand_wayline_keys(row.get("wayline_id"), db_to_biz, biz_to_db)
        for key in keys:
            counter_by_wayline[key][dock_sn] += 1

    dock_by_wayline = {}
    for key, dock_counter in counter_by_wayline.items():
        best_dock = ""
        best_count = -1
        for dock_sn, count in dock_counter.items():
            if count > best_count:
                best_dock = dock_sn
                best_count = count
        if best_dock:
            dock_by_wayline[key] = best_dock

    alarm_count_by_dock = defaultdict(int)
    for alarm in alarms:
        dock_sn = ""
        for key in _resolve_alarm_wayline_keys(alarm, db_to_biz, biz_to_db):
            mapped = dock_by_wayline.get(key)
            if mapped:
                dock_sn = mapped
                break
        if dock_sn:
            alarm_count_by_dock[dock_sn] += 1

    rows = []
    for item in by_airport:
        dock_sn = str(item.get("dock_sn") or item.get("dockSn") or "").strip()
        distance_km = _to_float(item.get("distanceKm"), 0.0)
        alarm_count = int(alarm_count_by_dock.get(dock_sn, 0))
        risk_index = (alarm_count / distance_km) if distance_km > 0 else 0.0
        rows.append(
            {
                "dockSn": dock_sn,
                "dock_sn": dock_sn,
                "name": item.get("name") or dock_sn or "未知机场",
                "taskCount": _to_int(item.get("taskCount"), 0),
                "distanceKm": round(distance_km, 2),
                "durationHours": round(_to_float(item.get("durationHours"), 0.0), 2),
                "alarmCount": alarm_count,
                "riskIndex": round(risk_index, 6),
            }
        )

    max_risk = max((row["riskIndex"] for row in rows), default=0.0)
    if max_risk <= 0:
        max_risk = 1.0

    for row in rows:
        row["riskPct"] = round((row["riskIndex"] / max_risk) * 100, 4)

    rows.sort(key=lambda item: (-item["riskIndex"], item["name"]))
    return rows


def _build_flight_stats(range_start, range_end, alarms):
    queryset = FlightTaskInfo.objects.filter(created_at__range=(range_start, range_end))
    dock_field = (
        "dock_sn"
        if any(field.name == "dock_sn" for field in FlightTaskInfo._meta.fields)
        else "sn"
    )

    totals = queryset.aggregate(
        total_tasks=Count("id"),
        total_distance=Sum("flight_distance"),
        total_duration=Sum("flight_duration"),
    )

    grouped_rows = list(
        queryset.exclude(**{f"{dock_field}__isnull": True})
        .exclude(**{dock_field: ""})
        .values(dock_field)
        .annotate(
            task_count=Count("id"),
            total_distance=Sum("flight_distance"),
            total_duration=Sum("flight_duration"),
        )
        .order_by("-task_count", dock_field)
    )

    by_airport = []
    by_airport_map = {}
    for dock in DockStatus.objects.values("dock_sn", "dock_name"):
        dock_sn = str(dock.get("dock_sn") or "").strip()
        if not dock_sn or dock_sn in by_airport_map:
            continue
        entry = {
            "dockSn": dock_sn,
            "dock_sn": dock_sn,
            "name": dock.get("dock_name") or dock_sn,
            "taskCount": 0,
            "distanceKm": 0.0,
            "durationHours": 0.0,
        }
        by_airport_map[dock_sn] = entry
        by_airport.append(entry)

    for row in grouped_rows:
        dock_sn = str(row.get(dock_field) or "").strip()
        if not dock_sn:
            continue
        entry = by_airport_map.get(dock_sn)
        if not entry:
            entry = {
                "dockSn": dock_sn,
                "dock_sn": dock_sn,
                "name": dock_sn,
                "taskCount": 0,
                "distanceKm": 0.0,
                "durationHours": 0.0,
            }
            by_airport_map[dock_sn] = entry
            by_airport.append(entry)

        entry["taskCount"] = _to_int(row.get("task_count"), 0)
        entry["distanceKm"] = round(_to_float(row.get("total_distance"), 0.0), 2)
        entry["durationHours"] = round(_to_float(row.get("total_duration"), 0.0) / 3600.0, 2)

    by_airport.sort(key=lambda item: (-item["taskCount"], item["name"]))
    airport_risk_rows = _build_airport_risk_rows(by_airport, queryset, dock_field, alarms)

    flight_stats = {
        "totalTasks": _to_int(totals.get("total_tasks"), 0),
        "distanceKm": round(_to_float(totals.get("total_distance"), 0.0), 2),
        "durationHours": round(_to_float(totals.get("total_duration"), 0.0) / 3600.0, 2),
        "byAirport": by_airport,
    }
    return flight_stats, airport_risk_rows


def _build_trend_months(now):
    local_now = timezone.localtime(now)
    year = local_now.year
    month = local_now.month
    tz = timezone.get_current_timezone()

    result = []
    for offset in range(11, -1, -1):
        y = year
        m = month - offset
        while m <= 0:
            y -= 1
            m += 12
        while m > 12:
            y += 1
            m -= 12

        start = timezone.make_aware(datetime(y, m, 1, 0, 0, 0, 0), timezone=tz)
        last_day = monthrange(y, m)[1]
        end = timezone.make_aware(datetime(y, m, last_day, 23, 59, 59, 999999), timezone=tz)
        result.append(
            {
                "key": f"{y}-{m}",
                "label": f"{m}月",
                "fullLabel": f"{y}年{m}月",
                "start": start,
                "end": end,
            }
        )
    return result


def _serialize_alarm_detail(alarm):
    wayline_name = "未知航线"
    wayline_id = "__UNKNOWN__"
    if getattr(alarm, "wayline_id", None):
        wayline_id = str(alarm.wayline_id)
    if getattr(alarm, "wayline", None):
        wayline_name = alarm.wayline.name or wayline_name
        if getattr(alarm.wayline, "wayline_id", None):
            wayline_id = str(alarm.wayline.wayline_id)

    return {
        "id": alarm.id,
        "content": alarm.content or "",
        "status": alarm.status or "",
        "created_at": _safe_iso(alarm.created_at),
        "updated_at": _safe_iso(alarm.updated_at),
        "wayline_id": wayline_id,
        "wayline_name": wayline_name,
    }


def _build_line_chart(now, trend_alarms):
    months = _build_trend_months(now)
    month_index = {item["key"]: idx for idx, item in enumerate(months)}
    buckets = {key: [0] * len(months) for key in TREND_TYPE_ORDER}
    detail_map = {key: {} for key in TREND_TYPE_ORDER}

    for alarm in trend_alarms:
        if not alarm.created_at:
            continue
        local_dt = timezone.localtime(alarm.created_at)
        key = f"{local_dt.year}-{local_dt.month}"
        idx = month_index.get(key)
        if idx is None:
            continue

        type_key = _resolve_alarm_detect_type(alarm)
        if type_key not in buckets:
            continue

        buckets[type_key][idx] += 1
        detail_map[type_key].setdefault(key, []).append(_serialize_alarm_detail(alarm))

    series = []
    for idx, type_key in enumerate(TREND_TYPE_ORDER):
        series.append(
            {
                "id": type_key,
                "name": TYPE_NAME_MAP.get(type_key, type_key),
                "color": TYPE_COLOR_MAP.get(type_key, SERIES_COLORS[idx % len(SERIES_COLORS)]),
                "data": buckets[type_key],
            }
        )

    line_chart = {
        "categories": [item["label"] for item in months],
        "months": [
            {
                "key": item["key"],
                "label": item["label"],
                "fullLabel": item["fullLabel"],
            }
            for item in months
        ],
        "series": series,
    }
    return line_chart, detail_map, months


def _build_safety_stats(now):
    local_now = timezone.localtime(now)
    tz = timezone.get_current_timezone()
    baseline = timezone.make_aware(SAFETY_BASELINE, timezone=tz)

    today_start = _start_of_day(now)
    today_end = _end_of_day(now)
    rolling30_start = _start_of_day(now - timedelta(days=29))
    rolling30_end = _end_of_day(now)
    year_start = timezone.make_aware(datetime(local_now.year, 1, 1, 0, 0, 0, 0), timezone=tz)
    year_end = _end_of_day(now)

    latest_alarm_at = Alarm.objects.order_by("-created_at").values_list("created_at", flat=True).first()

    return {
        "safetyDays": max((local_now.date() - baseline.date()).days, 0),
        "todayAlarms": Alarm.objects.filter(created_at__range=(today_start, today_end)).count(),
        "monthAlarms": Alarm.objects.filter(created_at__range=(rolling30_start, rolling30_end)).count(),
        "yearAlarms": Alarm.objects.filter(created_at__range=(year_start, year_end)).count(),
        "latestAlarmAt": _safe_iso(latest_alarm_at),
    }


def compute_alarm_dashboard_cache(range_days, now=None):
    days = max(_to_int(range_days, 30), 1)
    now = now or timezone.now()

    range_start, range_end = resolve_range_window(days, now=now)

    range_alarms = list(
        Alarm.objects.filter(created_at__range=(range_start, range_end))
        .select_related("category", "category__parent", "wayline")
        .order_by("-created_at")
    )

    trend_months = _build_trend_months(now)
    trend_start = trend_months[0]["start"] if trend_months else range_start
    trend_end = _end_of_day(now)
    trend_alarms = list(
        Alarm.objects.filter(created_at__range=(trend_start, trend_end))
        .select_related("category", "category__parent", "wayline")
        .order_by("-created_at")
    )

    detect_type_stats = _build_detect_type_stats(range_alarms)
    handle_rate_stats = _build_handle_rate_stats(range_alarms)
    wayline_stats = _build_wayline_stats(range_alarms, top_n=8)
    hourly_distribution = _build_hourly_distribution(range_alarms)
    handle_duration_by_type = _build_handle_duration_by_type(range_alarms)
    flight_stats, airport_risk_rows = _build_flight_stats(range_start, range_end, range_alarms)
    line_chart, trend_detail_map, _ = _build_line_chart(now, trend_alarms)
    safety_stats = _build_safety_stats(now)

    window = {
        "start": _safe_iso(range_start),
        "end": _safe_iso(range_end),
    }

    return {
        "rangeDays": days,
        "window": window,
        "updatedAt": _safe_iso(now),
        "safetyStats": safety_stats,
        "detectTypeStats": {
            "total": detect_type_stats["total"],
            "series": detect_type_stats["series"],
            "window": window,
        },
        "handleRateStats": {
            "total": handle_rate_stats["total"],
            "series": handle_rate_stats["series"],
            "window": window,
        },
        "flightStats": {
            "totalTasks": flight_stats["totalTasks"],
            "byAirport": flight_stats["byAirport"],
            "distanceKm": flight_stats["distanceKm"],
            "durationHours": flight_stats["durationHours"],
            "window": window,
        },
        "waylineStats": {
            "total": wayline_stats["total"],
            "series": wayline_stats["series"],
            "window": window,
        },
        "hourlyDistribution": hourly_distribution,
        "handleDurationByType": handle_duration_by_type,
        "lineChart": line_chart,
        "trendDetailMap": trend_detail_map,
        "airportRiskRows": airport_risk_rows,
    }


def upsert_alarm_dashboard_cache(range_days, now=None):
    payload = compute_alarm_dashboard_cache(range_days, now=now)
    obj, _ = AlarmDashboardCache.objects.update_or_create(
        range_days=payload["rangeDays"],
        defaults={"dashboard_data": payload},
    )
    return obj


def refresh_alarm_dashboard_cache(range_days_list=None, now=None):
    days_list = range_days_list or DEFAULT_RANGE_DAYS
    results = []
    for days in days_list:
        results.append(upsert_alarm_dashboard_cache(days, now=now))
    return results


def get_alarm_dashboard_cache(range_days, refresh_if_missing=False):
    days = max(_to_int(range_days, 30), 1)
    obj = AlarmDashboardCache.objects.filter(range_days=days).first()
    if not obj and refresh_if_missing:
        obj = upsert_alarm_dashboard_cache(days)
    return obj
