import math
import time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from telemetry_app.flight_stats_tracker import finalize_session_for_device, refresh_session_with_position
from telemetry_app.models import DockStatus, DronePosition


DEFAULT_DEVICE_SN = "1581F8HGX255D00A0DK8"
DEFAULT_DEVICE_MODEL = "M30T"
DEFAULT_INTERVAL_SECONDS = 2.0
DEFAULT_RADIUS_METERS = 35.0
DEFAULT_ALTITUDE_METERS = 85.0
DEFAULT_CENTER_LATITUDE = 39.90750000
DEFAULT_CENTER_LONGITUDE = 116.39139000
DEFAULT_BATTERY_PERCENT = 96
DEFAULT_SIGNAL_QUALITY = 90
EARTH_METERS_PER_DEGREE = 111320.0


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def normalize_heading(degrees):
    value = degrees % 360.0
    return value + 360.0 if value < 0 else value


def decimal_coord(value):
    return Decimal(f"{value:.8f}")


class Command(BaseCommand):
    help = "按固定间隔持续向 DronePosition 表写入模拟无人机位置数据"

    def add_arguments(self, parser):
        parser.add_argument("--device-sn", default=DEFAULT_DEVICE_SN, help=f"无人机 SN，默认 {DEFAULT_DEVICE_SN}")
        parser.add_argument("--device-model", default=DEFAULT_DEVICE_MODEL, help=f"无人机型号，默认 {DEFAULT_DEVICE_MODEL}")
        parser.add_argument("--dock-sn", default="", help="可选：联动更新的机场 SN")
        parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS, help=f"插入间隔秒数，默认 {DEFAULT_INTERVAL_SECONDS}")
        parser.add_argument("--count", type=int, default=0, help="插入条数，默认 0 表示持续运行直到 Ctrl+C")
        parser.add_argument("--center-lat", type=float, default=DEFAULT_CENTER_LATITUDE, help=f"轨迹中心纬度，默认 {DEFAULT_CENTER_LATITUDE}")
        parser.add_argument("--center-lon", type=float, default=DEFAULT_CENTER_LONGITUDE, help=f"轨迹中心经度，默认 {DEFAULT_CENTER_LONGITUDE}")
        parser.add_argument("--radius", type=float, default=DEFAULT_RADIUS_METERS, help=f"绕圈半径(米)，默认 {DEFAULT_RADIUS_METERS}")
        parser.add_argument("--altitude", type=float, default=DEFAULT_ALTITUDE_METERS, help=f"飞行高度(米)，默认 {DEFAULT_ALTITUDE_METERS}")
        parser.add_argument("--altitude-wave", type=float, default=6.0, help="高度波动振幅(米)，默认 6")
        parser.add_argument("--battery", type=int, default=DEFAULT_BATTERY_PERCENT, help=f"起始电量，默认 {DEFAULT_BATTERY_PERCENT}")
        parser.add_argument("--signal", type=int, default=DEFAULT_SIGNAL_QUALITY, help=f"信号质量，默认 {DEFAULT_SIGNAL_QUALITY}")
        parser.add_argument("--speed", type=float, default=8.0, help="水平速度(m/s)，默认 8")
        parser.add_argument("--heading-step", type=float, default=18.0, help="每次写入航向增量(度)，默认 18")
        parser.add_argument("--bind-dock", action="store_true", help="启动时把机场标记为飞行中，停止时恢复为在舱")
        parser.add_argument("--mqtt-topic", default="", help="模拟写入的 MQTT topic，默认自动生成")

    def handle(self, *args, **options):
        device_sn = str(options["device_sn"] or "").strip()
        if not device_sn:
            self.stderr.write(self.style.ERROR("device-sn 不能为空"))
            return

        interval = float(options["interval"])
        if interval <= 0:
            self.stderr.write(self.style.ERROR("interval 必须大于 0"))
            return

        count = int(options["count"])
        if count < 0:
            self.stderr.write(self.style.ERROR("count 不能小于 0"))
            return

        device_model = str(options["device_model"] or "").strip() or DEFAULT_DEVICE_MODEL
        dock_sn = str(options["dock_sn"] or "").strip()
        center_lat = float(options["center_lat"])
        center_lon = float(options["center_lon"])
        radius = max(0.0, float(options["radius"]))
        base_altitude = float(options["altitude"])
        altitude_wave = max(0.0, float(options["altitude_wave"]))
        battery_start = clamp(int(options["battery"]), 0, 100)
        signal_quality = clamp(int(options["signal"]), 0, 100)
        horizontal_speed = max(0.0, float(options["speed"]))
        heading_step = float(options["heading_step"])
        bind_dock = bool(options["bind_dock"])
        mqtt_topic = str(options["mqtt_topic"] or "").strip() or f"simulate/product/{device_sn}/osd"

        dock = self.resolve_dock(dock_sn, device_sn)
        if dock_sn and not dock:
            self.stderr.write(self.style.WARNING(f"未找到 dock_sn={dock_sn} 对应的机场记录，脚本将只写 DronePosition"))

        if bind_dock and dock:
            self.mark_dock_flying(dock, device_sn, battery_start)

        self.stdout.write(self.style.SUCCESS("开始模拟写入无人机位置报文"))
        self.stdout.write(f"  device_sn={device_sn}")
        self.stdout.write(f"  device_model={device_model}")
        self.stdout.write(f"  interval={interval}s")
        self.stdout.write(f"  count={'infinite' if count == 0 else count}")
        self.stdout.write(f"  center=({center_lat}, {center_lon}) radius={radius}m altitude={base_altitude}m")
        if dock:
            self.stdout.write(f"  dock={dock.dock_sn} bind_dock={bind_dock}")

        index = 0
        try:
            while count == 0 or index < count:
                timestamp = timezone.now()
                heading = normalize_heading(index * heading_step)
                angle_rad = math.radians(heading)
                latitude, longitude = self.compute_position(center_lat, center_lon, radius, angle_rad)
                altitude = base_altitude + math.sin(angle_rad * 1.7) * altitude_wave
                relative_height = max(0.0, altitude)
                battery_percent = clamp(int(round(battery_start - index * 0.08)), 0, 100)
                vertical_speed = math.cos(angle_rad * 1.7) * 0.5

                position = self.create_position(
                    device_sn=device_sn,
                    device_model=device_model,
                    latitude=latitude,
                    longitude=longitude,
                    altitude=altitude,
                    relative_height=relative_height,
                    heading=heading,
                    speed_horizontal=horizontal_speed,
                    speed_vertical=vertical_speed,
                    battery_percent=battery_percent,
                    signal_quality=signal_quality,
                    timestamp=timestamp,
                    mqtt_topic=mqtt_topic,
                )

                refresh_session_with_position(position)

                if dock and bind_dock:
                    self.update_dock_realtime(dock, device_sn, latitude, longitude, battery_percent, timestamp)

                self.stdout.write(
                    f"[{index + 1}] {timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"lat={float(latitude):.8f} lon={float(longitude):.8f} "
                    f"alt={altitude:.2f} heading={heading:.1f} battery={battery_percent}%"
                )

                index += 1
                if count == 0 or index < count:
                    time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("收到 Ctrl+C，准备停止模拟"))
        finally:
            if dock and bind_dock:
                self.mark_dock_landed(dock, device_sn, timestamp=timezone.now())
            else:
                finalize_session_for_device(device_sn, ended_at=timezone.now())

        self.stdout.write(self.style.SUCCESS("模拟写入结束"))

    def resolve_dock(self, dock_sn, device_sn):
        if dock_sn:
            return DockStatus.objects.filter(dock_sn=dock_sn).first()
        return DockStatus.objects.filter(drone_sn=device_sn).order_by("-last_update_time", "-updated_at").first()

    def compute_position(self, center_lat, center_lon, radius_meters, angle_rad):
        lat_offset_deg = (radius_meters * math.sin(angle_rad)) / EARTH_METERS_PER_DEGREE
        lon_scale = max(0.000001, math.cos(math.radians(center_lat)))
        lon_offset_deg = (radius_meters * math.cos(angle_rad)) / (EARTH_METERS_PER_DEGREE * lon_scale)
        latitude = center_lat + lat_offset_deg
        longitude = center_lon + lon_offset_deg
        return decimal_coord(latitude), decimal_coord(longitude)

    @transaction.atomic
    def create_position(
        self,
        *,
        device_sn,
        device_model,
        latitude,
        longitude,
        altitude,
        relative_height,
        heading,
        speed_horizontal,
        speed_vertical,
        battery_percent,
        signal_quality,
        timestamp,
        mqtt_topic,
    ):
        raw_data = {
            "device_sn": device_sn,
            "device_model": device_model,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "height": round(altitude, 2),
            "altitude": round(altitude, 2),
            "relative_height": round(relative_height, 2),
            "heading": round(heading, 2),
            "attitude_head": round(heading, 2),
            "battery_percent": battery_percent,
            "signal_quality": signal_quality,
            "speed_horizontal": round(speed_horizontal, 2),
            "speed_vertical": round(speed_vertical, 2),
            "simulated": True,
            "timestamp": timestamp.isoformat(),
        }

        return DronePosition.objects.create(
            device_sn=device_sn,
            device_model=device_model,
            latitude=latitude,
            longitude=longitude,
            altitude=round(altitude, 2),
            relative_height=round(relative_height, 2),
            heading=round(heading, 2),
            speed_horizontal=round(speed_horizontal, 2),
            speed_vertical=round(speed_vertical, 2),
            battery_percent=battery_percent,
            signal_quality=signal_quality,
            raw_data=raw_data,
            mqtt_topic=mqtt_topic,
            timestamp=timestamp,
        )

    def mark_dock_flying(self, dock, device_sn, battery_percent):
        now = timezone.now()
        dock.drone_sn = device_sn
        dock.drone_in_dock = 0
        dock.drone_charge_state = 0
        dock.drone_battery_percent = battery_percent
        dock.is_online = True
        dock.last_update_time = now
        dock.save(update_fields=[
            "drone_sn",
            "drone_in_dock",
            "drone_charge_state",
            "drone_battery_percent",
            "is_online",
            "last_update_time",
            "updated_at",
        ])

    def update_dock_realtime(self, dock, device_sn, latitude, longitude, battery_percent, timestamp):
        dock.latitude = latitude
        dock.longitude = longitude
        dock.drone_sn = device_sn
        dock.drone_in_dock = 0
        dock.drone_battery_percent = battery_percent
        dock.is_online = True
        dock.last_update_time = timestamp
        dock.save(update_fields=[
            "latitude",
            "longitude",
            "drone_sn",
            "drone_in_dock",
            "drone_battery_percent",
            "is_online",
            "last_update_time",
            "updated_at",
        ])

    def mark_dock_landed(self, dock, device_sn, timestamp):
        dock.drone_sn = device_sn
        dock.drone_in_dock = 1
        dock.drone_charge_state = 1
        dock.is_online = True
        dock.last_update_time = timestamp
        dock.save(update_fields=[
            "drone_sn",
            "drone_in_dock",
            "drone_charge_state",
            "is_online",
            "last_update_time",
            "updated_at",
        ])
        finalize_session_for_device(device_sn, ended_at=timestamp)
