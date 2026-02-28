import logging
import math

from django.db import DatabaseError
from django.utils import timezone

from telemetry_app.models import DockStatus, FlightStatsSession, FlightTaskInfo

logger = logging.getLogger(__name__)


def _to_float(value, default=math.nan):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _distance_meters(lat1, lon1, alt1, lat2, lon2, alt2):
    if not all(math.isfinite(v) for v in [lat1, lon1, lat2, lon2]):
        return math.nan
    rad = math.pi / 180.0
    phi1 = lat1 * rad
    phi2 = lat2 * rad
    d_phi = (lat2 - lat1) * rad
    d_lambda = (lon2 - lon1) * rad
    sin_dphi = math.sin(d_phi / 2.0)
    sin_dlambda = math.sin(d_lambda / 2.0)
    a_val = sin_dphi * sin_dphi + math.cos(phi1) * math.cos(phi2) * sin_dlambda * sin_dlambda
    c = 2.0 * math.atan2(math.sqrt(max(0.0, a_val)), math.sqrt(max(0.0, 1.0 - a_val)))
    horizontal = 6371000.0 * c
    if math.isfinite(alt1) and math.isfinite(alt2):
        dz = alt2 - alt1
        return math.sqrt(horizontal * horizontal + dz * dz)
    return horizontal


def _latest_task_for_sn(device_sn):
    if not device_sn:
        return None
    return FlightTaskInfo.objects.filter(sn=device_sn).order_by("-created_at").first()


def _task_for_session(session):
    if not session:
        return None
    task_uuid = str(session.task_uuid or "").strip()
    if task_uuid:
        task = FlightTaskInfo.objects.filter(task_uuid=task_uuid).first()
        if task:
            return task
    return _latest_task_for_sn(session.device_sn)


def _drone_in_dock_state(device_sn):
    if not device_sn:
        return None
    dock = (
        DockStatus.objects.filter(drone_sn=device_sn)
        .order_by("-last_update_time", "-updated_at")
        .first()
    )
    if not dock:
        return None
    value = dock.drone_in_dock
    if value in (0, "0"):
        return False
    if value in (1, "1"):
        return True
    return None


def _persist_task_stats(task, session, end_time=None):
    if not task or not session or not session.flight_started_at:
        return False
    end = end_time or session.last_position_time or timezone.now()
    started = session.flight_started_at
    duration_seconds = max(0, int((end - started).total_seconds()))
    distance_km = max(0.0, _to_float(session.distance_km, 0.0))
    distance_km = round(distance_km, 6)

    current_duration = int(task.flight_duration or 0)
    current_distance = _to_float(task.flight_distance, 0.0)
    update_data = {}
    if duration_seconds > current_duration:
        update_data["flight_duration"] = duration_seconds
    if distance_km > current_distance:
        update_data["flight_distance"] = distance_km

    if not update_data:
        return False
    FlightTaskInfo.objects.filter(pk=task.pk).update(**update_data)
    return True


def refresh_session_with_position(position):
    """
    处理单条无人机位置数据：
    - 飞行中：持续累加里程/时长
    - 未开始：按首个有效点启动会话
    """
    device_sn = str(getattr(position, "device_sn", "") or "").strip()
    if not device_sn:
        return False

    lat = _to_float(getattr(position, "latitude", None))
    lon = _to_float(getattr(position, "longitude", None))
    alt = _to_float(getattr(position, "altitude", 0.0), 0.0)
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return False
    timestamp = getattr(position, "timestamp", None) or timezone.now()

    try:
        session, _ = FlightStatsSession.objects.get_or_create(device_sn=device_sn)
    except DatabaseError as exc:
        logger.warning("FlightStatsSession get_or_create failed for %s: %s", device_sn, exc)
        return False

    if not session.is_active:
        # 仅在“明确在舱内”时拒绝启动；未知状态允许启动，避免漏记。
        in_dock = _drone_in_dock_state(device_sn)
        if in_dock is True:
            return False
        task = _latest_task_for_sn(device_sn)
        session.is_active = True
        session.task_uuid = task.task_uuid if task else ""
        session.flight_started_at = timestamp
        session.last_position_time = timestamp
        session.last_latitude = lat
        session.last_longitude = lon
        session.last_altitude = alt if math.isfinite(alt) else 0.0
        session.distance_km = 0.0
        session.save()
        if task:
            _persist_task_stats(task, session, end_time=timestamp)
        return True

    if session.last_position_time and timestamp < session.last_position_time:
        return False

    if not session.flight_started_at:
        session.flight_started_at = timestamp

    prev_lat = _to_float(session.last_latitude)
    prev_lon = _to_float(session.last_longitude)
    prev_alt = _to_float(session.last_altitude, 0.0)
    if math.isfinite(prev_lat) and math.isfinite(prev_lon):
        distance = _distance_meters(prev_lat, prev_lon, prev_alt, lat, lon, alt)
        if math.isfinite(distance) and distance >= 0:
            session.distance_km = max(0.0, _to_float(session.distance_km, 0.0) + (distance / 1000.0))

    session.last_position_time = timestamp
    session.last_latitude = lat
    session.last_longitude = lon
    session.last_altitude = alt if math.isfinite(alt) else 0.0

    task = _task_for_session(session)
    if task and session.task_uuid != task.task_uuid:
        session.task_uuid = task.task_uuid

    session.save()
    if task:
        _persist_task_stats(task, session, end_time=timestamp)
    return True


def finalize_session_for_device(device_sn, ended_at=None):
    """
    在无人机回舱时结束会话并写回任务统计。
    """
    normalized_sn = str(device_sn or "").strip()
    if not normalized_sn:
        return False
    session = FlightStatsSession.objects.filter(device_sn=normalized_sn).first()
    if not session or not session.is_active:
        return False

    final_time = ended_at or session.last_position_time or timezone.now()
    task = _task_for_session(session)
    if task:
        _persist_task_stats(task, session, end_time=final_time)

    session.is_active = False
    session.task_uuid = ""
    session.flight_started_at = None
    session.last_position_time = None
    session.last_latitude = None
    session.last_longitude = None
    session.last_altitude = None
    session.distance_km = 0.0
    session.save()
    return True


def get_realtime_task_stats(task):
    """
    返回任务的实时统计（若存在飞行会话，则覆盖为会话实时值）。
    """
    if not task:
        return {
            "flight_duration": 0,
            "flight_distance": 0.0,
            "flight_active": False,
        }

    duration = int(task.flight_duration or 0)
    distance = _to_float(task.flight_distance, 0.0)
    flight_active = False

    device_sn = str(task.sn or "").strip()
    if not device_sn:
        return {
            "flight_duration": duration,
            "flight_distance": round(max(0.0, distance), 6),
            "flight_active": False,
        }

    session = FlightStatsSession.objects.filter(device_sn=device_sn, is_active=True).first()
    if not session:
        return {
            "flight_duration": duration,
            "flight_distance": round(max(0.0, distance), 6),
            "flight_active": False,
        }

    session_task_uuid = str(session.task_uuid or "").strip()
    if session_task_uuid and session_task_uuid != str(task.task_uuid):
        return {
            "flight_duration": duration,
            "flight_distance": round(max(0.0, distance), 6),
            "flight_active": False,
        }

    if session.flight_started_at:
        end = session.last_position_time or timezone.now()
        session_duration = max(0, int((end - session.flight_started_at).total_seconds()))
        duration = max(duration, session_duration)
    session_distance = _to_float(session.distance_km, 0.0)
    distance = max(distance, session_distance)
    flight_active = True

    return {
        "flight_duration": duration,
        "flight_distance": round(max(0.0, distance), 6),
        "flight_active": flight_active,
    }
