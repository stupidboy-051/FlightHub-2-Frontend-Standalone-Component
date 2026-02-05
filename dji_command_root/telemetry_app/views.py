import json
import mimetypes
import os
import time
import math  # 🔥 Added for GPS calculation
import threading
from concurrent.futures import ThreadPoolExecutor, wait
import requests
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
# views.py
import uuid
# 1. 保持 Python 原生导入不变
from datetime import datetime, timezone
# --- 请确保 views.py 顶部包含这些引用 ---
import json
import re
import os
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import zipfile
import io
import re
import tempfile
CV2_IMPORT_ERROR = None
try:
    import cv2
except ImportError as e:
    cv2 = None
    CV2_IMPORT_ERROR = str(e)
except Exception as e:
    cv2 = None
    CV2_IMPORT_ERROR = f"Unexpected Error: {str(e)}"

from django.conf import settings  # 🔥 必须导入 settings
from .models import WaylineFingerprint, Wayline, AlarmCategory

# --- 补充 MinIO 客户端配置 (解决 'client' 报错) ---
# 如果你之前是在某个函数里定义的 client，现在需要把它放到外面变成全局变量，
# 这样新的 scan_candidate_folders 函数才能用它。
# 请确保这段代码在 views.py 的所有函数之前：


# 2. ⭐ 修改 Django 的导入，给它起个别名避免冲突
from django.utils import timezone as django_timezone
import boto3
from botocore.client import Config

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404
from django.utils._os import safe_join
from django.db import transaction
from django.db.models import Count, Q

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.reverse import reverse

from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Alarm, AlarmCategory, AlarmDashboardStats, Wayline, WaylineImage,
    ComponentConfig, MediaFolderConfig, InspectTask, InspectImage, UserProfile,
    DronePosition, FlightTaskInfo, DockStatus, SuspiciousImage
)

from .serializers import (
    AlarmSerializer, AlarmCategorySerializer, WaylineSerializer,
    WaylineImageSerializer, UserSerializer, UserCreateSerializer,
    LoginSerializer, TokenSerializer, ComponentConfigSerializer,
    MediaFolderConfigSerializer, InspectTaskSerializer, InspectImageSerializer,
    InspectImageListSerializer,
    DronePositionSerializer, DockStatusSerializer, FlightTaskInfoSerializer,
    SuspiciousImageSerializer
)

from .filters import AlarmFilter, WaylineImageFilter
from .alarm_dashboard_stats import resolve_window, upsert_alarm_dashboard_stats
from .permissions import IsSystemAdmin
from .pagination import StandardResultsSetPagination


# ======================================================================
# 1. 核心业务逻辑 helper (新增/修改部分)
# ======================================================================

# 🔥 全局信号量：限制同时处理视频的线程数不超过 2 个
VIDEO_PROCESS_SEMAPHORE = threading.BoundedSemaphore(2)

def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name=getattr(settings, "MINIO_REGION", "us-east-1"),
        config=Config(signature_version="s3v4"),
    )

def calculate_drone_gps(target_time_utc):
    """
    根据目标时间(UTC)查找最近的无人机位置并计算目标点坐标
    """
    from datetime import timedelta
    
    # 1. 查找最近记录 (前后 2 秒)
    start_time = target_time_utc - timedelta(seconds=2)
    end_time = target_time_utc + timedelta(seconds=2)
    
    logs = DronePosition.objects.filter(
        timestamp__range=(start_time, end_time)
    ).only('timestamp', 'latitude', 'longitude', 'altitude', 'raw_data', 'heading')
    
    if not logs.exists():
        # 🔥 终极兜底：如果时间点找不到，尝试找最近的一条记录 (不限时间)
        latest_log = DronePosition.objects.order_by('-timestamp').first()
        if latest_log:
             print(f"⚠️ [GPS Calc] 指定时间无记录，使用最近一次已知位置兜底 (Time: {latest_log.timestamp})")
             return {
                "lat": float(latest_log.latitude),
                "lon": float(latest_log.longitude),
                "high": float(latest_log.altitude),
                "method": "FALLBACK_LATEST_POS"
            }
        return None
        
    # 内存中找最近
    nearest_log = min(logs, key=lambda x: abs((x.timestamp - target_time_utc).total_seconds()))
    
    # 2. 计算坐标
    try:
        data = nearest_log.raw_data.get("data", {}) if nearest_log.raw_data else {}
        # 兼容不同 payload 结构
        if "latitude" not in data and "lat" not in data:
             if "latitude" in nearest_log.raw_data:
                 data = nearest_log.raw_data
        
        # 优先使用 raw_data 里的，如果没有则用模型字段
        drone_lat = float(data.get("latitude") or nearest_log.latitude or 0)
        drone_lon = float(data.get("longitude") or nearest_log.longitude or 0)
        height = float(data.get("height") or data.get("altitude") or nearest_log.altitude or 0)
        
        # 提取 Payload (挂载设备信息)
        payload = data.get("99-0-0", {})
        if not payload and "output" in data:
             payload = data.get("output", {}).get("ext", {})

        pitch = float(payload.get("gimbal_pitch", 0))
        yaw = float(payload.get("gimbal_yaw", 0))
        
        # 修正：如果 payload 里没找到 pitch/yaw，尝试从 data 根节点找
        if pitch == 0 and "gimbal_pitch" in data:
            pitch = float(data["gimbal_pitch"])
        if yaw == 0 and "gimbal_yaw" in data:
            yaw = float(data["gimbal_yaw"])
            
        # 如果还是没有 Yaw，使用无人机的 heading
        if yaw == 0 and nearest_log.heading is not None:
            yaw = float(nearest_log.heading)

        dji_lat = float(payload.get("measure_target_latitude", 0))
        dji_lon = float(payload.get("measure_target_longitude", 0))
        dji_alt = float(payload.get("measure_target_altitude", -9999)) # 目标海拔
        error_state = int(payload.get("measure_target_error_state", 1))

        # --- 策略 A: 硬件测距 ---
        if error_state == 0 and dji_lat != 0:
            return {
                "lat": dji_lat, 
                "lon": dji_lon, 
                "high": dji_alt if dji_alt != -9999 else height, # 优先用测距高度
                "method": "HARDWARE_RTK"
            }

        # --- 策略 B/C 参数准备 ---
        R_EARTH = 6378137.0
        calc_distance = 0.0
        method_tag = ""
        final_target_alt = 0.0 # 推算模式下，默认高度为0 (地面)
        
        if pitch <= -10:
            # 策略 B: 几何推算
            angle_rad = math.radians(abs(pitch))
            calc_distance = height / math.tan(angle_rad)
            if calc_distance > 500: calc_distance = 500
            method_tag = "TRIG_CALC"
        else:
            # 策略 C: 平视兜底
            # 动态调整：如果无人机飞得很低(比如10米)，只看前方20米
            if height < 10:
                calc_distance = 20.0
            else:
                calc_distance = 80.0
            method_tag = "FIXED_ESTIMATE"
            
        # --- 坐标投影 ---
        yaw_rad = math.radians(yaw)
        delta_north = calc_distance * math.cos(yaw_rad)
        delta_east = calc_distance * math.sin(yaw_rad)
        
        delta_lat = (delta_north / R_EARTH) * (180 / math.pi)
        # 经度变化 (需考虑纬度收敛)
        delta_lon = (delta_east / (R_EARTH * math.cos(math.radians(drone_lat)))) * (180 / math.pi)
        
        return {
            "lat": drone_lat + delta_lat,
            "lon": drone_lon + delta_lon,
            "high": final_target_alt,
            "method": method_tag
        }
        
    except Exception as e:
        print(f"❌ [GPS Calc] 计算异常: {e}")
        # 保底返回无人机位置
        return {
            "lat": float(nearest_log.latitude),
            "lon": float(nearest_log.longitude),
            "high": float(nearest_log.altitude),
            "method": "FALLBACK_DRONE_POS"
        }


def put_object_bytes(s3_client, bucket_name, object_name, data: bytes, content_type: str = "application/octet-stream"):
    """
    MinIO上传辅助函数：自动封装BytesIO并处理长度
    """
    data_stream = io.BytesIO(data)
    # boto3 put_object 会自动计算 BytesIO 的长度
    return s3_client.put_object(
        Bucket=bucket_name,
        Key=object_name,
        Body=data_stream,
        ContentType=content_type
    )

def safe_save(instance, retries=5, delay=0.5, **kwargs):
    """
    Helper function to save model instances with retry logic for handling database locks.
    """
    import time
    from django.db.utils import OperationalError
    
    for attempt in range(retries):
        try:
            instance.save(**kwargs)
            return True
        except OperationalError as e:
            # Check for database locked error (handling both string and object)
            error_str = str(e).lower()
            if "locked" in error_str:
                if attempt < retries - 1:
                    # Exponential backoff with jitter
                    import random
                    sleep_time = delay * (2 ** attempt) + random.uniform(0, 0.1)
                    time.sleep(sleep_time)
                    continue
            
            print(f"❌ [DB] Save failed after {attempt+1} attempts: {e}")
            if attempt == retries - 1:
                 print(f"❌ [DB] Final save failure for {instance}: {e}")
                 return False
        except Exception as e:
            print(f"❌ [DB] Unexpected error saving {instance}: {e}")
            if attempt == retries - 1:
                return False
    return False


# views.py 添加

def get_image_action_uuid_from_minio(s3_client, bucket, key):
    """
    [核心工具] 读取 MinIO 图片头部(前64KB)，提取 XMP 中的 FlightLineInfo (ActionUUID)
    """
    try:
        # 只读取前 64KB (Range Header)，避免下载几MB的大图
        resp = s3_client.get_object(Bucket=bucket, Key=key, Range='bytes=0-65535')
        head_data = resp['Body'].read()

        # 尝试解码 (XMP 是 ASCII/UTF-8 文本，混在二进制里)
        # 使用 latin-1 读取可以避免 decode 报错，且能保留英文字符
        try:
            text_data = head_data.decode('latin-1', errors='ignore')
        except:
            return None

        # 正则搜索 UUID
        # 格式通常是 drone-dji:FlightLineInfo="270f6508-..."
        # 或者 <drone-dji:FlightLineInfo>270f6508-...</drone-dji:FlightLineInfo>
        # 宽容模式：匹配 FlightLineInfo 后面的 36 位 UUID，允许中间有 =" 或 > 等字符
        match = re.search(r'FlightLineInfo.*?([0-9a-fA-F-]{36})', text_data)

        if match:
            uuid = match.group(1)
            print(f"🔍 [UUID Extract] 成功从 {key} 提取 UUID: {uuid}")
            return uuid
        else:
             # 调试日志：如果没提取到，打印一下相关片段，方便排查
             snippet_idx = text_data.find("FlightLineInfo")
             if snippet_idx != -1:
                 print(f"⚠️ [UUID Debug] 找到关键词但未匹配 UUID: ...{text_data[snippet_idx:snippet_idx+100]}...")
             else:
                 pass # 没找到关键词


    except Exception as e:
        # 只有在读不到或者不是图片时才会报错，属于正常现象
        # print(f"⚠️ 读取图片元数据失败: {key} - {e}")
        pass
    return None


# views.py

def sync_images_core(task):
    """
    [核心工具] 同步 MinIO 图片到数据库
    返回: 本次新发现的图片数量
    """
    s3 = get_minio_client()
    bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "dji")
    created_count = 0

    # 🛡️ 防御性编程：如果 prefix_list 为空，尝试根据 UUID 自动猜测路径
    # 你的截图路径类似: fh_sync/2025.../media/{uuid}/
    if not task.prefix_list:
        # 这是一个兜底策略，最好是在 Poller 里就存好
        print(f"⚠️ 任务 {task.id} 没有路径前缀，尝试搜索...")
        return 0

    try:
        # 遍历所有配置的前缀（通常只有一个）
        for folder_prefix in task.prefix_list:
            paginator = s3.get_paginator('list_objects_v2')

            # 开始扫描 MinIO
            for page in paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix):
                if "Contents" not in page: continue

                for obj in page["Contents"]:
                    key = obj["Key"]

                    # 1. 过滤非图片文件
                    if not key.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                        continue

                    # 2. 过滤算法生成的结果图 (防止死循环检测)
                    filename = key.split('/')[-1]
                    if filename.startswith("detected_") or "result" in filename:
                        continue

                    # 3. 查重 (数据库里没有才加)
                    # 使用 update_or_create 避免并发时的唯一性报错
                    if not InspectImage.objects.filter(inspect_task=task, object_key=key).exists():
                        InspectImage.objects.create(
                            inspect_task=task,
                            wayline=task.wayline,  # 如果任务关联了航线，传给图片
                            object_key=key,
                            detect_status="pending"  # 初始状态为待检测
                        )
                        created_count += 1
                        print(f"✨ [New Image] 捕获新图: {filename}")

    except Exception as e:
        print(f"❌ [Sync Error] 同步图片失败: {e}")
        return 0

    return created_count
def sync_images_core1(task):
    """MinIO 同步逻辑"""
    if not task.prefix_list: return 0
    folder_prefix = task.prefix_list[0]
    s3 = get_minio_client()
    created_count = 0
    try:
        paginator = s3.get_paginator('list_objects_v2')
        bucket_name = getattr(task, 'bucket', 'dji')

        for page in paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix):
            if "Contents" not in page: continue
            for obj in page["Contents"]:
                key = obj["Key"]
                if not key.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")): continue

                # 🔥 新增：跳过算法输出的结果图片（detected_ 开头的文件）
                filename = key.split('/')[-1]
                if filename.startswith("detected_"):
                    continue

                if not InspectImage.objects.filter(inspect_task=task, object_key=key).exists():
                    InspectImage.objects.create(
                        inspect_task=task,
                        wayline=task.wayline,
                        object_key=key,
                        detect_status="pending"
                    )
                    created_count += 1
        return created_count
    except Exception as e:
        print(f"❌ [Sync] Error: {e}")
        return 0


# views.py

# views.py

def create_alarm_from_detection(task, img, result_data):
    try:
        # 1. 解析病害描述 (列表 -> 字符串)
        # 算法返回: "defects_description": ["绝缘子破损", "螺母松动"]
        defects_list = result_data.get("defects_description", [])

        # 将列表转为字符串: "绝缘子破损, 螺母松动"
        if defects_list:
            content_text = ", ".join([str(d) for d in defects_list])
            # 取第一个作为 code 去匹配数据库分类 (用于统计)
            primary_code = defects_list[0]
        else:
            content_text = "AI检测发现异常(未说明类型)"
            primary_code = "UNKNOWN"

        # 2. 匹配分类 (数据库 Category 外键)
        # 虽然 Content 直接写了描述，但 category_id 还是需要关联的，方便以后筛选
        sub_category = AlarmCategory.objects.filter(code=primary_code).first()
        if not sub_category:
            sub_category = task.detect_category

        # 3. 提取 GPS (硬性要求)
        gps = result_data.get("gps") or {}
        lat = gps.get("lat", 0)  # 如果没 GPS，默认经纬度 0
        lon = gps.get("lon", 0)
        high = gps.get("high")  # 提取高度信息（可能为空）

        # 🔥 尝试关联 FlightTaskInfo (方便统计)
        flight_task_obj = None
        if getattr(task, 'dji_task_uuid', None):
            flight_task_obj = FlightTaskInfo.objects.filter(task_uuid=task.dji_task_uuid).first()

        # 4. 创建告警（避免重复创建）
        # 🔥 使用循环 + try-except 捕获并发竞态条件和数据库锁
        import time
        from django.db.utils import OperationalError

        for attempt in range(5):
            try:
                alarm, created = Alarm.objects.get_or_create(
                    source_image=img,
                    defaults={
                        'wayline': task.wayline,
                        'flight_task': flight_task_obj,
                        'category': sub_category,
                        'image_url': result_data.get("result_object_key") or img.object_key,
                        'specific_data': result_data,
                        'content': f"AI检测发现: {content_text}",
                        'latitude': lat,
                        'longitude': lon,
                        'high': high,
                        'status': "PENDING",
                        'handler': "AI_ALGORITHM"
                    }
                )

                if created:
                    print(f"🚨 [Alarm] 告警创建成功！内容: {content_text}, 高度: {high}")
                else:
                    print(f"ℹ️ [Alarm] 告警已存在 (ID: {alarm.id})，跳过创建。图片ID: {img.id}")
                
                # 成功则退出循环
                break

            except OperationalError as e:
                # 处理数据库锁定
                if "locked" in str(e):
                    if attempt < 4:
                        sleep_time = 0.5 * (attempt + 1)
                        # print(f"⏳ [Alarm] DB Locked, retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                        continue
                print(f"❌ [Alarm] DB Error: {e}")
                if attempt == 4:
                    raise

            except Exception as alarm_error:
                # 🔥 如果是唯一性约束错误，说明其他线程已经创建了告警，忽略即可
                if "UNIQUE constraint" in str(alarm_error) or "unique constraint" in str(alarm_error).lower():
                    print(f"ℹ️ [Alarm] 告警已存在（并发创建），跳过。图片ID: {img.id}")
                    break
                else:
                    # 其他类型的错误，抛出异常
                    raise

    except Exception as e:
        print(f"❌ [Alarm] 创建失败: {e}")
        import traceback
        traceback.print_exc()

def normalize_detect_code(code):
    if not code:
        return "rail"
    raw = str(code).strip()
    low = raw.lower()
    mapping = {
        "rail": "rail",
        "track": "rail",
        "bridge": "bridge",
        "contactline": "contactline",
        "catenary": "contactline",
        "overhead": "contactline",
        "insulator": "contactline",
        "pole": "contactline",
        "protected_area": "protected_area",
        "protection_zone": "protected_area",
        "protection_area": "protected_area",
    }
    normalized = mapping.get(low)
    if normalized:
        return normalized
    if low in {"rail", "contactline", "bridge", "protected_area"}:
        return low
    # 🔥 修复：不认识的类型不要默认返回 rail，否则会导致 unknown 类型匹配到 rail 的关键词
    return raw

def auto_trigger_detect1(task):
    """
    自动检测全流程 (本地 Mock 版 - 适配 defects_description 列表协议)
    """
    images = task.images.filter(detect_status="pending").order_by("id")
    if not images.exists(): return

    task.detect_status = "processing"
    task.started_at = django_timezone.now()
    safe_save(task, update_fields=['detect_status', 'started_at'])

    # 获取检测类型 (RAIL, BRIDGE...)
    algo_type = normalize_detect_code(task.detect_category.code) if task.detect_category else "rail"

    for i, img in enumerate(images):
        img.detect_status = "processing"
        safe_save(img, update_fields=['detect_status'])

        # =================================================================
        # 🛑 旧代码注释区 (这里保持不变，以后接真实算法时用)
        # =================================================================
        """
        # 注意：以后接真实算法时，payload 也要改成只发 3 个字段
        payload = {
            "bucket": task.bucket,
            "object_key": img.object_key,
            "detect_type": algo_type
        }
        try:
            detect_url = getattr(settings, "FASTAPI_DETECT_URL", "http://localhost:8001/detect")
            resp = requests.post(detect_url, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json() # 直接拿根对象
                img.result = data
                img.detect_status = "done"
                img.save(update_fields=['detect_status', 'result'])

                # 判断列表是否有值
                if data.get("defects_description"): 
                    create_alarm_from_detection(task, img, data)
            else:
                img.detect_status = "failed"
                img.save(update_fields=['detect_status'])
        except Exception:
            img.detect_status = "failed"
            img.save(update_fields=['detect_status'])
        """
        # =================================================================

        # =================================================================
        # ✅ 新代码 (Mock 模拟逻辑 - 已更新为列表格式)
        # =================================================================
        try:
            # 1. 模拟耗时
            time.sleep(0.2)

            # 2. 制造假结果 (每 3 张图出 1 个异常)
            is_defect = (i % 3 == 0)

            # 构造异常列表：如果有病害，列表里放一个类型代码；否则为空列表
            mock_defects_list = [algo_type] if is_defect else []

            if is_defect:
                print(f"   ⚠️ [Mock] 图片 {img.id} -> 发现异常 ({mock_defects_list})")
            else:
                print(f"   ✅ [Mock] 图片 {img.id} -> 正常")

            # ⭐ 3. 构造完全符合新协议的 JSON
            data = {
                # 必须有的结果图路径 (假装原图就是结果图)
                "result_object_key": img.object_key,

                # 关键：用列表表达异常
                "defects_description": mock_defects_list,

                # 状态位 (可选，辅助参考)
                "detection_status": 1 if is_defect else 0,

                # 关键：必须带 GPS，否则数据库报错
                "gps": {"lat": 0, "lon": 0}
            }

            # 4. 保存结果到 InspectImage
            img.result = data
            img.detect_status = "done"
            img.save(update_fields=['detect_status', 'result'])

            # 5. 触发告警 (判断列表是否非空)
            if len(mock_defects_list) > 0:
                create_alarm_from_detection(task, img, data)

        except Exception as e:
            print(f"❌ [Mock] 模拟出错: {e}")
            import traceback
            traceback.print_exc()
            img.detect_status = "failed"
            safe_save(img, update_fields=['detect_status'])
        # =================================================================

    task.finished_at = django_timezone.now()
    task.detect_status = "done"
    safe_save(task, update_fields=['detect_status', 'finished_at'])
    print(f"🏁 [Detect] 任务 {task.id} 结束.")

def process_single_image(img, task, detect_url, algo_type, submit_time=None):
    """处理单张图片的逻辑（供并发调用）"""
    import time
    
    # 🔥 计算排队时间 (如果提供了提交时间)
    wait_cost = 0
    if submit_time:
        wait_cost = time.time() - submit_time
    
    # 🔥 [Double Check] 防止队列积压导致的重复处理
    # 如果图片已经被其他线程处理完了(status='done')，就直接跳过
    try:
        img.refresh_from_db()
        if img.detect_status == 'done':
            print(f"⏩ [Skip] 图片 {img.id} 已标记为完成，跳过重复检测")
            return
    except Exception:
        # 如果查询数据库失败（例如被删了），暂不处理，继续后续逻辑尝试
        pass
    
    # 1. 构造极简请求 (符合之前确认的3字段协议)
    payload = {
        # 1. 必填字段 (算法要的)
        "req_id": f"req_{uuid.uuid4().hex[:8]}",  # 随机生成一个ID
        "image_id": img.id,  # 真实的图片ID
        "wayline_id": str(task.wayline_id) if task.wayline_id else "0",  # 转字符串
        "timestamp": int(time.time()),  # 当前时间戳

        # 2. 核心字段 (业务要的)
        "bucket": task.bucket,
        "object_key": img.object_key,
        "detect_type": algo_type
    }

    # 🔥 [新增] 注入 GPS 信息 (如果之前的步骤计算出来了)
    if img.result and isinstance(img.result, dict) and "gps" in img.result:
        payload["gps"] = img.result["gps"]
        # print(f"📤 [Detect] 注入 GPS 信息到算法请求: {payload['gps']}")

    # 🔥 性能监控：记录开始时间
    detect_start_time = time.time()

    try:
        # 🔥 修复 5：增加超时时间到 600 秒（10分钟），适应 GLM-4V 模型处理速度
        # GLM-4V 等大模型处理图片通常需要 1-2 分钟，极端情况可能更长
        req_start = time.time()
        resp = requests.post(detect_url, json=payload, timeout=600)
        http_cost = time.time() - req_start

        # 🔥 性能监控：记录耗时
        elapsed_time = time.time() - detect_start_time
        print(f"⏱️ [Detect] 图片 {img.id} 流程耗时: {elapsed_time:.2f}s (排队等待: {wait_cost:.2f}s, HTTP请求: {http_cost:.2f}s)")

        # 🔥 性能警告：如果耗时过长，记录日志
        if elapsed_time > 120:
            print(f"⚠️ [Detect] 图片 {img.id} 检测耗时较长: {elapsed_time:.2f} 秒")

        if resp.status_code == 200:
            # ⭐ 改动点1：直接获取 JSON，不要 .get("data")
            # 因为算法返回的是扁平结构
            data = resp.json()

            # 🔥 增强统计：尝试获取算法服务端耗时
            server_cost = data.get("cost_time") or data.get("inference_time") or data.get("process_time") or data.get("time_cost")
            if server_cost:
                try:
                    s_cost = float(server_cost)
                    n_cost = http_cost - s_cost
                    print(f"🔍 [Perf] 图片 {img.id} 耗时拆解 >> 算法内部: {s_cost:.2f}s | 网络传输/排队: {n_cost:.2f}s")
                except:
                    pass

            img.result = data
            img.detect_status = "done"
            safe_save(img, update_fields=['detect_status', 'result'])

            algo_status = data.get("detection_status", 0)

            if algo_status == 1:
                # 只有真的是异常 (1)，才创建 Alarm 记录
                print(f"⚠️ [Detect] 图片 {img.id} 确认为异常 (Status=1)，生成告警...")
                create_alarm_from_detection(task, img, data)
            else:
                # 正常 (0)，只打印日志，不往 Alarm 表里写垃圾数据
                print(f"✅ [Detect] 图片 {img.id} 检测通过 (Status=0).")
        else:
            print(f"❌ [Detect] 算法返回错误: {resp.status_code} - {resp.text}")

            # 🔥 算法服务错误（5xx）可以重试，客户端错误（4xx）不重试
            if resp.status_code >= 500 and img.retry_count < img.max_retries:
                img.retry_count += 1
                img.detect_status = "pending"  # 重新入队
                print(f"🔄 [Detect] 图片 {img.id} 算法服务错误 {resp.status_code}，重试 ({img.retry_count}/{img.max_retries})")
                time.sleep(10) # 简单避让
                safe_save(img)
            else:
                img.detect_status = "failed"
                safe_save(img, update_fields=['detect_status'])

    # 🔥 修复 3：改进异常处理，区分超时、连接错误等
    except requests.Timeout:
        # 超时：可能是算法服务慢
        elapsed_time = time.time() - detect_start_time
        print(f"⏱️ [Detect] 图片 {img.id} 检测超时 ({elapsed_time:.2f} 秒)")

        # 🔥 修复 4：添加重试机制
        if img.retry_count < img.max_retries:
            img.retry_count += 1
            # 💡 增加冷却时间，避免立即重试再次超时
            print(f"💤 [Detect] 图片 {img.id} 进入冷却 (30秒) 后重试...")
            time.sleep(30)
            img.detect_status = "pending"  # 重新入队
            print(f"🔄 [Detect] 图片 {img.id} 冷却结束，准备重试 ({img.retry_count}/{img.max_retries})")
        else:
            img.detect_status = "failed"
            print(f"❌ [Detect] 图片 {img.id} 检测超时，达到最大重试次数 ({img.max_retries})")
        safe_save(img)

    except requests.ConnectionError as conn_err:
        # 连接错误：算法服务可能挂了
        print(f"🔌 [Detect] 图片 {img.id} 连接算法服务失败: {conn_err}")

        # 🔥 连接错误也可以重试
        if img.retry_count < img.max_retries:
            img.retry_count += 1
            img.detect_status = "pending"  # 重新入队
            print(f"🔄 [Detect] 图片 {img.id} 连接失败，重试 ({img.retry_count}/{img.max_retries})")
        else:
            img.detect_status = "failed"
            print(f"❌ [Detect] 图片 {img.id} 连接失败，达到最大重试次数 ({img.max_retries})")
        safe_save(img)

    except Exception as e:
        # 其他异常：打印完整堆栈
        print(f"❌ [Detect] 图片 {img.id} 检测异常: {e}")
        import traceback
        traceback.print_exc()

        # 🔥 其他错误不重试，直接标记失败
        img.detect_status = "failed"
        safe_save(img)

# 全局导入
from concurrent.futures import ThreadPoolExecutor

# 🔥 全局单例线程池：所有任务共享这 1 个 worker
# 这样可以控制并发总量，且不会因为创建销毁线程池浪费资源
# ⭐ 修正：将并发数从 4 改为 1。
# 原因：后台算法使用 GLM-4V 等大模型，通常不支持高并发（显存限制）。
# 如果并发发送，会导致请求在算法服务端排队，从而导致 HTTP 响应时间虚高（包含排队时间），甚至触发超时。
# 改为串行处理后，日志记录的耗时将更接近真实的算法推理耗时。
GLOBAL_DETECT_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="GlobalDetect")

def auto_trigger_detect(task):
    """
    [异步非阻塞版] 自动检测调度器
    只负责将任务分发给全局线程池，不再同步等待结果。
    """
    # 🔥 使用任务级别的锁防止并发启动 (依然需要，防止重复提交同一批图片)
    lock_key = f"detect_task_{task.id}"
    from django.core.cache import cache

    # 尝试获取锁（过期时间 10 分钟）
    lock_acquired = cache.add(lock_key, True, timeout=600)

    if not lock_acquired:
        print(f"⏸️  [Detect] 任务 {task.id} 已有检测分发正在进行，跳过")
        return

    try:
        # 🔥 查询所有 pending 状态的图片
        images = task.images.filter(detect_status="pending").order_by("id")
        
        # 如果没有图片，直接退出
        if not images.exists():
            return

        # 🔥 原子操作：立即将这些图片标记为 processing
        # 这样 Poller 下一轮扫描时就不会再扫到它们了
        updated_count = images.update(detect_status="processing")
        
        if updated_count > 0:
            print(f"🚀 [Async] 任务 {task.id} 将 {updated_count} 张图片提交至后台队列...")
            
            # 重新获取对象（为了拿到更新后的状态，虽非必须但更稳妥）
            # 注意：这里不能复用上面的 images queryset，因为 update 后缓存可能失效
            processing_images = task.images.filter(detect_status="processing")
            
            # 🔥 仅首次更新任务开始时间
            if not task.started_at:
                task.started_at = django_timezone.now()
                safe_save(task, update_fields=['started_at'])

            detect_url = getattr(settings, "FASTAPI_DETECT_URL", "http://localhost:8088/detect")
            algo_type = normalize_detect_code(task.detect_category.code) if task.detect_category else "rail"

            # 🔥 核心修改：异步提交任务，不等待 (No Wait)
            # 💡 优化：由于我们改为了单线程执行 (max_workers=1)，
            # 如果一次性提交太多任务，后面的任务会排队很久，导致“排队时间”很长。
            # 但这对系统稳定性有好处，避免了并发请求压垮算法服务。
            # 只要 Poller 是单线程触发的，这里其实就是顺序入队。
            current_batch_submit_time = time.time()
            for img in processing_images:
                # submit 是非阻塞的，瞬间完成
                GLOBAL_DETECT_EXECUTOR.submit(
                    process_single_image, 
                    img, 
                    task, 
                    detect_url, 
                    algo_type,
                    current_batch_submit_time  # 所有图片共用同一个批次提交时间
                )
            
            print(f"✅ [Async] 任务 {task.id} 分发完成，后台正在处理中...")

    finally:
        # 🔥 释放锁
        # 注意：这里的锁只锁“分发过程”，不锁“执行过程”
        # 所以分发完立刻释放，允许 Poller 继续扫描该任务的新图片
        cache.delete(lock_key)


# ======================================================================
# 2. 后台轮询 Worker (替代原来的 Webhook)
# ======================================================================
# views.py
# views.py 需要引入 timedelta 处理时区
from datetime import timedelta

# views.py
import time
from datetime import timedelta
from django.utils import timezone as django_timezone


# ... (fetch_dji_task_info 函数保持之前的写法) ...
# views.py

# 确保顶部有这些导入
import requests
from django.conf import settings


def fetch_dji_task_info(task_uuid):
    """
    [新增工具函数] 请求司空接口获取任务详情
    (自动获取配置版)
    """
    target_uuid = "edd3e043-2cd4-4774-9132-f449d0524c4a"

    if task_uuid == target_uuid:
        print(f"🕵️ [Debug] 触发强制测试模式: {task_uuid}")
        return {
            "name": "强制测试任务",
            "status": "executing",  # <--- 关键！骗系统说它还在执行
            "wayline_uuid": "test-wayline-uuid",
            "expected": 10,
            "uploaded": 1,
        }

    try:
        # 自动从 Settings 获取配置 (解决硬编码问题)
        headers, base_url = WaylineFingerprintManager.get_api_headers_and_host()
    except Exception as e:
        print(f"⚠️ [API Config] 无法获取 API 配置: {e}")
        return None

    try:
        # 拼接 API 地址
        url = f"{base_url}/openapi/v0.1/flight-task/{task_uuid}"

        # 调试打印 (可选)
        # print(f"📡 [API] 请求 URL: {url}")

        resp = requests.get(url, headers=headers, timeout=5)

        if resp.status_code == 200:
            res_json = resp.json()
            if res_json.get("code") == 0:
                data = res_json.get("data", {})
                folder_info = data.get("folder_info", {})

                return {
                    "name": data.get("name"),
                    "status": data.get("status"),
                    "wayline_uuid": data.get("wayline_uuid"),
                    "expected": folder_info.get("expected_file_count", 0),
                    "uploaded": folder_info.get("uploaded_file_count", 0),
                }
            else:
                print(f"⚠️ [API] 业务报错: {res_json}")
        else:
            print(f"❌ [API] 请求失败: {resp.status_code} (请检查 Token 或 ProjectUUID)")

    except Exception as e:
        print(f"❌ [API Error] 连接异常: {e}")

    return None


def fetch_dji_task_media(task_uuid):
    """
    [新增工具函数] 调用司空接口获取任务的媒体资源列表
    返回图片列表: [{"uuid": "...", "name": "...", "file_type": "image", ...}, ...]
    """
    base_url = "http://192.168.10.2:30812"
    
    headers = {
        "X-User-Token": "eyJhbGciOiJIUzUxMiIsImNyaXQiOlsidHlwIiwiYWxnIiwia2lkIl0sImtpZCI6IjU3YmQyNmEwLTYyMDktNGE5My1hNjg4LWY4NzUyYmU1ZDE5MSIsInR5cCI6IkpXVCJ9.eyJhY2NvdW50IjoiIiwiZXhwIjoyMDgyMzQxNjQzLCJuYmYiOjE3NjY4MDg4NDMsIm9yZ2FuaXphdGlvbl91dWlkIjoiZmJjNGJkY2YtMmFjMC00MmI2LTliMWItZTFkMWUyMDE0NjgyIiwicHJvamVjdF91dWlkIjoiIiwic3ViIjoiZmgyIiwidXNlcl9pZCI6IjE3NjY4MDgyNjMxNjYwODAxNjcifQ.Szehmvkjcmub5csnJQj1r0KjhdXCtkzCSzi31GDjigRn3B7V7TYVqDJ1QJ9-BxkvAl2eSoY3JXaH34ccHW-eaA",
        "X-Project-Uuid": "d41dc59e-cab1-4798-8f91-faca84ff4cb7",
        "Content-Type": "application/json"
    }
    
    try:
        url = f"{base_url}/openapi/v0.1/flight-task/{task_uuid}/media"
        print(f"📡 [API] 获取任务图片: {url}")
        
        # 支持分页获取
        all_media = []
        page = 1
        page_size = 50
        
        while True:
            params = {"page": page, "page_size": page_size}
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("code") == 0:
                    data = res_json.get("data", {})
                    media_list = data.get("list", [])
                    
                    if not media_list:
                        break
                    
                    all_media.extend(media_list)
                    
                    # 如果返回的数量少于 page_size，说明已经是最后一页
                    if len(media_list) < page_size:
                        break
                    
                    page += 1
                else:
                    print(f"⚠️ [API] 获取图片列表失败: {res_json}")
                    break
            else:
                print(f"❌ [API] HTTP {resp.status_code}")
                break
        
        print(f"✅ [API] 获取到 {len(all_media)} 张图片")
        return all_media
        
    except Exception as e:
        print(f"❌ [API Error] 获取图片列表异常: {e}")
        return []
def minio_poller_worker():
    """
    [最终优化版] 智能任务扫描
    逻辑：扫描 MinIO -> 自动建任务 -> 调接口补全信息 -> 持续检测 -> 超时判断结束
    """
    print("🕵️ [Poller] 智能扫描已启动 (支持断点续飞+自动重开+固定命名文件夹)...")
    import re  # 🔥 移到函数开头，避免循环中重复import
    s3 = get_minio_client()
    bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "dji")

    # 🔥 定义静默超时时间 (覆盖无人机充电时间 30-40 分钟)
    # 只有超过 45 分钟没有新图，且司空说结束了，我们才真的结束
    SILENCE_TIMEOUT_MINUTES = getattr(settings, 'TASK_SILENCE_TIMEOUT_MINUTES', 45)

    # 🔥 定义检测类型映射
    DETECT_TYPE_MAPPING = {
        '铁路': 'rail',
        '接触网': 'contactline',
        '桥梁': 'bridge',
        '保护区': 'protected_area'
    }

    # 🔥 固定命名文件夹超时时间
    FIXED_FOLDER_TIMEOUT = 10

    # 🔥 固定命名文件夹匹配正则
    FIXED_FOLDER_PATTERN = re.compile(r'^(\d{8})(铁路|接触网|桥梁|保护区)$')

    while True:
        try:
            # 1. 扫描 MinIO 发现 Task UUID 和它的 真实路径前缀
            found_tasks = {}  # {uuid: full_prefix_path}

            # 🔥 新增：扫描固定命名格式的文件夹
            found_fixed_folders = {}  # {folder_name: full_prefix_path}

            paginator = s3.get_paginator('list_objects_v2')

            # 尝试扫描 fh_sync/ 下的所有内容
            for page in paginator.paginate(Bucket=bucket_name, Prefix="fh_sync/"):
                if "Contents" not in page: continue
                for obj in page["Contents"]:
                    key = obj["Key"]

                    # 🔥 核心修复：动态解析路径
                    # 只要路径里包含 /media/，就自动识别上一级和下一级
                    if "/media/" in key:
                        parts = key.split("/")
                        try:
                            # 找到 media 所在的位置
                            idx = parts.index("media")
                            # media 的下一级就是 UUID
                            if len(parts) > idx + 1:
                                uuid_val = parts[idx + 1]

                                # 构造该UUID对应的【真实】完整前缀路径
                                # 例如: fh_sync/20251231/media/edd3e.../
                                prefix_path = "/".join(parts[:idx + 2]) + "/"

                                # 存入字典
                                found_tasks[uuid_val] = prefix_path
                        except:
                            pass

                    # 🔥 新增：扫描固定命名格式的文件夹
                    # 格式: YYYYMMDD + 检测类型，例如 20260113桥梁
                    # 路径格式: fh_sync/media/YYYYMMDD检测类型/...
                    if "/media/" in key:
                        parts = key.split("/")
                        try:
                            idx = parts.index("media")
                            if len(parts) > idx + 1:
                                folder_name = parts[idx + 1]

                                # 检查是否符合固定命名格式: 8位数字 + 检测类型
                                match = FIXED_FOLDER_PATTERN.match(folder_name)

                                if match:
                                    date_str = match.group(1)  # 20260113
                                    detect_type_cn = match.group(2)  # 桥梁

                                    # 构造完整前缀路径
                                    prefix_path = "/".join(parts[:idx + 2]) + "/"

                                    # 存入字典
                                    found_fixed_folders[folder_name] = {
                                        'prefix': prefix_path,
                                        'date': date_str,
                                        'detect_type_cn': detect_type_cn,
                                        'detect_type': DETECT_TYPE_MAPPING.get(detect_type_cn, 'rail')
                                    }
                        except:
                            pass

            # 2. 遍历处理每个 UUID
            for uuid_val, prefix_path in found_tasks.items():

                # 如果这个 UUID 已存在，就获取；不存在就创建
                task, created = InspectTask.objects.get_or_create(
                    dji_task_uuid=uuid_val,
                    defaults={
                        "external_task_id": uuid_val,
                        "bucket": bucket_name,
                        "detect_status": "processing",
                        "prefix_list": [prefix_path]  # 🔥 这里不再是 generic，而是真实的 prefix_path
                    }
                )

                # 补丁：如果任务早已存在但 prefix_list 是错的/空的，自动修正它
                if not task.prefix_list or (task.prefix_list and task.prefix_list[0] != prefix_path):
                    print(f"🔧 [Fix Path] 修正任务 {uuid_val} 路径: {prefix_path}")
                    task.prefix_list = [prefix_path]
                    safe_save(task)

                # =========================================================
                # B. 调用司空接口 (仅在必要时)
                # =========================================================
                # 如果是新任务，或者状态不是 terminated，或者超过5分钟没更新，就去调一次接口
                should_fetch_api = False
                if created:
                    should_fetch_api = True
                elif task.dji_status != "terminated":
                    should_fetch_api = True

                if should_fetch_api:
                    api_data = fetch_dji_task_info(uuid_val)  # 🔥 修复：使用 uuid_val 而不是 uuid
                    if api_data:
                        task.dji_task_name = api_data["name"]
                        task.dji_status = api_data["status"]
                        # 更新 external_task_id 为中文名，方便看
                        if created and api_data["name"]:
                            task.external_task_id = api_data["name"]
                        safe_save(task)
                        print(f"🔄 [API Sync] 任务 {task.external_task_id} 状态更新: {task.dji_status}")

                # =========================================================
                # C. 同步图片 + 自动重开逻辑 (Auto Re-open)
                # =========================================================
                # 调用 sync_images_core，它会返回新增图片数量
                new_images_count = sync_images_core(task)

                if new_images_count > 0:
                    current_time = django_timezone.now()

                    # 🔥 关键：有新图，更新“最后活跃时间”
                    task.last_image_uploaded_at = current_time

                    # 🔥 关键：如果任务之前已经 Done 了，现在又有新图，强制“复活”
                    if task.detect_status == "done":
                        print(f"🚀 [Re-open] 任务 {task.external_task_id} 收到新图，重新标记为处理中...")
                        task.detect_status = "processing"

                    safe_save(task)
                    print(f"📸 [Poller] 任务 {task.external_task_id} 同步了 {new_images_count} 张新图")

                # 🔥 新增：检查是否有待检测图片（不管是否有新图）
                pending_count = InspectImage.objects.filter(
                    inspect_task=task,
                    detect_status='pending'
                ).count()
                
                if pending_count > 0:
                    # 🔥 防止重复启动：检查是否已有检测线程在运行
                    processing_count = InspectImage.objects.filter(
                        inspect_task=task,
                        detect_status='processing'
                    ).count()
                    
                    if processing_count == 0:  # 没有正在处理的图片
                        print(f"🚀 [Poller] 任务 {task.external_task_id} 有 {pending_count} 张待检测图片，触发检测...")
                        # 触发算法检测
                        threading.Thread(target=auto_trigger_detect, args=(task,)).start()
                    else:
                        print(f"⏳ [Poller] 任务 {task.external_task_id} 有 {processing_count} 张图片正在检测中，跳过重复启动")

                # =========================================================
                # D. 判断任务结束 (超时判定)
                # =========================================================
                # 修改：不再依赖 dji_status == "terminated"，因为无人机换电也会导致 terminated
                # 改为纯静默时间判断
                if task.detect_status == "processing":

                    # 检查静默时间
                    if task.last_image_uploaded_at:
                        time_since_last = django_timezone.now() - task.last_image_uploaded_at
                        minutes_silent = time_since_last.total_seconds() / 60

                        if minutes_silent > SILENCE_TIMEOUT_MINUTES:
                            # 确实很久没动静了，且司空也说结束了 -> 标记完成
                            print(
                                f"✅ [Task Done] 任务 {task.external_task_id} 已静默 {int(minutes_silent)} 分钟，自动结束。")
                            task.detect_status = "done"
                            task.finished_at = django_timezone.now()
                            safe_save(task)
                        else:
                            # 还在静默期内（可能在换电池）
                            # print(f"⏳ [Waiting] 任务 {task.external_task_id} 等待中 (静默 {int(minutes_silent)}m / {SILENCE_TIMEOUT_MINUTES}m)")
                            pass
                else:
                    # 极端情况：还没收到过图片，先不管
                    pass

            # =========================================================
            # 🔥 新增：处理固定命名格式的文件夹
            # =========================================================
            for folder_name, folder_info in found_fixed_folders.items():
                prefix_path = folder_info['prefix']
                date_str = folder_info['date']  # 20260113
                detect_type_cn = folder_info['detect_type_cn']  # 桥梁
                detect_type = folder_info['detect_type']  # bridge

                # 构造任务ID
                task_id = f"{date_str}{detect_type_cn}"

                # 检查是否已存在该任务
                task, created = InspectTask.objects.get_or_create(
                    external_task_id=task_id,
                    defaults={
                        "bucket": bucket_name,
                        "detect_status": "processing",
                        "prefix_list": [prefix_path],
                        "dji_task_name": f"{detect_type_cn}检测({date_str})"
                    }
                )

                if created:
                    print(f"📁 [Fixed Folder] 发现新文件夹并创建任务: {folder_name}, 路径: {prefix_path}")
                    print(f"✅ [Fixed Folder] 任务ID: {task_id}")

                    # 🔥 创建父任务 (与其他任务保持一致的命名规则)
                    parent_task_id = f"{date_str}巡检任务"
                    parent_task, _ = InspectTask.objects.get_or_create(
                        external_task_id=parent_task_id,
                        defaults={
                            "detect_status": "pending",
                            "bucket": bucket_name,
                            "prefix_list": []
                        }
                    )

                    # 设置父任务关系
                    task.parent_task = parent_task
                    safe_save(task)

                    print(f"📂 [Fixed Folder] 父任务: {parent_task_id}")

                # 获取或创建对应的检测类型
                category, _ = AlarmCategory.objects.get_or_create(
                    code=detect_type.upper(),
                    defaults={
                        "name": detect_type_cn,
                        "match_keyword": detect_type_cn
                    }
                )

                # 更新任务的检测类型
                if task.detect_category != category:
                    task.detect_category = category
                    safe_save(task)

                # 同步图片
                new_images_count = sync_images_core(task)

                if new_images_count > 0:
                    current_time = django_timezone.now()
                    task.last_image_uploaded_at = current_time

                    # 如果任务之前已经 Done 了，现在又有新图，强制"复活"
                    if task.detect_status == "done":
                        print(f"🚀 [Re-open Fixed] 任务 {task_id} 收到新图，重新标记为处理中...")
                        task.detect_status = "processing"

                    safe_save(task)
                    print(f"📸 [Fixed Folder] 任务 {task_id} 同步了 {new_images_count} 张新图")

                # 检查是否有待检测图片
                pending_count = InspectImage.objects.filter(
                    inspect_task=task,
                    detect_status='pending'
                ).count()

                if pending_count > 0:
                    # 防止重复启动检测
                    processing_count = InspectImage.objects.filter(
                        inspect_task=task,
                        detect_status='processing'
                    ).count()

                    if processing_count == 0:
                        print(f"🚀 [Fixed Folder] 任务 {task_id} 有 {pending_count} 张待检测图片，触发检测...")
                        threading.Thread(target=auto_trigger_detect, args=(task,)).start()
                    else:
                        print(f"⏳ [Fixed Folder] 任务 {task_id} 有 {processing_count} 张图片正在检测中，跳过重复启动")

                # 判断任务结束 (固定命名文件夹使用更短的超时时间，因为通常是手动上传)
                if task.detect_status == "processing":
                    if task.last_image_uploaded_at:
                        time_since_last = django_timezone.now() - task.last_image_uploaded_at
                        minutes_silent = time_since_last.total_seconds() / 60

                        # 固定命名文件夹超时时间设置为10分钟
                        FIXED_FOLDER_TIMEOUT = 10

                        if minutes_silent > FIXED_FOLDER_TIMEOUT:
                            print(f"✅ [Fixed Folder Done] 任务 {task_id} 已静默 {int(minutes_silent)} 分钟，自动结束。")
                            task.detect_status = "done"
                            task.finished_at = django_timezone.now()
                            safe_save(task)

        except Exception as e:
            print(f"❌ Poller Error: {e}")
            # import traceback
            # traceback.print_exc()

        time.sleep(5)
def minio_poller_worker1231():
    """
    [最终命名优化版] 智能指纹扫描线程
    命名规则：
      - 父任务：yyyyMMdd巡检任务
      - 子任务：yyyyMMdd航线名检测类型
    """
    print("🕵️ [Poller] 智能命名扫描已启动...")
    time.sleep(5)

    # 启动指纹同步
    threading.Thread(target=WaylineFingerprintManager.sync_by_keywords).start()

    s3 = get_minio_client()
    bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "dji")

    while True:
        try:
            paginator = s3.get_paginator('list_objects_v2')

            # 存储结构变更为: { "子文件夹前缀": { "key": "采样图", "date": "yyyyMMdd" } }
            found_sub_folders = {}

            for page in paginator.paginate(Bucket=bucket_name, Prefix="fh_sync/"):
                if "Contents" not in page: continue
                for obj in page["Contents"]:
                    key = obj["Key"]
                    if not key.lower().endswith((".jpg", ".jpeg")): continue

                    # 🔥 跳过实时直播任务（保护区检测等），避免在轮播检测界面显示
                    if "/live/" in key:
                        continue

                    parts = key.split('/')
                    if "media" in parts:
                        idx = parts.index("media")
                        if len(parts) > idx + 2:
                            folder_prefix = "/".join(parts[:idx + 2]) + "/"

                            # 如果这个文件夹还没记录，或者记录了但现在有了更新的日期，就更新它
                            if folder_prefix not in found_sub_folders:
                                # 获取文件时间 (UTC) 并转为北京时间 (UTC+8)
                                last_modified = obj['LastModified']
                                cn_time = last_modified + timedelta(hours=8)
                                date_str = cn_time.strftime("%Y%m%d")

                                found_sub_folders[folder_prefix] = {
                                    "key": key,
                                    "date": date_str
                                }

            # 处理发现的文件夹
            for folder_prefix, info in found_sub_folders.items():
                sample_key = info["key"]
                date_str = info["date"]

                # 原始的文件夹 UUID (2c8a...) 仍然需要用来判断是否处理过，防止重复读取指纹
                # 但不再用作 TaskID
                folder_native_uuid = folder_prefix.strip('/').split('/')[-1]

                # 暂时用 prefix_list 来判断是否处理过该物理路径
                # (注意：因为我们要改 ID 格式，所以不能简单用 external_task_id 查重了)
                # 我们可以查询 prefix_list 包含此路径的任务
                # JSONField 查询：prefix_list__contains=folder_prefix
                # ✅ 修正代码：使用 icontains 进行字符串匹配
                # 这会将数据库里的 JSON 视为字符串 "['path/to/a', 'path/to/b']"，然后查找子串
                if InspectTask.objects.filter(prefix_list__icontains=folder_prefix).exists():
                    continue

                print(f"🔍 [New Folder] 发现新上传: {folder_prefix} ({date_str})，正在识别...")

                uuid = get_image_action_uuid_from_minio(s3, bucket_name, sample_key)
                if not uuid: continue

                # 查指纹
                # ✅ SQLite 兼容版 (把 JSON 当字符串查)
                fingerprint = WaylineFingerprint.objects.filter(action_uuids__icontains=uuid).first()
                if not fingerprint:
                    # 兼容遍历
                    for fp in WaylineFingerprint.objects.all():
                        if uuid in fp.action_uuids:
                            fingerprint = fp
                            break

                if fingerprint:
                    # 获取名称信息
                    wayline_name = fingerprint.wayline.name
                    cat_name = fingerprint.detect_category.name if fingerprint.detect_category else "通用检测"

                    print(f"✅ [Match] 命中: {wayline_name} -> {cat_name}")

                    # =========================================================
                    # 1. 创建父任务 (虚拟任务)
                    # 命名格式: "20251221巡检任务"
                    # =========================================================
                    parent_task_id = f"{date_str}巡检任务"

                    parent_task, _ = InspectTask.objects.get_or_create(
                        external_task_id=parent_task_id,
                        defaults={
                            "detect_status": "pending",  # 🔥 父任务初始状态改为pending
                            "bucket": bucket_name,
                            "prefix_list": []  # 父任务没有具体路径
                        }
                    )

                    # =========================================================
                    # 2. 创建子任务 (真实任务)
                    # 命名格式: "20251221工业大学桥梁检测"
                    # =========================================================
                    sub_task_id = f"{date_str}{wayline_name}{cat_name}"

                    # 创建任务（不自动检测，等待前端用户选择）
                    new_task = InspectTask.objects.create(
                        parent_task=parent_task,
                        external_task_id=sub_task_id,  # 🔥 这里变成了中文名称
                        bucket=bucket_name,
                        prefix_list=[folder_prefix],  # 🔥 真实的 MinIO 路径存在这里
                        wayline=fingerprint.wayline,
                        detect_category=fingerprint.detect_category,
                        detect_status="pending"  # 🔥 改为 pending，等待用户手动启动
                    )
                    print(f"🎉 任务创建: [{parent_task_id}] -> [{sub_task_id}] (等待用户启动)")

            # 常规图片同步逻辑（只同步 scanning 状态的任务）
            active_tasks = InspectTask.objects.filter(detect_status='scanning')
            for task in active_tasks:
                # 🔥 1. 先同步新图片
                new_cnt = sync_images_core(task)
                if new_cnt > 0:
                    print(f"📥 [Poller] 任务 {task.external_task_id} 同步了 {new_cnt} 张新图")

                # 🔥 2. 无论是否有新图，都检查是否有待检测的图片
                pending_cnt = InspectImage.objects.filter(
                    inspect_task=task,
                    detect_status='pending'
                ).count()

                if pending_cnt > 0:
                    print(f"🔄 [Poller] 任务 {task.external_task_id} 有 {pending_cnt} 张待检测图片，触发检测...")
                    threading.Thread(target=auto_trigger_detect, args=(task,)).start()
                else:
                    # 🔥 3. 没有pending图片，检查是否还有processing状态的图片
                    processing_cnt = InspectImage.objects.filter(
                        inspect_task=task,
                        detect_status='processing'
                    ).count()

                    if processing_cnt == 0:
                        # 所有图片都处理完了，且没有新图
                        print(f"✅ [Poller] 任务 {task.external_task_id} 所有图片处理完毕，标记为完成")
                        task.detect_status = 'done'
                        task.finished_at = django_timezone.now()
                        safe_save(task, update_fields=['detect_status', 'finished_at'])

                        # 🔥 新增：检查父任务，如果所有子任务都完成了，同步父任务状态
                        if task.parent_task:
                            parent = task.parent_task
                            all_sub_done = not parent.sub_tasks.exclude(detect_status='done').exists()
                            if all_sub_done and parent.detect_status != 'done':
                                parent.detect_status = 'done'
                                parent.finished_at = django_timezone.now()
                                safe_save(parent, update_fields=['detect_status', 'finished_at'])
                                print(f"🎉 [Poller] 父任务 {parent.external_task_id} 所有子任务完成，标记为完成")
                    else:
                        print(f"⏳ [Poller] 任务 {task.external_task_id} 还有 {processing_cnt} 张图片正在检测中...")

        except Exception as e:
            print(f"❌ Poller Loop Error: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(5)

def process_video_task(task, s3_client, bucket, video_key):
    """
    [视频处理] 视频切片并回传 MinIO
    """
    if not cv2:
        print("❌ [Video] OpenCV 未安装，跳过视频处理")
        return

    # 🔥 申请信号量，控制并发数
    print(f"⏳ [Video] 正在排队等待处理资源: {video_key} (当前并发限制: 2)")
    with VIDEO_PROCESS_SEMAPHORE:
        print(f"🎬 [Video] 开始处理视频: {video_key}")
        
        # 下载视频
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
            try:
                s3_client.download_fileobj(bucket, video_key, tmp_video)
                tmp_path = tmp_video.name
            except Exception as e:
                print(f"❌ [Video] 下载失败: {e}")
                return

    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            print("❌ [Video] 无法打开视频")
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        INTERVAL = 2  # 每2秒一帧
        frame_interval = int(fps * INTERVAL)
        
        folder_prefix = os.path.dirname(video_key) + "/"
        video_name = os.path.splitext(os.path.basename(video_key))[0]
        
        saved_count = 0
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            if frame_idx % frame_interval == 0:
                success, buf = cv2.imencode(".jpg", frame)
                if success:
                    fname = f"{video_name}_frame_{saved_count:04d}.jpg"
                    key = folder_prefix + fname
                    try:
                        put_object_bytes(
                            s3_client,
                            bucket,
                            key,
                            buf.tobytes(),
                            content_type="image/jpeg"
                        )
                        saved_count += 1
                    except Exception as e:
                        print(f"❌ [Video Upload Error] 切片上传失败! Bucket={bucket}, Key={key}, Error={e}")
            frame_idx += 1
            
        cap.release()
        print(f"✅ [Video] 切片完成: {saved_count} 张")
        
        # 立即触发同步和检测
        if saved_count > 0:
            new_cnt = sync_images_core(task)
            if new_cnt > 0:
                threading.Thread(target=auto_trigger_detect, args=(task,)).start()

    except Exception as e:
        print(f"❌ [Video] 处理异常: {e}")
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def minio_poller_worker2():
    """
    [最终适配版] 智能指纹扫描线程
    逻辑：扫描 .../media/{SubFolder}/ 下的图片 -> 识别指纹 -> 创建父子任务
    结构：Job(父) -> SubFolder(子, 绑定类型)
    
    [用户需求增强]:
    1. 考虑到无人机换电（约40分钟），任务超时判断需延长（建议60分钟）。
    2. 支持“断点续飞”：即使任务已存在，如果发现新图片（增量），也要自动触发检测。
    3. 新文件夹自动创建并触发检测。
    """
    print("🕵️ [Poller] 深度指纹扫描已启动 (智能增量版)...")
    time.sleep(5)

    # 1. 启动时同步一次指纹库
    threading.Thread(target=WaylineFingerprintManager.sync_by_keywords).start()

    s3 = get_minio_client()
    bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "dji")
    
    # 🔴 关键配置：静默超时时间（分钟）
    # 设为 60 分钟，覆盖无人机换电时间（通常30-40分钟）
    SILENCE_TIMEOUT_MINUTES = 60 

    from django.db import close_old_connections

    while True:
        # 修复长时间运行导致的数据库连接丢失问题
        close_old_connections()
        
        try:
            # =========================================================
            # 第一步：发现 MinIO 里的所有“子任务文件夹”
            # =========================================================
            paginator = s3.get_paginator('list_objects_v2')
            
            # 数据结构升级：
            # found_sub_folders[folder_prefix] = {
            #     'sample_key': '...',  # 用于创建任务时的采样（优先存图片）
            #     'video_keys': []      # 存储该文件夹下所有的 .mp4 文件
            # }
            found_sub_folders = {}
            
            # 调试：打印扫描配置
            # print(f"🔍 [Poller] Scanning Bucket: {bucket_name}, Prefix: fh_sync/")

            # 注意：如果 Bucket 巨大，这里可能需要优化，但在独立部署组件中通常可接受
            for page in paginator.paginate(Bucket=bucket_name, Prefix="fh_sync/"):
                if "Contents" not in page: continue
                for obj in page["Contents"]:
                    key = obj["Key"]
                    # 🔥 支持视频文件 (.mp4) 和图片
                    is_video = key.lower().endswith(".mp4")
                    is_image = key.lower().endswith((".jpg", ".jpeg"))
                    
                    if not (is_image or is_video): continue

                    parts = key.split('/')
                    if "media" in parts:
                        idx = parts.index("media")
                        if len(parts) > idx + 2:
                            folder_prefix = "/".join(parts[:idx + 2]) + "/"
                            
                            # 初始化字典结构
                            if folder_prefix not in found_sub_folders:
                                found_sub_folders[folder_prefix] = {
                                    'sample_key': key,
                                    'video_keys': []
                                }
                            
                            # 获取当前记录
                            entry = found_sub_folders[folder_prefix]
                            
                            # 1. 收集视频列表
                            if is_video:
                                entry['video_keys'].append(key)
                            
                            # 2. 优化 sample_key：优先保留图片作为采样（用于指纹识别），
                            #    如果当前是视频，遇到图片则替换。
                            current_sample = entry['sample_key']
                            if current_sample.lower().endswith(".mp4") and is_image:
                                entry['sample_key'] = key

            # =========================================================
            # 第二步：处理每一个发现的子文件夹 (创建或更新)
            # =========================================================
            for folder_prefix, entry in found_sub_folders.items():
                sample_key = entry['sample_key']
                video_keys = entry['video_keys']
                
                folder_uuid = folder_prefix.strip('/').split('/')[-1]
                
                # 尝试获取已存在的任务
                # 🔥 修正：优先获取子任务（实际执行检测的任务），排除父任务容器
                # 因为父任务和子任务可能拥有相同的 external_task_id
                existing_task = InspectTask.objects.filter(
                    external_task_id=folder_uuid, 
                    parent_task__isnull=False
                ).first()
                
                # 如果没找到子任务，再尝试找一下是不是只有单层任务（兼容旧数据）
                if not existing_task:
                     existing_task = InspectTask.objects.filter(
                        external_task_id=folder_uuid
                     ).exclude(dji_task_name__contains="巡检作业").first()
                
                target_task = None
                
                # A. 如果任务不存在 -> 创建流程
                if not existing_task:
                    print(f"🔍 [New Sub-Task] 发现新文件夹: {folder_uuid}，正在采样识别...")
                    
                    # 尝试从本地 FlightTaskInfo 获取任务详情 (补充 SN 等信息)
                    local_task_info = FlightTaskInfo.objects.filter(task_uuid=folder_uuid).first()
                    local_sn = local_task_info.sn if local_task_info else None
                    local_name = local_task_info.name if local_task_info else None
                    
                    is_video_task = sample_key.lower().endswith(".mp4")
                    uuid = None
                    fingerprint = None

                    if is_video_task:
                        print(f"🎥 [Video] 识别为视频任务: {sample_key} -> 自动归类为保护区")
                    else:
                        uuid = get_image_action_uuid_from_minio(s3, bucket_name, sample_key)
                        if not uuid:
                            print(f"⚠️ [Skip] 无法从 {sample_key} 提取 UUID")
                            continue

                    # SQLite 不支持 JSONField 的 contains 查找，直接遍历查找
                    fingerprint = None
                    if uuid:  # 🔥 只有提取到 UUID (即图片任务) 才去查指纹
                        all_fps = WaylineFingerprint.objects.all()
                        print(f"🔍 [Debug] 正在数据库中查找 UUID: {uuid}")
                        print(f"🔍 [Debug] 数据库中共有 {all_fps.count()} 个指纹记录")
                        
                        for fp in all_fps:
                            if fp.action_uuids and uuid in fp.action_uuids:
                                fingerprint = fp
                                print(f"✅ [Debug] 找到匹配! 航线: {fp.wayline.name}, ID: {fp.id}")
                                break
                        
                        if not fingerprint:
                            print(f"❌ [Debug] 遍历了所有指纹，未找到匹配的 UUID: {uuid}")
                            if all_fps.exists() and all_fps.first().action_uuids:
                                 sample_uuid = all_fps.first().action_uuids[0]
                                 print(f"ℹ️ [Debug] 数据库指纹示例 UUID (第一个): {sample_uuid}")
                                 print(f"ℹ️ [Debug] 待匹配 UUID: {uuid}")
                                 print(f"ℹ️ [Debug] 长度比较 - 库中: {len(sample_uuid)}, 提取: {len(uuid)}")
                    
                    if not fingerprint:
                        print(f"⚠️ [Skip] UUID {uuid} 未匹配到任何航线指纹，将创建【未分类】任务以便测试")
                        
                        # 🔥 [修复] 尝试调用司空接口查询航线 (重点解决保护区/视频任务关联航线问题)
                        target_wayline = None
                        target_category = None
                        
                        try:
                            # 尝试获取任务详情
                            api_data = fetch_dji_task_info(folder_uuid)
                            if api_data:
                                # 1. 尝试关联航线
                                wl_uuid = api_data.get("wayline_uuid")
                                if wl_uuid:
                                    # 注意：这里需要确保 Wayline 和 AlarmCategory 已引入
                                    target_wayline = Wayline.objects.filter(wayline_id=wl_uuid).first()
                                    
                                    if target_wayline:
                                        print(f"🔗 [API Match] 通过接口关联到航线: {target_wayline.name}")
                                        
                                        # 2. 自动推断分类 (如果有航线类型)
                                        if target_wayline.detect_type:
                                            cat_code = normalize_detect_code(target_wayline.detect_type)
                                            target_category = AlarmCategory.objects.filter(code__iexact=cat_code).first()
                                            if target_category:
                                                print(f"🏷️ [API Match] 自动归类: {target_category.name}")
                                                
                        except Exception as e:
                            print(f"⚠️ [API Fail] 查询任务详情失败: {e}")

                        # 降级策略：创建未分类任务
                        job_id = folder_uuid
                        date_str = django_timezone.now().strftime('%Y-%m-%d')
                        
                        # 优先使用本地记录的任务名
                        base_name = local_name if local_name else f"未分类任务-{job_id[-6:]}"
                        if is_video_task:
                            base_name = local_name if local_name else f"视频任务-{job_id[-6:]}"

                        # 🔥 修改：使用与其他检测类型统一的虚拟父任务命名规则
                        # 格式: "20250110巡检任务" (与保护区检测一致)
                        today_str = django_timezone.now().strftime('%Y%m%d')
                        parent_task_id = f"{today_str}巡检任务"

                        # 创建/获取统一的父任务
                        parent_task, created = InspectTask.objects.get_or_create(
                            external_task_id=parent_task_id,  # 🔥 使用统一的虚拟父任务ID
                            defaults={
                                "detect_status": "pending",
                                "bucket": bucket_name,
                                "prefix_list": []
                            }
                        )

                        # 确定分类
                        # 视频任务默认逻辑：如果没有从 API 查到分类，则默认为保护区
                        if is_video_task and not target_category:
                            target_category = AlarmCategory.objects.filter(code='protected_area').first()

                        # 创建子任务
                        child_name = f"{base_name} ({'保护区视频' if is_video_task else '未知航线'})"
                        target_task = InspectTask.objects.create(
                            parent_task=parent_task,
                            external_task_id=folder_uuid,
                            bucket=bucket_name,
                            prefix_list=[folder_prefix],
                            wayline=target_wayline,  # 🔥 使用 API 查到的航线
                            detect_category=target_category, # 🔥 使用 API 查到或默认的分类
                            detect_status="scanning",
                            last_image_uploaded_at=django_timezone.now(),
                            dji_task_uuid=folder_uuid,
                            dji_task_name=child_name,
                            device_sn=local_sn  # 🔥 填入SN
                        )
                        print(f"⚠️ 任务创建成功({'视频/保护区' if is_video_task else '未分类'}): {folder_uuid}")
                        
                        # 🔥 如果是视频任务，立即触发切片处理
                        if is_video_task:
                            # 遍历所有视频进行处理（支持单任务多视频）
                            for v_key in video_keys:
                                v_name = os.path.splitext(os.path.basename(v_key))[0]
                                # 精准去重：检查该视频是否已产生切片
                                if not InspectImage.objects.filter(
                                    inspect_task=target_task, 
                                    object_key__contains=v_name
                                ).exists():
                                    print(f"🎬 [Video] 触发新视频处理: {v_key}")
                                    threading.Thread(target=process_video_task, args=(target_task, s3, bucket_name, v_key)).start()
                    
                    else:
                        # 原有匹配逻辑
                        # 🔥 自动修正逻辑：如果指纹类型是 unknown，但航线名包含关键字，则自动更新分类
                        correct_category = None
                        if fingerprint.detect_category and fingerprint.detect_category.code == 'unknown':
                            wayline_name = fingerprint.wayline.name
                            if "轨道" in wayline_name or "rail" in wayline_name.lower():
                                correct_category = AlarmCategory.objects.filter(code='rail').first()
                            elif "桥梁" in wayline_name or "bridge" in wayline_name.lower():
                                correct_category = AlarmCategory.objects.filter(code='bridge').first()
                            elif "接触网" in wayline_name or "contact" in wayline_name.lower():
                                correct_category = AlarmCategory.objects.filter(code='contactline').first()
                            elif "保护区" in wayline_name or "protected" in wayline_name.lower():
                                correct_category = AlarmCategory.objects.filter(code='protected_area').first()
                            
                            if correct_category:
                                print(f"🔧 [AutoFix] 自动修正指纹分类: {fingerprint.id} | {fingerprint.detect_category.name} -> {correct_category.name}")
                                fingerprint.detect_category = correct_category
                                fingerprint.save()
                        
                        cat_name = fingerprint.detect_category.name if fingerprint.detect_category else "无类型"
                        print(f"✅ [Match] 命中航线: {fingerprint.wayline.name} -> 类型: {cat_name}")

                        # 修正：media 下一级的文件夹名就是任务 ID (job_id)
                        # 例如: .../media/edd3e043.../ -> job_id = edd3e043...
                        job_id = folder_uuid

                        # 尝试调用司空接口获取真实任务信息（用于后续状态跟踪）
                        dji_task_info = fetch_dji_task_info(job_id)
                        dji_status_val = dji_task_info.get("status", "unknown") if dji_task_info else "unknown"

                        # 🔥 修改：使用与其他检测类型统一的虚拟父任务命名规则
                        # 格式: "20250110巡检任务" (与保护区检测一致)
                        today_str = django_timezone.now().strftime('%Y%m%d')
                        parent_task_id = f"{today_str}巡检任务"

                        parent_task, created = InspectTask.objects.get_or_create(
                            external_task_id=parent_task_id,  # 🔥 使用统一的虚拟父任务ID
                            defaults={
                                "detect_status": "pending",
                                "bucket": bucket_name,
                                "prefix_list": []  # 父任务没有具体路径
                            }
                        )

                        # 🔥 新增：如果司空API返回了任务信息，更新父任务状态
                        if dji_task_info and not created:
                            if parent_task.dji_status != dji_status_val:
                                parent_task.dji_status = dji_status_val
                                safe_save(parent_task, update_fields=['dji_status'])

                        # 🔥 修复：构造子任务名称时使用 today_str（已定义）而不是未定义的 date_str
                        # 构造子任务名称：日期 + 航线名 + 检测类型
                        child_name = f"{today_str} {fingerprint.wayline.name} {cat_name}"

                        # 创建子任务
                        target_task = InspectTask.objects.create(
                            parent_task=parent_task,
                            external_task_id=folder_uuid,
                            bucket=bucket_name,
                            prefix_list=[folder_prefix],
                            wayline=fingerprint.wayline,
                            detect_category=fingerprint.detect_category,
                            detect_status="scanning", # 初始设为 scanning
                            last_image_uploaded_at=django_timezone.now(), # 初始化时间
                            dji_task_uuid=folder_uuid,    # 🔥 核心修正：UUID 归属于子任务
                            dji_task_name=child_name,      # 填入构造的名称
                            device_sn=local_sn             # 🔥 填入SN
                        )
                        print(f"🎉 任务创建成功: {folder_uuid} (父: {job_id})")
                
                # B. 如果任务已存在 -> 准备检查增量
                else:
                    target_task = existing_task
                    
                    # 🔥 [自动修复] 检查视频任务的切片情况（支持多视频）
                    if video_keys:
                        for v_key in video_keys:
                            v_name = os.path.splitext(os.path.basename(v_key))[0]
                            
                            # 1. 检查该特定视频是否已有切片
                            has_slices = InspectImage.objects.filter(
                                inspect_task=target_task, 
                                object_key__contains=v_name
                            ).exists()
                            
                            if not has_slices:
                                # 使用缓存锁防止短时间内重复触发
                                from django.core.cache import cache
                                
                                # 1. 频率控制 (5分钟一次) - 针对特定视频文件
                                # 使用文件名的 hash 或直接用 key 作为锁的一部分
                                import hashlib
                                v_hash = hashlib.md5(v_key.encode()).hexdigest()
                                lock_key = f"retry_video_{target_task.id}_{v_hash}"
                                
                                # 2. 次数控制 (最多3次)
                                count_key = f"retry_count_video_{target_task.id}_{v_hash}"
                                current_count = cache.get(count_key, 0)
                                
                                if current_count >= 3:
                                    pass
                                else:
                                    if cache.add(lock_key, True, timeout=300): 
                                        print(f"♻️ [Retry] 发现视频 {v_name} 无切片，尝试触发处理 ({current_count + 1}/3)...")
                                        cache.set(count_key, current_count + 1, timeout=86400)
                                        threading.Thread(target=process_video_task, args=(target_task, s3, bucket_name, v_key)).start()
                                    else:
                                        pass

                
                # =========================================================
                # 第三步：对该任务执行“图片同步” (无论新旧)
                # =========================================================
                if target_task:
                    # 回填分类/航线：如果任务缺少 detect_category，尝试用图片UUID匹配指纹
                    if not target_task.detect_category:
                        try:
                            uuid = get_image_action_uuid_from_minio(s3, bucket_name, sample_key)
                            fp = None
                            if uuid:
                                fp = WaylineFingerprint.objects.filter(action_uuids__icontains=uuid).first()
                                if not fp:
                                    for _fp in WaylineFingerprint.objects.all():
                                        if uuid in _fp.action_uuids:
                                            fp = _fp
                                            break
                            if fp:
                                target_task.wayline = fp.wayline
                                target_task.detect_category = fp.detect_category
                                safe_save(target_task, update_fields=['wayline', 'detect_category'])
                                print(f"🔧 [Backfill] 任务 {target_task.external_task_id} 已回填分类与航线: {fp.detect_category.name if fp.detect_category else '无'} -> {fp.wayline.name}")
                        except Exception as _e:
                            print(f"⚠️ [Backfill] 无法回填分类: {_e}")
                    
                    # 只有当状态不是 'failed' 时才去同步
                    if target_task.detect_status == 'failed':
                        continue

                    # 执行同步，返回新增图片数
                    new_images_count = sync_images_core(target_task)
                    
                    if new_images_count > 0:
                        print(f"📥 [Increment] 任务 {target_task.external_task_id} 发现 {new_images_count} 张新图")
                        
                        # 1. 更新活跃时间
                        target_task.last_image_uploaded_at = django_timezone.now()
                        
                        # 2. 如果任务之前是 'done' 或 'pending'，现在有了新图，必须切回 'scanning'
                        #    这样才能让后面的超时判断逻辑继续工作
                        if target_task.detect_status in ['done', 'pending']:
                             print(f"♻️ [Re-Activate] 任务 {target_task.external_task_id} 被重新激活 (Done -> Scanning)")
                             target_task.detect_status = 'scanning'
                        
                        safe_save(target_task)

                        # 3. 自动触发检测 (对新图片)
                        #    注意：auto_trigger_detect 内部会找 pending 的图片进行检测
                        threading.Thread(target=auto_trigger_detect, args=(target_task,)).start()
                    else:
                        # 🔥 修复：即使没有新图片，也要检查是否有挂起的任务需要处理
                        # 避免因为 sync_images_core 返回 0 而导致之前的 pending 图片卡死
                        pending_count = target_task.images.filter(detect_status="pending").count()
                        if pending_count > 0:
                             # 为了避免日志刷屏，可以只在真的触发时打印
                             threading.Thread(target=auto_trigger_detect, args=(target_task,)).start()

            # =========================================================
            # 第四步：全局超时判断 (处理无人机充电/结束的情况)
            # =========================================================
            # 遍历所有处于 'scanning' 或 'processing' 的任务
            active_tasks = InspectTask.objects.filter(detect_status__in=['scanning', 'processing'])
            
            for task in active_tasks:
                # 必须有 last_image_uploaded_at 才能判断超时
                if not task.last_image_uploaded_at:
                    continue
                
                # 计算静默时间
                time_since_last = django_timezone.now() - task.last_image_uploaded_at
                minutes_silent = time_since_last.total_seconds() / 60
                
                # 如果超过阈值 (60分钟) -> 标记为 Done
                if minutes_silent > SILENCE_TIMEOUT_MINUTES:
                    # 再次确认：是否真的没有 pending 图片了？
                    pending_imgs = InspectImage.objects.filter(inspect_task=task, detect_status__in=['pending', 'processing']).count()
                    
                    if pending_imgs == 0:
                        print(f"🏁 [Timeout Done] 任务 {task.external_task_id} 已静默 {int(minutes_silent)} 分钟 (> {SILENCE_TIMEOUT_MINUTES}m)，自动结束。")
                        task.detect_status = 'done'
                        task.finished_at = django_timezone.now()
                        safe_save(task)
                        
                        # 同步父任务状态 (如果所有子任务都完了，父任务也完了)
                        if task.parent_task:
                            all_subs = task.parent_task.sub_tasks.all()
                            if not all_subs.filter(detect_status__in=['scanning', 'processing', 'pending']).exists():
                                task.parent_task.detect_status = 'done'
                                task.parent_task.finished_at = django_timezone.now()
                                safe_save(task.parent_task)
                                print(f"🏁 [Parent Done] 父任务 {task.parent_task.external_task_id} 也已全部完成。")
                    else:
                        # 还有图片没跑完，虽然没新图了，但还得等算法跑完
                        # print(f"⏳ [Waiting] 任务 {task.external_task_id} 静默中，但仍有 {pending_imgs} 张图片在处理...")
                        pass

        except Exception as e:
            print(f"❌ Poller Loop Error: {e}")
            # import traceback
            # traceback.print_exc()

        time.sleep(5)
def minio_poller_worker1():
    """
    [新版] 智能扫描线程 (含自动结束逻辑)
    """
    print("🕵️ [Poller] 智能扫描线程已启动，等待指令...")
    time.sleep(3)

    s3 = get_minio_client()

    while True:
        try:
            # 只查询状态为 'scanning' 的任务
            active_tasks = InspectTask.objects.filter(detect_status='scanning')

            if not active_tasks.exists():
                time.sleep(2)
                continue

            for task in active_tasks:
                # 1. 确定扫描路径
                if task.prefix_list and len(task.prefix_list) > 0:
                    prefix = task.prefix_list[0]
                else:
                    # 如果没有 prefix_list，暂时跳过并在日志中警告（避免无限循环报错）
                    # print(f"⚠️ 任务 {task.id} 没有路径前缀，跳过扫描...")
                    continue

                bucket_name = getattr(task, 'bucket', 'dji')

                # 2. 扫描 MinIO
                paginator = s3.get_paginator('list_objects_v2')
                new_images_count = 0

                # 加上异常捕获，防止某个任务路径不对卡死整个线程
                try:
                    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                        if "Contents" not in page: continue

                        for obj in page["Contents"]:
                            key = obj["Key"]
                            if not key.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")): continue
                            filename = key.split('/')[-1]
                            if filename.startswith("detected_"): continue

                            # 检查去重
                            if not InspectImage.objects.filter(inspect_task=task, object_key=key).exists():
                                InspectImage.objects.create(
                                    inspect_task=task,
                                    wayline=task.wayline,
                                    object_key=key,
                                    detect_status="pending"
                                )
                                print(f"✨ [New Image] 发现新图片: {filename}")
                                new_images_count += 1
                except Exception as s3_err:
                    print(f"⚠️ 扫描任务 {task.id} 路径异常: {s3_err}")

                # 3. 分支判断
                if new_images_count > 0:
                    # A. 有新图 -> 触发检测 -> 检测函数会在跑完后把状态改为 done
                    print(f"🚀 [Poller] 任务 {task.external_task_id} 发现 {new_images_count} 张新图，触发检测...")
                    threading.Thread(target=auto_trigger_detect, args=(task,)).start()
                else:
                    # B. 无新图 -> 检查是否还有残留的 pending/processing 图片
                    # 如果所有图片都跑完了，且刚才没扫到新图，说明任务彻底结束了
                    unfinished_cnt = InspectImage.objects.filter(
                        inspect_task=task,
                        detect_status__in=['pending', 'processing']
                    ).count()

                    if unfinished_cnt == 0:
                        print(f"✅ [Poller] 任务 {task.external_task_id} 已无新图且处理完毕，自动结束扫描。")
                        task.detect_status = 'done'
                        task.save(update_fields=['detect_status'])

            time.sleep(3)

        except Exception as e:
            print(f"❌ [Poller Error] 轮询出错: {e}")
            time.sleep(5)
#threading.Thread(target=minio_poller_worker, daemon=True).start()
# ======================================================================
# 3. ViewSets (融合了你的旧逻辑和我的新逻辑)
# ======================================================================

class AlarmCategoryViewSet(viewsets.ModelViewSet):
    """告警类型管理（兼配置中心）"""
    queryset = AlarmCategory.objects.all()
    serializer_class = AlarmCategorySerializer
    filter_backends = [SearchFilter]
    search_fields = ['name', 'code', 'match_keyword']


class InspectTaskViewSet(viewsets.ModelViewSet):
    """巡检任务管理 (全自动)"""
    queryset = InspectTask.objects.all().order_by("-created_at")
    serializer_class = InspectTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["external_task_id", "wayline__name"]
    ordering_fields = ["created_at", "started_at", "finished_at"]
    filterset_fields = {
        'detect_status': ['exact', 'in'],
        'parent_task': ['exact', 'isnull'],
        'wayline': ['exact', 'isnull'],
        'detect_category': ['exact', 'isnull'],
    }

    def list(self, request, *args, **kwargs):
        """
        任务列表接口
        - 默认返回所有父任务（虚拟聚合任务）
        - 支持 ?parent_task=null 只返回父任务
        - 支持 ?parent_task__isnull=false 只返回子任务
        - 支持 ?parent_task__isnull=true 只返回父任务
        """
        # 获取基础查询集
        queryset = self.get_queryset()

        # 检查是否有 parent_task__isnull 参数
        parent_task_isnull = request.query_params.get('parent_task__isnull', None)

        if parent_task_isnull == 'true' or parent_task_isnull == 'True':
            # 只返回父任务（没有 parent_task 的任务）
            queryset = queryset.filter(parent_task__isnull=True).annotate(
                sub_task_count=Count('sub_tasks')
            ).filter(sub_task_count__gt=0)
        elif parent_task_isnull == 'false' or parent_task_isnull == 'False':
            # 只返回子任务
            queryset = queryset.filter(parent_task__isnull=False)
        else:
            # 检查旧的 parent_task 参数（向后兼容）
            show_parent_only = request.query_params.get('parent_task', None)

            if show_parent_only == 'null' or show_parent_only == '':
                # 只返回父任务（没有 parent_task 的任务）
                queryset = queryset.filter(parent_task__isnull=True).annotate(
                    sub_task_count=Count('sub_tasks')
                ).filter(sub_task_count__gt=0)
            elif show_parent_only == 'false' or show_parent_only == '0':
                # 只返回子任务
                queryset = queryset.filter(parent_task__isnull=False)

        # 🔥 关键修复: 应用其他过滤器(搜索、排序等)
        queryset = self.filter_queryset(queryset)

        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def sync_images(self, request, pk=None):
        task = self.get_object()
        cnt = sync_images_core(task)
        return Response({"detail": f"Synced {cnt} images."})

    @action(detail=True, methods=["post"])
    def trigger_detect(self, request, pk=None):
        task = self.get_object()
        if task.detect_status == "processing":
            return Response({"detail": "Processing..."}, status=400)
        threading.Thread(target=auto_trigger_detect, args=(task,)).start()
        return Response({"detail": "Detection started."})

    @action(detail=True, methods=["get"])
    def images(self, request, pk=None):
        """返回某个巡检任务下的所有图片及检测状态，按时间顺序排序"""
        task = self.get_object()
        # 🔥 优化：使用 select_related 预加载关联字段，避免 N+1
        # 虽然 inspect_task 已知，但 serializer 的 method field (get_signed_url) 可能仍需访问 task 属性
        queryset = InspectImage.objects.filter(inspect_task=task).select_related('inspect_task', 'wayline').order_by("created_at", "id")
        # 🔥 优化：使用轻量级 Serializer，移除 inspect_task_details
        serializer = InspectImageListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def sub_tasks(self, request, pk=None):
        """返回某个父任务下面的所有子任务"""
        task = self.get_object()
        queryset = InspectTask.objects.filter(parent_task=task).order_by("created_at", "id")
        serializer = InspectTaskSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """启动巡检任务:将状态从pending改为scanning"""
        task = self.get_object()
        if task.detect_status not in ["pending"]:
            return Response({"detail": f"当前状态[{task.detect_status}]不可启动,仅pending状态可启动"}, status=400)

        task.detect_status = "scanning"
        task.started_at = django_timezone.now()
        safe_save(task, update_fields=["detect_status", "started_at"])

        # 🔥 新增：如果是子任务，同步父任务状态
        if task.parent_task and task.parent_task.detect_status == "pending":
            task.parent_task.detect_status = "scanning"
            task.parent_task.started_at = django_timezone.now()
            safe_save(task.parent_task, update_fields=["detect_status", "started_at"])
            print(f"🚀 [Start] 父任务 {task.parent_task.external_task_id} 状态同步为 scanning")

        return Response(InspectTaskSerializer(task).data)

    @action(detail=True, methods=["delete", "post"])
    def force_delete(self, request, pk=None):
        """
        强制删除任务及其所有关联数据
        删除范围:
        1. InspectTask (任务本身)
        2. InspectImage (任务的所有图片)
        3. Alarm (任务产生的所有告警)
        4. 如果是子任务,需要考虑父任务状态
        """
        task = self.get_object()

        # 统计即将删除的数据
        image_count = InspectImage.objects.filter(inspect_task=task).count()
        alarm_count = Alarm.objects.filter(wayline=task.wayline).count()

        print(f"🗑️ [Force Delete] 准备删除任务: {task.external_task_id}")
        print(f"   - 图片: {image_count} 张")
        print(f"   - 告警: {alarm_count} 条")

        # 1. 删除所有关联的 InspectImage
        InspectImage.objects.filter(inspect_task=task).delete()
        print(f"✅ 已删除 {image_count} 张图片记录")

        # 2. 删除所有关联的 Alarm (通过 wayline 和 source_image 关联)
        Alarm.objects.filter(source_image__inspect_task=task).delete()
        print(f"✅ 已删除相关告警记录")

        # 3. 记录父任务信息(如果是子任务)
        parent_task = task.parent_task
        external_id = task.external_task_id

        # 4. 删除任务本身
        task.delete()
        print(f"✅ 已删除任务: {external_id}")

        # 5. 如果是子任务,检查父任务是否还有其他子任务
        if parent_task:
            remaining_subs = parent_task.sub_tasks.count()
            if remaining_subs == 0:
                # 父任务没有子任务了,也删除父任务
                parent_task.delete()
                print(f"✅ 已删除空父任务: {parent_task.external_task_id}")
            else:
                print(f"ℹ️ 父任务还有 {remaining_subs} 个子任务,保留父任务")

        return Response({
            "detail": f"任务 {external_id} 及其所有关联数据已强制删除",
            "deleted_images": image_count,
            "deleted_alarms": alarm_count
        }, status=200)


class AlarmViewSet(viewsets.ModelViewSet):
    """保留你原本的 Search Fields"""
    queryset = Alarm.objects.select_related('category', 'wayline').all()
    serializer_class = AlarmSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AlarmFilter
    search_fields = [
        'content', 'handler', 'category__name', 'category__code',
        'wayline__wayline_id', 'wayline__name', 'specific_data'
    ]
    ordering_fields = ['created_at', 'updated_at', 'status']


# views.py

class WaylineViewSet(viewsets.ModelViewSet):
    queryset = Wayline.objects.all()
    serializer_class = WaylineSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['wayline_id', 'name', 'description', 'created_by']
    ordering_fields = ['created_at', 'updated_at', 'status', 'name']
    ordering = ['-created_at']

    filterset_fields = {
        'wayline_id': ['exact', 'icontains'],
        'name': ['exact', 'icontains'],
        'status': ['exact'],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        detect_type = self.request.query_params.get('detect_type')
        if not detect_type:
            return qs
        norm = normalize_detect_code(detect_type)
        variants_map = {
            "rail": {"rail", "track"},
            "contactline": {"contactline", "catenary", "overhead", "insulator", "pole"},
            "bridge": {"bridge"},
            "protected_area": {"protected_area", "protection_zone", "protection_area"},
        }
        variants = variants_map.get(norm, {norm})
        return qs.filter(detect_type__in=list(variants))

    @action(detail=False, methods=['get'], url_path='tree')
    def tree(self, request):
        type_labels = {
            "rail": "轨道",
            "contactline": "接触网",
            "bridge": "桥梁",
            "protected_area": "保护区",
        }
        variants_map = {
            "rail": {"rail", "track"},
            "contactline": {"contactline", "catenary", "overhead", "insulator", "pole"},
            "bridge": {"bridge"},
            "protected_area": {"protected_area", "protection_zone", "protection_area"},
        }
        groups = {k: {"type": k, "label": v, "items": []} for k, v in type_labels.items()}
        waylines = Wayline.objects.all().only("id", "wayline_id", "name", "detect_type")
        for w in waylines:
            dt = (w.detect_type or "").lower()
            bucket_type = None
            for k, variants in variants_map.items():
                if dt in variants:
                    bucket_type = k
                    break
            if not bucket_type:
                bucket_type = "rail"
            recent = InspectTask.objects.filter(wayline=w).order_by(
                "-last_image_uploaded_at", "-finished_at", "-started_at", "-created_at"
            ).first()
            recent_time = None
            recent_id = None
            if recent:
                recent_time = recent.last_image_uploaded_at or recent.finished_at or recent.started_at or recent.created_at
                recent_id = recent.id
            groups[bucket_type]["items"].append({
                "id": w.id,
                "wayline_id": w.wayline_id,
                "name": w.name,
                "recent_task_time": recent_time.isoformat() if recent_time else None,
                "recent_task_id": recent_id,
            })
        for g in groups.values():
            g["items"].sort(key=lambda x: (x["recent_task_time"] is not None, x["recent_task_time"] or ""), reverse=True)
            g["count"] = len(g["items"])
        ordered = ["rail", "contactline", "bridge", "protected_area"]
        data = [groups[t] for t in ordered]
        return Response({"groups": data})
    
    @action(detail=True, methods=['get'], url_path='action-details')
    def action_details(self, request, pk=None):
        """
        获取指定航线的指纹动作详情及UUID集合
        返回字段：
          - wayline: { id, wayline_id, name, detect_type }
          - detect_category: { id, name, code } 或 null
          - action_uuids: [uuid...]
          - action_details: [{ uuid, lat, lon, height, ellipsoid_height, gimbal_yaw, aircraft_heading }, ...]
        """
        try:
            wayline = Wayline.objects.filter(pk=pk).first()
            if not wayline:
                return Response({"detail": "Wayline not found"}, status=404)
            fp = WaylineFingerprint.objects.filter(wayline=wayline).first()
            detect_category = None
            if fp and fp.detect_category:
                detect_category = {
                    "id": fp.detect_category.id,
                    "name": fp.detect_category.name,
                    "code": fp.detect_category.code
                }
            data = {
                "wayline": {
                    "id": wayline.id,
                    "wayline_id": wayline.wayline_id,
                    "name": wayline.name,
                    "detect_type": wayline.detect_type
                },
                "detect_category": detect_category,
                "action_uuids": fp.action_uuids if fp and fp.action_uuids else [],
                "action_details": fp.action_details if fp and fp.action_details else []
            }
            return Response(data)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)
    # =========================================================
    # 🆕 新增接口: 同步航线数据 (POST /waylines/sync_data/)
    # =========================================================
    @action(detail=False, methods=['post'])
    def sync_data(self, request):
        """
        [硬编码配置版] 主动调用司空 API 同步航线列表到本地数据库
        """
        print("🔄 [Wayline Sync] 开始同步航线列表 (使用 Settings 配置)...")

        try:
            # 1. 使用 WaylineFingerprintManager 统一获取 Header 和 Base URL
            headers, base_url = WaylineFingerprintManager.get_api_headers_and_host()

            # 2. 发起请求
            # API 路径: /openapi/v0.1/wayline
            api_url = f"{base_url}/openapi/v0.1/wayline"

            # 假设你的接口支持分页，我们可以先传大一点的 page_size
            params = {
                "page": 1,
                "page_size": 100
            }

            print(f"   -> 请求接口: {api_url}")
            resp = requests.get(api_url, headers=headers, params=params, timeout=10)

            if resp.status_code != 200:
                print(f"❌ 同步失败: {resp.status_code} - {resp.text}")
                return Response({"code": 502, "msg": f"司空接口报错: {resp.status_code}"}, status=502)

            # 3. 解析数据
            resp_json = resp.json()

            # 根据你提供的 JSON 结构，数据可能在 data.list 里，或者 data 本身就是 list
            # 结构通常是: { "code": 0, "data": { "list": [...] } }
            raw_data = resp_json.get("data", {})
            wayline_list = []

            if isinstance(raw_data, dict):
                wayline_list = raw_data.get("list", [])
            elif isinstance(raw_data, list):
                wayline_list = raw_data

            print(f"   -> 获取到 {len(wayline_list)} 条航线数据")

            # 4. 入库更新
            updated_count = 0
            for item in wayline_list:
                w_id = item.get("id")
                w_name = item.get("name")

                # 你的 JSON 里有 "update_time": 1766109565421
                # 这是一个毫秒级时间戳，如果需要存，可以转一下，或者直接存到 description 里备注
                raw_update_time = item.get("update_time")

                if not w_id: continue

                # 执行 Update 或 Create
                Wayline.objects.update_or_create(
                    wayline_id=w_id,
                    defaults={
                        "name": w_name,
                        "description": f"Synced from API. UpdateTime: {raw_update_time}",
                        "status": "ACTIVE"
                    }
                )
                updated_count += 1

            print(f"✅ [Wayline Sync] 同步完成，已更新 {updated_count} 条记录")
            return Response({"code": 200, "msg": "同步成功", "count": updated_count})

        except Exception as e:
            print(f"❌ 同步异常: {e}")
            import traceback
            traceback.print_exc()
            return Response({"code": 500, "msg": str(e)}, status=500)


class WaylineImageViewSet(viewsets.ModelViewSet):
    queryset = WaylineImage.objects.select_related('wayline', 'alarm').all()
    serializer_class = WaylineImageSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = WaylineImageFilter
    search_fields = ['title', 'description', 'wayline__name', 'wayline__wayline_id']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            token_serializer = TokenSerializer(token)
            return Response(token_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        try:
            request.user.auth_token.delete()
            return Response({'message': '注销成功'}, status=status.HTTP_200_OK)
        except:
            return Response({'message': '注销失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """保留你原本的 destroy 保护逻辑"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['username', 'profile__name']
    ordering_fields = ['id', 'username', 'date_joined']
    ordering = ['-date_joined']

    def get_permissions(self):
        if self.action in ['create', 'list', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsSystemAdmin()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def destroy(self, request, *args, **kwargs):
        """防止删除admin用户"""
        user = self.get_object()
        if user.username == 'admin':
            return Response({'message': '不能删除管理员账户'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class ComponentConfigViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]

    def get_object(self):
        obj, _ = ComponentConfig.objects.get_or_create(id=1)
        return obj

    def list(self, request):
        obj = self.get_object()
        serializer = ComponentConfigSerializer(obj)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        obj = self.get_object()
        serializer = ComponentConfigSerializer(obj)
        return Response(serializer.data)

    def update(self, request, pk=None):
        obj = self.get_object()
        serializer = ComponentConfigSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        obj = self.get_object()
        serializer = ComponentConfigSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MediaLibraryViewSet(viewsets.ViewSet):
    """保留你原本的 List 和 Serve 逻辑"""
    permission_classes = [AllowAny]
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpeg', '.mpg'}

    def get_permissions(self):
        if self.action == 'config' and getattr(self, 'request', None):
            if self.request.method in ['PUT', 'PATCH', 'POST']:
                return [permissions.IsAuthenticated(), IsSystemAdmin()]
        return [AllowAny()]

    def get_config(self):
        obj, _ = MediaFolderConfig.objects.get_or_create(id=1)
        return obj

    def list(self, request):
        config = self.get_config()
        folder_path = config.folder_path

        if not folder_path:
            return Response({'folder_path': folder_path, 'files': [], 'message': '媒体文件夹未配置'}, status=400)
        if not os.path.isdir(folder_path):
            return Response({'folder_path': folder_path, 'files': [], 'message': '路径不存在'}, status=400)

        files = []
        try:
            for entry in sorted(Path(folder_path).iterdir()):
                if not entry.is_file(): continue
                suffix = entry.suffix.lower()
                if suffix in self.image_extensions:
                    media_type = 'image'
                elif suffix in self.video_extensions:
                    media_type = 'video'
                else:
                    continue

                stat = entry.stat()
                rel_path = entry.relative_to(folder_path).as_posix()
                file_url = reverse('media-library-serve', kwargs={'path': rel_path}, request=request)
                files.append({
                    'name': entry.name,
                    'path': rel_path,
                    'type': media_type,
                    'url': file_url,
                    'size': stat.st_size,
                    'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        except OSError:
            return Response({'folder_path': folder_path, 'files': [], 'message': '读取失败'}, status=400)
        return Response({'folder_path': folder_path, 'files': files})

    @action(detail=False, methods=['get', 'put'], url_path='config')
    def config(self, request):
        config = self.get_config()
        if request.method == 'GET':
            return Response(MediaFolderConfigSerializer(config).data)
        serializer = MediaFolderConfigSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            if serializer.validated_data.get('folder_path') and not os.path.isdir(
                    serializer.validated_data['folder_path']):
                return Response({'folder_path': ['路径不存在']}, status=400)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['get'], url_path='serve/(?P<path>.+)', permission_classes=[permissions.AllowAny])
    def serve(self, request, path=None):
        config = self.get_config()
        if not config.folder_path: raise Http404("未配置")
        try:
            full_path = safe_join(config.folder_path, path)
        except (SuspiciousFileOperation, ValueError):
            raise Http404("非法路径")
        if not full_path or not os.path.isfile(full_path): raise Http404("文件不存在")

        response = FileResponse(open(full_path, 'rb'))
        mime_type, _ = mimetypes.guess_type(full_path)
        if mime_type: response["Content-Type"] = mime_type
        return response

@csrf_exempt
def debug_opencv_status(request):
    """
    OpenCV 状态诊断接口
    GET /api/debug/opencv
    """
    import sys
    import pkg_resources
    
    status_info = {
        "cv2_installed": cv2 is not None,
        "cv2_version": getattr(cv2, "__version__", "N/A"),
        "import_error": CV2_IMPORT_ERROR,
        "python_version": sys.version,
        "python_path": sys.path,
        "installed_packages": [f"{p.key}=={p.version}" for p in pkg_resources.working_set if "opencv" in p.key]
    }
    
    return JsonResponse(status_info)


# ======================================================================
# 直播监听管理（保护区检测）
# ======================================================================

# 全局变量：存储正在运行的监听线程
live_monitor_threads = {}
# 格式: { "stream_id": { "thread": Thread对象, "stop_event": Event对象, "task": InspectTask对象 } }

# 🔥 新增：线程锁，防止并发启动同一个流的多个监听线程
live_monitor_lock = threading.Lock()


class LiveMonitorViewSet(viewsets.ViewSet):
    """
    直播监听控制接口（保护区检测）
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='start')
    def start_monitor(self, request):
        """
        启动直播监听
        POST /api/v1/live-monitor/start/
        Body: { "stream_id": "drone01", "interval": 3.0 }
        """
        stream_id = request.data.get('stream_id', 'drone01')
        interval = float(request.data.get('interval', 3.0))

        # 🔥 使用线程锁，防止并发启动多个线程
        with live_monitor_lock:
            # 在锁内再次检查（双重检查锁定模式）
            if stream_id in live_monitor_threads:
                return Response(
                    {"status": "error", "message": f"流 {stream_id} 的监听已在运行中"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                # 创建停止事件
                stop_event = threading.Event()

                # 🔥 关键修复：先记录线程信息，再启动线程
                # 这样即使线程立即失败，记录也存在，可以正常停止
                monitor_thread = threading.Thread(
                    target=self._run_monitor,
                    args=(stream_id, interval, stop_event),
                    daemon=True,
                    name=f"Monitor-{stream_id}"
                )

                # 🔥 在线程启动前就记录信息
                live_monitor_threads[stream_id] = {
                    "thread": monitor_thread,
                    "stop_event": stop_event,
                    "task": None,  # 初始为None，线程内会更新
                    "started_at": django_timezone.now().isoformat()
                }

                print(f"✅ [线程记录] Stream: {stream_id} | 已记录到 live_monitor_threads")

                # 启动线程
                monitor_thread.start()
                print(f"✅ [线程启动] Stream: {stream_id} | Thread: {monitor_thread.name}")

                return Response({
                    "status": "success",
                    "message": f"直播监听已启动: {stream_id}",
                    "stream_id": stream_id,
                    "interval": interval,
                    "task_id": None  # 任务ID会在首帧成功后创建
                })

            except Exception as e:
                print(f"❌ 启动监听失败: {e}")
                import traceback
                traceback.print_exc()

                # 🔥 失败时清理可能已创建的记录
                if stream_id in live_monitor_threads:
                    del live_monitor_threads[stream_id]
                    print(f"🧹 [清理记录] Stream: {stream_id} | 已从 live_monitor_threads 删除")

                return Response(
                    {"status": "error", "message": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    @action(detail=False, methods=['post'], url_path='stop')
    def stop_monitor(self, request):
        """
        停止直播监听
        POST /api/v1/live-monitor/stop/
        Body: { "stream_id": "drone01" }
        """
        stream_id = request.data.get('stream_id', 'drone01')

        print(f"\n{'='*60}")
        print(f"🔴 [停止请求] 收到停止监听请求: stream_id={stream_id}")
        print(f"🔴 [停止请求] 当前运行中的线程列表: {list(live_monitor_threads.keys())}")
        print(f"{'='*60}\n")

        # 🔥 使用线程锁，防止并发问题
        with live_monitor_lock:
            if stream_id not in live_monitor_threads:
                print(f"⚠️ [停止失败] stream_id={stream_id} 不在运行列表中")
                return Response(
                    {"status": "error", "message": f"流 {stream_id} 没有运行中的监听"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                # 发送停止信号
                monitor_info = live_monitor_threads[stream_id]

                print(f"🔍 [停止调试] 找到线程信息:")
                print(f"  - 线程对象: {monitor_info['thread']}")
                print(f"  - 线程名称: {monitor_info['thread'].name}")
                print(f"  - 线程是否存活: {monitor_info['thread'].is_alive()}")
                print(f"  - 停止事件: {monitor_info['stop_event']}")
                print(f"  - 停止事件状态(设置前): {monitor_info['stop_event'].is_set()}")

                # 🔥 设置停止信号
                monitor_info["stop_event"].set()
                print(f"🔴 [停止信号] 已设置停止事件")
                print(f"  - 停止事件状态(设置后): {monitor_info['stop_event'].is_set()}")

                # 🔥 修复：等待线程结束（最多10秒，确保当前截图完成）
                # 给足够时间让当前截图处理完并退出循环
                print(f"⏳ [等待线程] 开始等待线程结束（最多10秒）...")

                import time
                start_wait = time.time()
                monitor_info["thread"].join(timeout=10)
                wait_time = time.time() - start_wait

                print(f"⏳ [等待线程] 等待完成，耗时 {wait_time:.2f}秒")
                print(f"  - 线程是否还存活: {monitor_info['thread'].is_alive()}")

                if monitor_info['thread'].is_alive():
                    print(f"⚠️ [警告] 线程在10秒后仍在运行，可能是线程卡死或stop_event检查失败")

                # 🔥 修复：如果线程还在运行，强制更新任务状态
                if monitor_info["task"]:
                    task = InspectTask.objects.get(id=monitor_info["task"].id)
                    task.detect_status = "done"
                    task.finished_at = django_timezone.now()
                    task.save(update_fields=['detect_status', 'finished_at'])
                    print(f"✅ [停止完成] 任务 {task.external_task_id} 已标记为完成")

                # 移除记录（在锁内完成）
                del live_monitor_threads[stream_id]

                print(f"🛑 [监听停止] Stream: {stream_id}")
                print(f"🛑 [清理完成] 已从 live_monitor_threads 删除")
                print(f"🔍 [剩余线程] 当前运行中的线程: {list(live_monitor_threads.keys())}")
                print(f"{'='*60}\n")

                return Response({
                    "status": "success",
                    "message": f"直播监听已停止: {stream_id}"
                })

            except Exception as e:
                print(f"❌ 停止监听失败: {e}")
                import traceback
                traceback.print_exc()

                # 🔥 失败时也尝试清理记录
                if stream_id in live_monitor_threads:
                    del live_monitor_threads[stream_id]

                return Response(
                    {"status": "error", "message": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    @action(detail=False, methods=['get'], url_path='status')
    def get_status(self, request):
        """
        获取所有监听状态
        GET /api/v1/live-monitor/status/
        """
        stream_id = request.query_params.get('stream_id')

        if stream_id:
            # 查询单个流状态
            if stream_id in live_monitor_threads:
                info = live_monitor_threads[stream_id]
                return Response({
                    "stream_id": stream_id,
                    "is_running": True,
                    "started_at": info["started_at"],
                    "task_id": info["task"].id if info["task"] else None
                })
            else:
                return Response({
                    "stream_id": stream_id,
                    "is_running": False
                })
        else:
            # 查询所有流状态
            status_list = []
            for sid, info in live_monitor_threads.items():
                status_list.append({
                    "stream_id": sid,
                    "is_running": True,
                    "started_at": info["started_at"],
                    "task_id": info["task"].id if info["task"] else None
                })
            return Response({
                "monitors": status_list,
                "count": len(status_list)
            })

    def _run_monitor(self, stream_id, interval, stop_event):
        """
        监听主逻辑（在独立线程中运行）
        """
        # 配置区
        ZLM_API_HOST = "http://zlm:80"
        ZLM_SECRET = "123456"  # 🔥 修复：与docker-compose中ZLM配置一致
        bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "dji")

        print(f"🚀 [监听启动] Stream: {stream_id} | 等待首帧截图...")
        print(f"📡 [ZLM配置] {ZLM_API_HOST} | secret: {ZLM_SECRET[:8]}...")
        print(f"📦 [MinIO配置] bucket: {bucket_name}")

        # 🔥 新增：启动时测试MinIO连接
        try:
            s3 = get_minio_client()
            s3.head_bucket(Bucket=bucket_name)
            print(f"✅ [MinIO连接] 成功")
        except Exception as e:
            print(f"❌ [MinIO连接] 失败: {e}")
            return

        frame_count = 0
        current_task = None  # ⭐ 延迟创建任务

        # 用于标记是否已成功截取第一帧
        first_frame_captured = False

        # 🔥 新增：记录循环开始时间
        import time as time_module
        loop_count = 0

        print(f"🔄 [循环启动] Stream: {stream_id} | 开始进入主循环")

        # 循环抽帧（直到收到停止信号）
        from django.db import close_old_connections
        while not stop_event.is_set():
            close_old_connections()
            loop_count += 1
            loop_start_time = time_module.time()

            # 🔥 每10次循环打印一次状态
            if loop_count % 10 == 1:
                print(f"🔄 [循环状态] Stream: {stream_id} | 第{loop_count}次循环 | stop_event={stop_event.is_set()}")

            # 🔥 在每次循环开始都检查停止信号，确保快速响应
            if stop_event.is_set():
                print(f"🔴 [循环退出-1] Stream: {stream_id} | 在循环开始处检测到停止信号")
                break

            try:
                # 🔥 关键修复：在每次请求前检查停止信号
                if stop_event.is_set():
                    print(f"🔴 [循环退出-2] Stream: {stream_id} | 在请求前检测到停止信号")
                    break

                # 🔥 新增：打印请求开始时间
                request_start = time_module.time()
                if loop_count % 10 == 1:
                    print(f"📡 [请求开始] Stream: {stream_id} | 准备请求ZLM截图API")

                # 🔥 动态查找流信息 (App/Schema)
                media_list_api = f"{ZLM_API_HOST}/index/api/getMediaList"
                target_url = None
                
                # ⭐ 从 settings 获取映射配置
                
                # 确定要搜索的 ID 列表 (优先搜 SN，其次搜映射名)
                search_ids = [stream_id]
                
                # 使用 settings 中的配置进行映射
                dock_mapping = getattr(settings, 'DOCK_STREAM_MAPPING', {})
                if stream_id in dock_mapping:
                    search_ids.append(dock_mapping[stream_id])

                try:
                    media_resp = requests.get(media_list_api, params={"secret": ZLM_SECRET}, timeout=5)
                    if media_resp.status_code == 200:
                        media_data = media_resp.json()
                        if media_data.get('code') == 0:
                            for item in media_data.get('data', []):
                                # 检查当前流是否匹配任何一个搜索 ID
                                if item.get('stream') in search_ids:
                                    # 找到流，构建 URL
                                    app_name = item.get('app')
                                    real_stream_id = item.get('stream')
                                    target_url = f"rtmp://127.0.0.1:1935/{app_name}/{real_stream_id}"
                                    if loop_count % 10 == 1:
                                        print(f"✅ [流发现] 映射匹配: {stream_id} -> {real_stream_id}")
                                    break
                except Exception as e:
                    if loop_count % 10 == 1:
                        print(f"⚠️ [流查询失败] {e}")

                if not target_url:
                    if loop_count % 10 == 1:
                        print(f"⏳ [等待推流] 流 {stream_id} (或映射ID) 未在线...")
                    stop_event.wait(2.0)
                    continue

                snap_api = f"{ZLM_API_HOST}/index/api/getSnap"
                params = {
                    "secret": ZLM_SECRET,
                    "url": target_url,
                    "timeout_sec": 10,  # 🔥 ZLM服务器超时10秒(给足够时间截图)
                    "expire_sec": 1
                }

                # 🔥 requests超时设置为12秒
                resp = requests.get(snap_api, params=params, timeout=12)

                request_time = time_module.time() - request_start
                if loop_count % 10 == 1:
                    print(f"📡 [请求完成] Stream: {stream_id} | 请求耗时 {request_time:.2f}秒")

                # 🔥 在处理响应前再次检查停止信号
                if stop_event.is_set():
                    print(f"🔴 [循环退出-3] Stream: {stream_id} | 在响应后检测到停止信号")
                    break

                # 🔥 修复：检查HTTP状态码，避免失败时直接抛异常
                if resp.status_code != 200:
                    if not first_frame_captured:
                        print(f"⏳ [等待推流] HTTP {resp.status_code} - ZLM可能未准备好...")
                    # 🔥 关键修复：等待时也要检查停止信号，使用短间隔分段等待
                    for _ in range(int(interval)):  # 分成1秒的多次检查
                        if stop_event.is_set():
                            print(f"⚠️ [停止中断] 等待期间收到停止信号")
                            break
                        stop_event.wait(1)  # 每次只等1秒
                    continue

                # 🔥 修复：ZLM的getSnap API直接返回JPEG二进制数据，不是JSON
                # 检查响应是否为图片（通过Content-Type或JPEG魔数）
                content_type = resp.headers.get('Content-Type', '')
                if 'image' in content_type or resp.content[:4] == b'\xff\xd8\xff\xe0':  # JPEG魔数
                    # ✅ 成功获取到截图数据（直接从resp.content获取）

                    # ⭐ 第一次成功截图时，才创建任务
                    if not first_frame_captured:
                        print(f"✅ [首帧成功] 开始创建任务...")

                        # 🔥 修改：使用与其他检测类型统一的父任务命名规则
                        # 格式: "20250110巡检任务" (与其他检测类型一致)
                        today_str = datetime.now().strftime('%Y%m%d')
                        parent_task_id = f"{today_str}巡检任务"

                        parent_task, _ = InspectTask.objects.get_or_create(
                            external_task_id=parent_task_id,
                            defaults={
                                "detect_status": "pending",  # 🔥 改为pending，与其他任务一致
                                "bucket": bucket_name,
                                "prefix_list": []  # 父任务没有具体路径
                            }
                        )

                        # 创建/获取保护区分类
                        category, _ = AlarmCategory.objects.get_or_create(
                            code="protected_area",
                            defaults={"name": "保护区", "match_keyword": "保护区"}
                        )

                        # 🔥 修改：子任务命名与其他检测类型保持一致
                        # 格式: "20250110保护区检测直播_drone01_HHMMSS"
                        now_time = datetime.now().strftime('%H%M%S')
                        sub_task_id = f"{today_str}保护区检测直播_{stream_id}_{now_time}"
                        virtual_prefix = f"fh_sync/live/{today_str}巡检任务/{sub_task_id}/"

                        # 🔥 新增：设置dji_task_name为用户友好的任务名称
                        dji_task_name = f"保护区检测-{stream_id}"

                        current_task = InspectTask.objects.create(
                            parent_task=parent_task,
                            external_task_id=sub_task_id,
                            dji_task_name=dji_task_name,  # 🔥 新增：用户友好的任务名称
                            bucket=bucket_name,
                            prefix_list=[virtual_prefix],
                            detect_category=category,
                            detect_status="processing"  # 直播任务立即开始检测
                        )

                        # 更新全局线程记录（补充任务信息）
                        if stream_id in live_monitor_threads:
                            live_monitor_threads[stream_id]["task"] = current_task

                        print(f"📂 [任务创建] [{parent_task_id}] -> [{sub_task_id}]")
                        first_frame_captured = True

                    # 🔥 在上传前再次检查停止信号
                    if stop_event.is_set():
                        print(f"⚠️ [停止中断] 收到停止信号，放弃上传当前帧")
                        break

                    # 🔥 修复：直接使用resp.content，不需要再次下载
                    file_bytes = io.BytesIO(resp.content)
                    file_size = len(resp.content)
                    fname = f"frame_{datetime.now().strftime('%H%M%S_%f')}.jpg"
                    object_key = f"{current_task.prefix_list[0]}{fname}"

                    # 🔥 关键修复：上传前最后一次检查停止信号
                    if stop_event.is_set():
                        print(f"⚠️ [停止中断] 上传前收到停止信号")
                        break

                    # 上传到MinIO
                    s3.put_object(
                        Bucket=bucket_name,
                        Key=object_key,
                        Body=file_bytes,
                        ContentLength=file_size,
                        ContentType='image/jpeg'
                    )

                    # 🔥 [新增] 计算 GPS 坐标
                    gps_result = {}
                    try:
                        from datetime import timedelta
                        # 1. 获取当前 UTC 时间 (Django aware time)
                        # 注意：必须使用 django_timezone.now()，不能用 datetime.now()
                        capture_time = django_timezone.now()
                        
                        # 2. 修正延迟 (1.5s)
                        flight_time = capture_time - timedelta(seconds=1.5)
                        
                        # 3. 计算
                        gps_info = calculate_drone_gps(flight_time)
                        
                        if gps_info:
                            gps_result = {"gps": gps_info}
                            # 打印日志方便调试
                            lat_val = gps_info.get('lat', 0)
                            lon_val = gps_info.get('lon', 0)
                            print(f"📍 [GPS] 图片 {fname} 坐标计算成功: {gps_info.get('method')} ({lat_val:.6f}, {lon_val:.6f})")
                        else:
                            print(f"⚠️ [GPS] 未找到附近的飞行记录，跳过坐标计算 (Time: {flight_time})")
                            
                    except Exception as gps_err:
                        print(f"❌ [GPS] 计算流程异常: {gps_err}")
                        gps_result = {}

                    InspectImage.objects.create(
                        inspect_task=current_task,
                        object_key=object_key,
                        detect_status='pending',
                        wayline=current_task.wayline,
                        result=gps_result # 🔥 存入 result
                    )
                    frame_count += 1
                    loop_time = time_module.time() - loop_start_time
                    print(f"📸 [截图] {fname} (总计: {frame_count}) | 本次循环耗时 {loop_time:.2f}秒")

                    # 🔥 关键修复：触发检测前再次检查停止信号
                    if stop_event.is_set():
                        print(f"🔴 [循环退出-4] Stream: {stream_id} | 在触发检测前检测到停止信号")
                        break

                    # 异步触发检测
                    threading.Thread(target=auto_trigger_detect, args=(current_task,)).start()
                else:
                    # 流还没推上来，等待
                    if not first_frame_captured:
                        print(f"⏳ [等待推流] {stream_id}...")

            except requests.exceptions.Timeout as e:
                # 🔥 超时异常的特殊处理
                if not stop_event.is_set():
                    print(f"⏱️ [请求超时] ZLM截图超时(10秒)，可能是流未推流或ZLM负载高: {e}")
                    # 🔥 超时后不要立即重试，等待一段时间
                    for step in range(int(interval)):
                        if stop_event.is_set():
                            print(f"🔴 [循环退出-5a] Stream: {stream_id} | 超时等待期间收到停止信号")
                            break
                        stop_event.wait(1)
                    continue
                else:
                    print(f"🔴 [循环退出-5b] Stream: {stream_id} | 超时异常时检测到停止信号")
                    break
            except Exception as e:
                if not stop_event.is_set():
                    print(f"❌ 截图异常: {type(e).__name__}: {e}")
                else:
                    print(f"🔴 [循环退出-5] Stream: {stream_id} | 异常时检测到停止信号")
                    break

            # 🔥 关键修复：等待间隔时使用分段等待，每0.5秒检查一次停止信号
            # 这样可以更快响应停止操作，最多等待0.5秒就退出
            wait_steps = int(interval / 0.5)  # 将interval分成0.5秒的小段
            for step in range(wait_steps):
                if stop_event.is_set():
                    print(f"🔴 [循环退出-6] Stream: {stream_id} | 在等待间隔第{step+1}步时检测到停止信号")
                    break
                stop_event.wait(0.5)

        print(f"\n{'='*60}")
        print(f"🛑 [监听停止] Stream: {stream_id}")
        print(f"  - 总循环次数: {loop_count}")
        print(f"  - 总截取帧数: {frame_count}")
        print(f"  - 线程即将退出")
        print(f"{'='*60}\n")

        # 停止时更新任务状态
        if current_task:
            current_task.detect_status = "done"
            current_task.finished_at = django_timezone.now()
            current_task.save(update_fields=['detect_status', 'finished_at'])
            print(f"✅ [任务完成] {current_task.external_task_id}")


# ======================================================================
# 恢复 Webhook 相关全局变量
# ======================================================================
webhook_queue = Queue()
processed_event_ids = set()
try:
    from collections import deque
    webhook_recent = deque(maxlen=50)
except Exception:
    webhook_recent = []


# ... (保留 minio_poller_worker 和其他代码) ...

# ======================================================================
# 恢复 WebhookTestViewSet
# ======================================================================

class WebhookTestViewSet(viewsets.ViewSet):
    """
    【生产级 Webhook 接口】(已恢复)
    - 用于接收司空或外部系统的 HTTP 推送
    - 数据仅存入队列，暂不干扰 MinIO 轮询逻辑
    """
    permission_classes = [AllowAny]  # 注意：需确保导入了 AllowAny

    @action(detail=False, methods=['post', 'get'], url_path='receive')
    def receive_data(self, request):
        if request.method == 'GET':
            return Response(
                {'msg': 'Webhook OK（请以 POST 方式发送正式数据）'},
                status=status.HTTP_200_OK
            )

        try:
            # 尝试解析 JSON
            try:
                data = request.data
            except:
                data = {}

            # 摘要日志，便于现场快速判断消息类型
            evt_type = None
            topic = None
            if isinstance(data, dict):
                evt_type = data.get("type") or data.get("event") or data.get("method")
                topic = data.get("topic")

            sn = None
            if isinstance(data, dict):
                sn = data.get("sn") or data.get("device_sn") or (data.get("gateway") or {}).get("sn")

            has_url = False
            if isinstance(data, dict):
                payload = data.get("data", data)
                if isinstance(payload, dict):
                    u = payload.get("url")
                    has_url = bool(u and str(u).startswith(("http://", "https://")))

            # --- 智能日志过滤与增强 ---
            # 1. 定义仅仅是"噪音"的基础设施事件
            NOISY_EVENTS = [
                "client.check_authz_complete",
                "message.delivered",
                "message.acked",
                "client.connected",
                "client.disconnected",
                "session.subscribed",
                "session.unsubscribed",
                "message.publish"  # 🔥 新增：过滤MQTT消息发布事件（太频繁）
            ]

            # 2. 只有非噪音事件，或者虽然是噪音但包含了特殊信息（如URL）时才打印
            if evt_type not in NOISY_EVENTS or has_url:
                log_parts = [f"🔥 [Webhook] 收到: type={evt_type or '未知'}"]
                if sn:
                    log_parts.append(f"sn={sn}")
                if topic:
                    log_parts.append(f"topic={topic}")
                if has_url:
                    log_parts.append("✅ [包含URL]")

                print(" ".join(log_parts))
            else:
                # 极其偶尔打印一个点，表示服务还活着，但防止刷屏
                # print(".", end="", flush=True)
                pass

            # 处理 challenge，用于司空验证
            if isinstance(data, dict) and "challenge" in data:
                return Response({"challenge": data["challenge"]})

            # 生成事件 ID（用于去重）
            event_id = (
                    data.get("id")
                    or data.get("event_id")
                    or f"{time.time()}-{request.META.get('REMOTE_ADDR')}"
            )

            if event_id in processed_event_ids:
                return Response({"msg": "重复事件，已忽略"}, status=200)

            processed_event_ids.add(event_id)

            # 为了防止集合无限增长，简单清理一下（可选）
            if len(processed_event_ids) > 1000:
                processed_event_ids.clear()

            data["_event_id"] = event_id

            # 放入队列 (如果你后续想处理它，可以再写一个 worker 来消费这个队列)
            webhook_queue.put(data)
            try:
                webhook_recent.append({
                    "event_id": event_id,
                    "type": evt_type,
                    "sn": sn,
                    "has_url": has_url,
                    "payload": data,
                    "received_at": time.time(),
                })
            except Exception:
                pass

            return Response({"msg": "接收成功", "event_id": event_id}, status=200)

        except Exception as e:
            print(f"❌ Webhook 处理异常: {e}")
            return Response({"msg": "解析失败"}, status=400)

    @action(detail=False, methods=['get'], url_path='recent')
    def recent(self, request):
        """
        查询最近收到的 Webhook 消息（最多50条）
        GET /api/v1/test/webhook/recent
        """
        try:
            # 转为列表以便序列化
            items = list(webhook_recent) if webhook_recent else []
            # 可选：限制返回字段大小，避免过大载荷影响前端
            out = []
            for it in items[-50:]:
                payload = it.get("payload", {})
                # 只返回部分关键字段，完整载荷仍可从 payload 查看
                out.append({
                    "event_id": it.get("event_id"),
                    "type": it.get("type"),
                    "sn": it.get("sn"),
                    "has_url": it.get("has_url"),
                    "received_at": it.get("received_at"),
                    "payload": payload,
                })
            return Response({"count": len(out), "items": out}, status=200)
        except Exception as e:
            print(f"❌ Webhook recent 查询异常: {e}")
            return Response({"msg": "查询失败"}, status=500)

@csrf_exempt
def scan_candidate_folders(request):
    """
    [API] 查询数据库中的任务列表（不再扫描 MinIO）
    🔥 优化：避免与 minio_poller_worker 重复扫描
    新逻辑：
    1. 直接从数据库查询已存在的任务
    2. 按日期分组返回
    3. 不再自动创建任务（由 minio_poller_worker 负责）
    """
    if request.method != 'GET':
        return JsonResponse({"code": 405, "msg": "Method Not Allowed"})

    try:
        # 🔥 直接查询数据库中的所有任务
        tasks = InspectTask.objects.filter(
            parent_task__isnull=True  # 只查询父任务
        ).order_by('-created_at')
        
        # 按日期分组
        candidates = {}
        
        for task in tasks:
            # 提取日期
            if task.created_at:
                date_str = task.created_at.strftime("%Y-%m-%d")
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")
            
            # 计算任务状态
            total_images = task.images.count()
            if total_images > 0:
                done_images = task.images.filter(detect_status='done').count()
                processing_images = task.images.filter(detect_status='processing').count()
                
                if processing_images > 0:
                    db_status = "processing"
                elif done_images < total_images:
                    db_status = "processing"
                else:
                    db_status = task.detect_status
            else:
                db_status = task.detect_status
            
            # 构建任务信息
            if date_str not in candidates:
                candidates[date_str] = []
            
            candidates[date_str].append({
                "task_uuid": task.dji_task_uuid or str(task.id),
                "task_name": task.external_task_id or task.dji_task_name or "未命名任务",
                "detect_type": task.detect_category.name if task.detect_category else "未知类型",
                "category_code": task.detect_category.code if task.detect_category else "unknown",
                "dji_status": task.dji_status or "unknown",
                "db_status": db_status,
                "prefix_path": task.prefix_list[0] if task.prefix_list else "",
                "wayline_uuid": str(task.wayline.id) if task.wayline else ""
            })
        
        # 转为数组，按日期倒序排列
        result = [
            {"date": date, "tasks": tasks}
            for date, tasks in sorted(candidates.items(), reverse=True)
        ]
        
        total_tasks = sum(len(group['tasks']) for group in result)
        response_msg = f"查询完成，共 {total_tasks} 个任务"
        
        print(f"✅ [Scan DB] {response_msg}")
        return JsonResponse({
            "code": 200, 
            "data": result,
            "msg": response_msg,
            "auto_started": 0  # 不再自动启动
        })
        
    except Exception as e:
        print(f"❌ [Scan DB Error]: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"code": 500, "msg": str(e)})


@csrf_exempt
def start_manual_task(request):
    """
    手动/手机端启动检测任务
    POST /start_manual_task
    Body: { "source": "mobile", "folder_path": "...", "detect_type": "...", "task_name": "..." }
    """
    if request.method != 'POST':
        return JsonResponse({"code": 405, "msg": "Method Not Allowed"})
    
    try:
        data = json.loads(request.body)
        source = data.get('source', 'unknown')
        folder_path = data.get('folder_path')
        detect_type = data.get('detect_type', 'unknown')
        task_name = data.get('task_name', '').strip()
        
        print(f"📱 [Manual Task] 收到启动请求, source={source}, data={data}")
        
        if not folder_path:
            return JsonResponse({"code": 400, "msg": "必须提供 folder_path"})
            
        # 1. 尝试从路径中解析 task_uuid (司空任务ID)
        # 假设路径形如: .../media/{task_uuid}/... 或 .../{task_uuid}/...
        potential_uuid = None
        parts = folder_path.strip('/').split('/')
        
        # 简单启发式：查找 UUID 格式或特定长度的字符串
        for part in reversed(parts):
            if len(part) > 20 and '-' in part: # 简单的 UUID 判断
                potential_uuid = part
                break
            # 或者尝试匹配特定的任务名格式（如果任务名就是 UUID）
        
        if not potential_uuid:
            # 如果没找到明显 UUID，就用最后一个文件夹名作为标识
            potential_uuid = parts[-1] if parts else f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 2. 查找是否已存在对应的司空任务
        # 优先按 dji_task_uuid 查找，其次按 external_task_id (任务名) 查找
        existing_task = InspectTask.objects.filter(
            Q(dji_task_uuid=potential_uuid) | 
            Q(external_task_id=task_name if task_name else potential_uuid) |
            Q(prefix_list__contains=folder_path) # 最准确：按路径查找
        ).first()

        if existing_task:
            print(f"🔄 [Manual Task] 发现现有任务 {existing_task.id} ({existing_task.external_task_id})，复用之")
            
            # 更新状态为 scanning 以触发检测
            existing_task.detect_status = "scanning"
            
            # 如果提供了新的任务名且原任务没名字，则更新
            if task_name and (not existing_task.dji_task_name or existing_task.dji_task_name == existing_task.dji_task_uuid):
                existing_task.dji_task_name = task_name
                existing_task.external_task_id = task_name
                
            # 更新检测类型
            if detect_type and detect_type != 'unknown':
                category_obj = AlarmCategory.objects.filter(code=detect_type).first()
                if category_obj:
                    existing_task.detect_category = category_obj
            
            # 确保路径在列表中
            if folder_path not in existing_task.prefix_list:
                existing_task.prefix_list.append(folder_path)
                
            existing_task.save()
            task = existing_task
            msg = f"已触发检测: {existing_task.external_task_id}"
            
        else:
            # 3. 创建新任务 (确实是手动任务)
            print(f"🆕 [Manual Task] 未找到现有任务，创建新任务")
            
            # 解析任务名称
            if not task_name:
                task_name = parts[-1] if parts else f"manual_task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
            # 匹配检测类型
            category_obj = None
            if detect_type and detect_type != 'unknown':
                category_obj = AlarmCategory.objects.filter(code=detect_type).first()
            
            bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "dji")
            
            # 构造一个唯一的 dji_task_uuid
            # 如果 potential_uuid 看起来像 UUID，就用它；否则加前缀避免冲突
            final_uuid = potential_uuid if len(potential_uuid) > 30 else f"manual_{potential_uuid}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            task = InspectTask.objects.create(
                dji_task_uuid=final_uuid,
                external_task_id=task_name,
                dji_task_name=task_name,
                dji_status="manual_created",
                bucket=bucket_name,
                prefix_list=[folder_path],
                detect_category=category_obj,
                detect_status="scanning",
                started_at=django_timezone.now()
            )
            msg = f"检测任务已启动: {task_name}"

        # 4. 异步触发图片同步和检测
        # 注意：这里我们手动调用 sync_images_core 来立即响应
        # 但为了不阻塞，建议还是依赖后台轮询，或者用线程
        threading.Thread(target=auto_trigger_detect, args=(task,)).start()
        
        return JsonResponse({
            "code": 0, 
            "msg": msg,
            "task_id": task.id
        })
    except Exception as e:
        print(f"❌ [Manual Task Error]: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"code": 500, "msg": str(e)})


import re
from datetime import datetime


def parse_folder_name(folder_name):
    """
    解析文件夹名称，提取日期和类型
    支持格式: "李达轨道 2025-12-12" 或 "20251211_rail_test"
    返回: (date_str, type_str)
    """
    # 移除末尾的斜杠
    folder_name = folder_name.strip('/')

    # 1. 尝试匹配 YYYY-MM-DD 格式
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', folder_name)
    if date_match:
        date_str = date_match.group(1)
        # 类型 = 原名去掉日期和空格
        type_str = folder_name.replace(date_str, '').strip(' _-')
        return date_str, type_str or "未知类型"

    # 2. 尝试匹配 YYYYMMDD 格式
    date_match_compact = re.search(r'(\d{8})', folder_name)
    if date_match_compact:
        raw_date = date_match_compact.group(1)
        # 格式化为 YYYY-MM-DD 以便前端统一展示
        try:
            date_obj = datetime.strptime(raw_date, "%Y%m%d")
            date_str = date_obj.strftime("%Y-%m-%d")
            type_str = folder_name.replace(raw_date, '').strip(' _-')
            return date_str, type_str or "未知类型"
        except ValueError:
            pass

    # 3. 实在解析不出来，就默认“今天”
    return datetime.now().strftime("%Y-%m-%d"), folder_name


@csrf_exempt
def start_selected_tasks(request):
    """
    [API] 批量启动任务
    新逻辑：
    1. 根据任务 UUID 调用司空接口获取任务详情
    2. 根据任务 name 中的关键字自动匹配 detect_category
    3. 图片从 MinIO 扫描获取（通过 sync_images_core）
    4. 启动检测任务
    """
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            selected_tasks = body.get("folders", [])  # 现在传入的是 task_uuid 列表

            if not selected_tasks:
                return JsonResponse({"code": 400, "msg": "未选择任何任务"})

            started_list = []
            bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "dji")

            for task_uuid in selected_tasks:
                print(f"🚀 [Start] 处理任务: {task_uuid}")
                
                # 1. 调用司空接口获取任务详情
                api_data = fetch_dji_task_info(task_uuid)
                
                if not api_data:
                    print(f"⚠️ [Start] 无法获取任务 {task_uuid} 的详情，跳过")
                    continue
                
                task_name = api_data.get("name", task_uuid)
                task_status = api_data.get("status", "unknown")
                wayline_uuid = api_data.get("wayline_uuid", "")
                
                # 2. 根据任务名称匹配检测类型
                category_code = "unknown"
                task_name_lower = task_name.lower()
                
                if ("轨道" in task_name) or ("铁路" in task_name) or ("rail" in task_name_lower):
                    category_code = "rail"
                elif ("接触网" in task_name) or ("contactline" in task_name_lower) or ("catenary" in task_name_lower) or ("overhead" in task_name_lower) or ("绝缘子" in task_name) or ("insulator" in task_name_lower):
                    category_code = "contactline"
                elif ("桥" in task_name) or ("bridge" in task_name_lower):
                    category_code = "bridge"
                elif ("保护区" in task_name) or ("protected_area" in task_name_lower) or ("protection_zone" in task_name_lower) or ("protection_area" in task_name_lower):
                    category_code = "protected_area"
                
                # 3. 获取或创建 AlarmCategory
                category_obj = AlarmCategory.objects.filter(code=category_code).first()
                if not category_obj and category_code != "unknown":
                    category_obj = AlarmCategory.objects.create(
                        name=f"{category_code}检测(自动)", 
                        code=category_code
                    )
                
                # 4. 从 AlarmCategory 继承航线
                target_wayline = category_obj.wayline if category_obj else None
                
                # 5. 从 MinIO 扫描获取真实路径
                prefix_path = f"fh_sync/unknown/media/{task_uuid}/"  # 默认值
                
                # 扫描 MinIO 查找真实路径
                s3 = get_minio_client()
                paginator = s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=bucket_name, Prefix="fh_sync/"):
                    if "Contents" not in page:
                        continue
                    for obj in page["Contents"]:
                        key = obj["Key"]
                        if task_uuid in key and "/media/" in key:
                            parts = key.split("/")
                            try:
                                idx = parts.index("media")
                                prefix_path = "/".join(parts[:idx + 2]) + "/"
                                print(f"📂 [Start] 找到路径: {prefix_path}")
                                break
                            except:
                                pass
                    if prefix_path != f"fh_sync/unknown/media/{task_uuid}/":
                        break
                
                # 6. 创建或更新 InspectTask
                task, created = InspectTask.objects.get_or_create(
                    dji_task_uuid=task_uuid,
                    defaults={
                        "external_task_id": task_name,  # 使用任务名称作为 external_id
                        "dji_task_name": task_name,
                        "dji_status": task_status,
                        "bucket": bucket_name,
                        "prefix_list": [prefix_path],
                        "detect_category": category_obj,
                        "wayline": target_wayline,
                        "detect_status": "scanning",
                        "started_at": django_timezone.now()
                    }
                )
                
                # 7. 如果任务已存在，更新相关字段
                if not created:
                    task.dji_task_name = task_name
                    task.dji_status = task_status
                    task.detect_category = category_obj
                    
                    if target_wayline:
                        task.wayline = target_wayline
                    
                    if not task.prefix_list or task.prefix_list[0] != prefix_path:
                        task.prefix_list = [prefix_path]
                    
                    if task.detect_status != 'scanning':
                        task.detect_status = 'scanning'
                        task.started_at = django_timezone.now()
                    
                    task.save()
                    print(f"🔄 [Start] 任务 {task_name} 已更新")
                else:
                    print(f"✨ [Start] 任务 {task_name} 已创建")
                
                # 8. 从 MinIO 同步图片（使用现有的 sync_images_core 函数）
                print(f"📸 [Start] 开始从 MinIO 同步图片...")
                new_images_count = sync_images_core(task)
                print(f"✅ [Start] 同步了 {new_images_count} 张新图片")
                
                # 9. 重置失败图片（如果是重测）
                reset_count = task.images.filter(detect_status='failed').update(detect_status='pending')
                if reset_count > 0:
                    print(f"🔄 [Start] 重置 {reset_count} 张失败图片")
                
                # 10. 启动检测
                if task.images.filter(detect_status='pending').exists():
                    print(f"🚀 [Start] 启动检测线程")
                    threading.Thread(target=auto_trigger_detect, args=(task,)).start()
                else:
                    print(f"⚠️ [Start] 没有待检测图片，跳过检测")
                
                started_list.append(task_name)

            return JsonResponse({
                "code": 200, 
                "msg": f"成功启动 {len(started_list)} 个任务", 
                "started": started_list
            })

        except Exception as e:
            print(f"❌ [Start Task Error]: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"code": 500, "msg": str(e)})

    return JsonResponse({"code": 405, "msg": "Method Not Allowed"})
@csrf_exempt
def stop_detect(request):
    """
    [API] 强制停止/结束检测任务
    前端点击 [结束检测] 按钮时调用
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # 允许传 task_id (数据库ID) 或者 external_id (文件夹名)
            task_id = data.get('task_id')
            folder_name = data.get('folder_name')

            tasks = InspectTask.objects.none()

            if task_id:
                tasks = InspectTask.objects.filter(id=task_id)
            elif folder_name:
                tasks = InspectTask.objects.filter(external_task_id=folder_name)

            if not tasks.exists():
                return JsonResponse({"code": 404, "msg": "未找到指定任务"})

            # 强制更新为 done
            rows = tasks.update(detect_status="done")

            return JsonResponse({"code": 200, "msg": f"已停止 {rows} 个任务"})

        except Exception as e:
            return JsonResponse({"code": 500, "msg": str(e)})

    return JsonResponse({"code": 405, "msg": "Method Not Allowed"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alarm_dashboard_stats_summary(request):
    """
    首页告警统计/处置率缓存读取
    GET /api/v1/alarm-dashboard-stats/summary/?metric=detect_type&range_days=30
    可选参数: refresh=1 (若无缓存则即时计算并写入)
    """
    metric = request.query_params.get("metric", "detect_type")
    try:
        range_days = int(request.query_params.get("range_days", 30))
    except (TypeError, ValueError):
        range_days = 30
    refresh = str(request.query_params.get("refresh", "0")).lower() in {"1", "true", "yes"}

    obj = (
        AlarmDashboardStats.objects.filter(metric=metric, range_days=range_days)
        .order_by("-computed_at")
        .first()
    )

    if not obj and refresh:
        obj = upsert_alarm_dashboard_stats(range_days, metric)

    if not obj:
        window_start, window_end = resolve_window(range_days)
        return Response(
            {
                "metric": metric,
                "range_days": range_days,
                "total": 0,
                "series": [],
                "window": {
                    "start": window_start.isoformat(),
                    "end": window_end.isoformat(),
                },
                "computed_at": None,
            }
        )

    return Response(
        {
            "metric": obj.metric,
            "range_days": obj.range_days,
            "total": obj.total,
            "series": obj.series,
            "window": {
                "start": obj.window_start.isoformat() if obj.window_start else None,
                "end": obj.window_end.isoformat() if obj.window_end else None,
            },
            "computed_at": obj.computed_at.isoformat() if obj.computed_at else None,
        }
    )


class WaylineFingerprintManager:

    @staticmethod
    def get_api_headers_and_host():
        """从 Settings 获取配置"""
        base_url = getattr(settings, "DJI_API_BASE_URL", "http://192.168.10.2").rstrip('/')
        
        # 动态生成 X-Request-Id (如果 Settings 里没配，或者需要每次唯一)
        # 通常 X-Request-Id 应该是唯一的，这里我们优先用 Settings 里的前缀+UUID，或者直接 UUID
        request_id = getattr(settings, "DJI_X_Request_ID", str(uuid.uuid4()))
        if request_id == "uuid-123": # 如果是默认值，生成一个新的
             request_id = str(uuid.uuid4())
             
        headers = {
            "X-User-Token": getattr(settings, "DJI_X_USER_TOKEN", ""),
            "X-Project-Uuid": getattr(settings, "DJI_X_PROJECT_UUID", ""),
            "X-Request-Id": request_id,
            "X-Language": getattr(settings, "DJI_X_LANGUAGE", "zh"),
            "Content-Type": "application/json"
        }
        if not headers["X-User-Token"] or not headers["X-Project-Uuid"]:
            raise Exception("Settings 中缺少 DJI_X_USER_TOKEN 或 DJI_X_PROJECT_UUID 配置")
        return headers, base_url

    @staticmethod
    def sync_by_keywords():
        """
        🚀 [按需同步核心逻辑]
        1. 获取 API 所有航线列表。
        2. 遍历本地 AlarmCategory 获取匹配规则 (例如: 轨道, 桥梁)。
        3. 只有名字匹配上的航线，才下载 KMZ 并存入指纹表。
        """
        print("🔄 [Fingerprint] 开始按关键字匹配并同步...")

        try:
            # 1. 准备配置和规则
            headers, base_url = WaylineFingerprintManager.get_api_headers_and_host()

            categories = AlarmCategory.objects.filter(parent__isnull=True)

            if not categories.exists():
                print("⚠️ [Stop] 本地 AlarmCategory 表为空，无法进行匹配。")
                return

            print(f"   -> 加载匹配规则: {[c.name + ':' + (c.match_keyword or '') for c in categories]}")

            # 2. 调用 API 获取航线列表 (仅获取名字和ID)
            # API: GET /openapi/v0.1/wayline
            list_url = f"{base_url}/openapi/v0.1/wayline"

            # 分页获取所有航线 (这里简化写，假设一页够用，不够可加循环)
            res = requests.get(list_url, headers=headers, params={"page": 1, "page_size": 200}, timeout=10)
            if res.status_code != 200:
                print(f"❌ 获取航线列表失败: {res.status_code}")
                return

            res_json = res.json()
            raw_data = res_json.get('data', [])
            wayline_list = raw_data.get('list', []) if isinstance(raw_data, dict) else raw_data

            print(f"   -> API 返回 {len(wayline_list)} 条航线，开始筛选...")

            matched_count = 0

            # 3. 循环匹配
            for item in wayline_list:
                w_id = item.get('id')
                w_name = item.get('name')

                if not w_id or not w_name: continue

                w_name_str = str(w_name)
                w_name_lower = w_name_str.lower()

                # 🔥 优化：数据库优先策略
                # 如果数据库中已经存在该航线且有类型，直接使用数据库中的类型
                existing_wayline = Wayline.objects.filter(wayline_id=w_id).first()
                matched_category = None

                if existing_wayline and existing_wayline.detect_type:
                    # 尝试从数据库类型反查 category 对象
                    # 注意：existing_wayline.detect_type 存储的是 normalized code (如 rail, bridge)
                    # 我们需要找到对应的 AlarmCategory
                    db_type = existing_wayline.detect_type
                    
                    # 优先匹配 code 完全一致的
                    matched_category = next((c for c in categories if normalize_detect_code(c.code) == db_type), None)
                    
                    if matched_category:
                        print(f"   ✅ [Database] 航线 '{w_name_str}' 使用已有类型: {matched_category.name} ({db_type})")
                    else:
                        # 如果找不到对应的 category (比如类型被删了)，回退到关键词匹配
                        print(f"   ⚠️ [Database] 航线 '{w_name_str}' 有类型 {db_type} 但未找到对应分类配置，尝试重新匹配...")

                # 如果数据库没有匹配到，则尝试关键词匹配
                if not matched_category:
                    for cat in categories:
                     norm_code = normalize_detect_code(cat.code)
                    keyword_map = {
                        "rail": ["rail", "铁路", "轨道"],
                        "contactline": ["contactline", "接触网", "catenary", "overhead"],
                        "bridge": ["bridge", "桥梁"],
                        "protected_area": ["protected_area", "保护区"],
                    }
                    tokens = []
                    if cat.match_keyword:
                        tokens.append(cat.match_keyword)
                    tokens.extend(keyword_map.get(norm_code, []))

                    for token in tokens:
                        if token and token.lower() in w_name_lower:
                            matched_category = cat
                            break
                    if matched_category:
                        break

                # 只有匹配成功的才处理
                if matched_category:
                    print(f"   ✅ [Match] 航线 '{w_name_str}' 命中规则: {matched_category.name}")

                    # 4. 获取详情拿到 download_url
                    WaylineFingerprintManager.process_single_wayline(
                        base_url, headers, w_id, w_name, matched_category
                    )
                    matched_count += 1
                else:
                    # print(f"   ⚪ [Skip] 航线 '{w_name}' 未匹配任何关键字")
                    pass

            print(f"🏁 同步完成: API共 {len(wayline_list)} 条，匹配并入库 {matched_count} 条。")

        except Exception as e:
            print(f"❌ 同步流程异常: {e}")
            import traceback
            traceback.print_exc()

    @staticmethod
    def process_single_wayline(base_url, headers, wayline_id, wayline_name, category_obj):
        """
        处理单个命中的航线：入库 Wayline -> 获取 URL -> 下载 KMZ -> 入库 Fingerprint
        """
        print(f"🚀 [Debug] process_single_wayline 版本: DEBUG_V2")
        try:
            # A. 确保存储了 Wayline 基本信息
            local_wayline, _ = Wayline.objects.update_or_create(
                wayline_id=wayline_id,
                defaults={
                    "name": wayline_name,
                    "detect_type": normalize_detect_code(category_obj.code)
                }
            )

            # B. 调用详情接口获取 download_url
            detail_url = f"{base_url}/openapi/v0.1/wayline/{wayline_id}"
            res = requests.get(detail_url, headers=headers, timeout=10)

            download_url = None
            if res.status_code == 200:
                data = res.json().get('data', {})
                download_url = data.get('download_url')

            if not download_url:
                print(f"      ⚠️ 未获取到 download_url，跳过下载")
                return

            # C. 下载并解析 KMZ
            print(f"      📥 下载 KMZ 解析指纹...")
            r = requests.get(download_url, timeout=30)
            if r.status_code != 200:
                return

            uuid_set = set()
            action_details_list = []
            
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                kml_files = [n for n in z.namelist() if n.endswith('template.kml')]
                if kml_files:
                    with z.open(kml_files[0]) as f:
                        # 使用 ElementTree 解析 XML
                        try:
                            import xml.etree.ElementTree as ET
                            # 定义命名空间
                            ns = {'wpml': 'http://www.dji.com/wpmz/1.0.0', 'kml': 'http://www.opengis.net/kml/2.2'}
                            
                            # 注册命名空间以便 find 查找
                            # ET.register_namespace('wpml', ns['wpml'])
                            # ET.register_namespace('', ns['kml'])
                            
                            content = f.read()
                            root = ET.fromstring(content)
                            print(f"      🗂️ 解析文件: {kml_files[0]}")
                            print(f"      🧾 KML 内容长度: {len(content)} 字节")
                            
                            # 查找所有 Placemark (航点)
                            # 注意: KML 结构通常是 Document -> Folder -> Placemark
                            # 使用 XPath 查找所有 Placemark
                            # 由于 ElementTree 对带命名空间的查找支持有限，这里用比较通用的方式
                            
                            # 辅助函数：带命名空间的查找
                            def find_val(node, tag):
                                res = node.find(f".//wpml:{tag}", ns)
                                if res is None: # 尝试不带命名空间的前缀（有时候结构复杂）
                                     res = node.find(f".//{{http://www.dji.com/wpmz/1.0.0}}{tag}")
                                return res.text if res is not None else None

                            def find_all(node, tag):
                                return node.findall(f".//wpml:{tag}", ns) or node.findall(f".//{{http://www.dji.com/wpmz/1.0.0}}{tag}")
                            
                            def _local(t):
                                x = t
                                if '}' in x:
                                    x = x.split('}', 1)[1]
                                if ':' in x:
                                    x = x.split(':', 1)[1]
                                return x
                            
                            def find_local_first(node, name):
                                for n in node.iter():
                                    if _local(n.tag) == name:
                                        return n
                                return None
                            
                            def find_local_all(node, name):
                                out = []
                                for n in node.iter():
                                    if _local(n.tag) == name:
                                        out.append(n)
                                return out

                            # 遍历所有 Placemark
                            # KML 标准中 Placemark 是属于 http://www.opengis.net/kml/2.2
                            placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
                            print(f"      📍 Placemark 数量: {len(placemarks)}")
                            actions_total = 0
                            
                            for idx, pm in enumerate(placemarks, 1):
                                # 1. 提取位置信息
                                point = pm.find(".//{http://www.opengis.net/kml/2.2}Point") or find_local_first(pm, "Point")
                                if point is None: continue
                                
                                coords_text = point.find(".//{http://www.opengis.net/kml/2.2}coordinates") or find_local_first(point, "coordinates")
                                if coords_text is None: continue
                                
                                # coordinates 格式: lon,lat 或 lon,lat,height
                                coords = coords_text.text.strip().split(',')
                                lon = float(coords[0])
                                lat = float(coords[1])
                                
                                # 高度信息 (优先用 wpml:height)
                                height_node = find_local_first(pm, 'height')
                                ellipsoid_node = find_local_first(pm, 'ellipsoidHeight')
                                height_val = height_node.text if height_node is not None else find_val(pm, 'height')
                                ellipsoid_height = ellipsoid_node.text if ellipsoid_node is not None else find_val(pm, 'ellipsoidHeight')
                                
                                # 如果 wpml:height 没找到，尝试从 coordinates 取第3个值
                                final_height = float(height_val) if height_val else (float(coords[2]) if len(coords) > 2 else 0.0)

                                # 2. 查找该航点下的所有 Action
                                action_group = pm.find(".//wpml:actionGroup", ns) or pm.find(".//{http://www.dji.com/wpmz/1.0.0}actionGroup") or find_local_first(pm, "actionGroup")
                                
                                if action_group:
                                    actions = find_all(action_group, 'action') or find_local_all(action_group, 'action')
                                    actions_total += len(actions)
                                    if len(actions) == 0:
                                        print(f"      ⚠️ Placemark#{idx} 未找到 action")
                                    for action in actions:
                                        actuator_param = action.find(".//wpml:actionActuatorFuncParam", ns) or action.find(".//{http://www.dji.com/wpmz/1.0.0}actionActuatorFuncParam") or find_local_first(action, "actionActuatorFuncParam")
                                        
                                        if actuator_param:
                                            # 提取 UUID
                                            uuid_node = actuator_param.find("wpml:actionUUID", ns) or actuator_param.find("{http://www.dji.com/wpmz/1.0.0}actionUUID") or find_local_first(actuator_param, "actionUUID")
                                            if uuid_node is not None and uuid_node.text:
                                                uuid = uuid_node.text
                                                uuid_set.add(uuid)
                                                
                                                # 提取 Yaw
                                                yaw_node = actuator_param.find("wpml:gimbalYawRotateAngle", ns) or actuator_param.find("{http://www.dji.com/wpmz/1.0.0}gimbalYawRotateAngle") or find_local_first(actuator_param, "gimbalYawRotateAngle")
                                                gimbal_yaw = float(yaw_node.text) if yaw_node is not None else 0.0
                                                
                                                # 提取 Aircraft Heading (如果有)
                                                heading_node = actuator_param.find("wpml:aircraftHeading", ns) or actuator_param.find("{http://www.dji.com/wpmz/1.0.0}aircraftHeading") or find_local_first(actuator_param, "aircraftHeading")
                                                aircraft_heading = float(heading_node.text) if heading_node is not None else 0.0

                                                # 组装详细信息
                                                detail = {
                                                    "uuid": uuid,
                                                    "lat": lat,
                                                    "lon": lon,
                                                    "height": final_height,
                                                    "ellipsoid_height": float(ellipsoid_height) if ellipsoid_height else None,
                                                    "gimbal_yaw": gimbal_yaw,
                                                    "aircraft_heading": aircraft_heading
                                                }
                                                action_details_list.append(detail)
                                else:
                                    print(f"      ⚠️ Placemark#{idx} 未找到 actionGroup")
                            
                            print(f"      📊 解析统计: UUID={len(uuid_set)}, Placemark={len(placemarks)}, Actions={actions_total}, 详情={len(action_details_list)}")
                            
                            # 如果未在 Placemark 下找到 actionGroup，尝试全局查找并通过索引映射航点
                            try:
                                if actions_total == 0:
                                    # 构建航点坐标索引列表 (0-based)
                                    coords_list = []
                                    for pm in placemarks:
                                        point = pm.find(".//{http://www.opengis.net/kml/2.2}Point")
                                        coords_text = point.find(".//{http://www.opengis.net/kml/2.2}coordinates") if point is not None else None
                                        if coords_text is None:
                                            coords_list.append(None)
                                            continue
                                        coords = coords_text.text.strip().split(',')
                                        lon = float(coords[0]); lat = float(coords[1])
                                        height_val = find_val(pm, 'height')
                                        ellipsoid_height = find_val(pm, 'ellipsoidHeight')
                                        final_height = float(height_val) if height_val else (float(coords[2]) if len(coords) > 2 else 0.0)
                                        coords_list.append((lat, lon, final_height, float(ellipsoid_height) if ellipsoid_height else None))
                                    
                                    global_groups = root.findall(".//wpml:actionGroup", ns) or root.findall(".//{http://www.dji.com/wpmz/1.0.0}actionGroup")
                                    print(f"      🌐 全局 actionGroup 数量: {len(global_groups)}")
                                    
                                    for g_idx, group in enumerate(global_groups, 1):
                                        start_idx_txt = find_val(group, 'actionGroupStartIndex')
                                        end_idx_txt = find_val(group, 'actionGroupEndIndex')
                                        sel_idx = None
                                        if start_idx_txt and start_idx_txt.isdigit():
                                            sel_idx = int(start_idx_txt)
                                        elif end_idx_txt and end_idx_txt.isdigit():
                                            sel_idx = int(end_idx_txt)
                                        
                                        if sel_idx is None or sel_idx < 0 or sel_idx >= len(coords_list):
                                            print(f"      ⚠️ Group#{g_idx} 无法映射航点索引 (start={start_idx_txt}, end={end_idx_txt})")
                                        
                                        actions = find_all(group, 'action')
                                        if len(actions) == 0:
                                            # 兼容：有些模板直接把 UUID 放在 actionGroup 里
                                            uuid_nodes = group.findall(".//wpml:actionUUID", ns) or group.findall(".//{http://www.dji.com/wpmz/1.0.0}actionUUID")
                                        else:
                                            uuid_nodes = []
                                        
                                        mapped_coords = coords_list[sel_idx] if (sel_idx is not None and 0 <= sel_idx < len(coords_list)) else None
                                        
                                        # 1) 遍历标准 action 节点
                                        for action in actions:
                                            actuator_param = action.find(".//wpml:actionActuatorFuncParam", ns) or action.find(".//{http://www.dji.com/wpmz/1.0.0}actionActuatorFuncParam")
                                            if actuator_param is None:
                                                continue
                                            
                                            # 判断是否是保护区航线 (允许无 UUID 提取坐标)
                                            is_protected_wayline = False
                                            if category_obj:
                                                cat_code = str(getattr(category_obj, 'code', '')).lower()
                                                if 'protected' in cat_code or '保护区' in cat_code:
                                                    is_protected_wayline = True
                                            
                                            print(f"      🔍 [Debug] Check Action: is_protected={is_protected_wayline}, cat_code={getattr(category_obj, 'code', 'None')}")
                                            
                                            uuid = None
                                            uuid_node = actuator_param.find("wpml:actionUUID", ns) or actuator_param.find("{http://www.dji.com/wpmz/1.0.0}actionUUID")
                                            
                                            if uuid_node is not None and uuid_node.text:
                                                uuid = uuid_node.text
                                                uuid_set.add(uuid) # 只有真实 UUID 才加入匹配集合
                                                print(f"      ✅ [Debug] Found Real UUID: {uuid}")
                                            
                                            # 如果没有 UUID，且是保护区航线，生成虚拟 UUID 用于绘图
                                            if not uuid and is_protected_wayline:
                                                func_node = action.find("wpml:actionActuatorFunc", ns) or action.find("{http://www.dji.com/wpmz/1.0.0}actionActuatorFunc")
                                                func_name = func_node.text if func_node is not None else "action"
                                                # 使用索引生成唯一标识
                                                uuid = f"virtual_{func_name}_{g_idx}_{actions.index(action)}"
                                                print(f"      🔧 [Debug] Generated Virtual UUID: {uuid}")
                                            
                                            if not uuid:
                                                print(f"      ⚠️ [Debug] Skip Action (No UUID)")
                                                continue

                                            yaw_node = actuator_param.find("wpml:gimbalYawRotateAngle", ns) or actuator_param.find("{http://www.dji.com/wpmz/1.0.0}gimbalYawRotateAngle")
                                            gimbal_yaw = float(yaw_node.text) if yaw_node is not None else 0.0
                                            heading_node = actuator_param.find("wpml:aircraftHeading", ns) or actuator_param.find("{http://www.dji.com/wpmz/1.0.0}aircraftHeading")
                                            aircraft_heading = float(heading_node.text) if heading_node is not None else 0.0
                                            
                                            detail = {
                                                "uuid": uuid,
                                                "lat": mapped_coords[0] if mapped_coords else None,
                                                "lon": mapped_coords[1] if mapped_coords else None,
                                                "height": mapped_coords[2] if mapped_coords else None,
                                                "ellipsoid_height": mapped_coords[3] if mapped_coords else None,
                                                "gimbal_yaw": gimbal_yaw,
                                                "aircraft_heading": aircraft_heading
                                            }
                                            action_details_list.append(detail)
                                            actions_total += 1
                                        
                                        # 2) 兼容遍历直接 UUID 节点
                                        for uuid_node in uuid_nodes:
                                            if not uuid_node.text:
                                                continue
                                            uuid = uuid_node.text
                                            uuid_set.add(uuid)
                                            detail = {
                                                "uuid": uuid,
                                                "lat": mapped_coords[0] if mapped_coords else None,
                                                "lon": mapped_coords[1] if mapped_coords else None,
                                                "height": mapped_coords[2] if mapped_coords else None,
                                                "ellipsoid_height": mapped_coords[3] if mapped_coords else None,
                                                "gimbal_yaw": 0.0,
                                                "aircraft_heading": 0.0
                                            }
                                            action_details_list.append(detail)
                                            actions_total += 1
                                    
                                    print(f"      ✅ 全局解析补充后: UUID={len(uuid_set)}, Actions={actions_total}, 详情={len(action_details_list)}")
                            except Exception as e:
                                print(f"      ❌ 全局解析失败: {e}")
                                                
                        except Exception as parse_err:
                            print(f"      ❌ 解析 KML 失败: {parse_err}")
                            # 降级：如果 XML 解析失败，回退到正则只提取 UUID
                            content_str = content.decode('utf-8', errors='ignore')
                            found = re.findall(r'<wpml:actionUUID>(.*?)</wpml:actionUUID>', content_str)
                            uuid_set.update(found)

            # D. 存入指纹表 (包含 detect_category 和 action_details)
            # 🔥 [修复] 即使没有提取到 UUID，只要匹配了分类也入库，方便排查和记录
            if uuid_set or category_obj:
                fp, _ = WaylineFingerprint.objects.get_or_create(wayline=local_wayline)
                fp.detect_category = category_obj
                fp.action_uuids = list(uuid_set)
                fp.action_details = action_details_list # 🔥 存入详细信息
                fp.source_url = download_url
                fp.save()
                
                if uuid_set:
                    print(f"      💾 指纹入库成功 (包含 {len(uuid_set)} 个 UUID, {len(action_details_list)} 条详情)")
                else:
                    print(f"      ⚠️ [Warning] 指纹入库 (无UUID): 航线 '{wayline_name}' 未提取到动作UUID，但已绑定分类 '{category_obj.name}'")

        except Exception as e:
            print(f"      ❌ 处理单条航线出错: {e}")

    @staticmethod
    def identify(image_uuid):
        """根据图片UUID反查航线"""
        all_fps = WaylineFingerprint.objects.all()
        for fp in all_fps:
            if image_uuid in fp.action_uuids:
                return fp.wayline
        return None



class FlightTaskProxyViewSet(viewsets.ViewSet):
    """
    代理 DJI 飞行任务相关的 API 请求
    通过后端转发，隐藏 settings 中的敏感 Header 信息
    """
    
    @action(detail=False, methods=['get'])
    def devices(self, request):
        """获取设备列表 (GET /device)"""
        try:
            headers, base_url = WaylineFingerprintManager.get_api_headers_and_host()
            # 这里的路径取决于司空的真实 API，通常是 /openapi/v0.1/device
            # 如果需要分页，司空 API 可能需要 page/page_size 参数
            url = f"{base_url}/openapi/v0.1/device"

            # 透传前端传来的 query params (比如 page_size)
            params = request.query_params

            print(f"📡 [Proxy] Forwarding GET to {url}")
            resp = requests.get(url, headers=headers, params=params, timeout=10)

            # 直接返回上游的 JSON
            return Response(resp.json(), status=resp.status_code)
        except Exception as e:
            print(f"❌ [Proxy Error] Fetch devices failed: {e}")
            return Response({"code": 500, "msg": str(e)}, status=500)

    @action(detail=False, methods=['get'], url_path='recent-devices')
    def recent_devices(self, request):
        """
        获取最近使用的设备SN列表
        用于创建任务页面的快速选择
        """
        try:
            # 从 FlightTaskInfo 表获取最近使用的设备
            # 按创建时间降序，去重，最多返回10个
            from django.db.models import Max

            recent_tasks = FlightTaskInfo.objects.filter(
                sn__isnull=False
            ).exclude(
                sn=''
            ).values('sn').annotate(
                last_used=Max('created_at')
            ).order_by('-last_used')[:10]

            device_list = []
            for task in recent_tasks:
                sn = task['sn']
                # 查找该SN最近的任务名称
                task_info = FlightTaskInfo.objects.filter(sn=sn).order_by('-created_at').first()
                device_list.append({
                    'sn': sn,
                    'name': task_info.name if task_info else sn,
                    'last_used': task['last_used'].isoformat()
                })

            return Response({
                "code": 0,
                "data": device_list
            })
        except Exception as e:
            print(f"❌ [Error] Get recent devices failed: {e}")
            return Response({"code": 500, "msg": str(e)}, status=500)

    @action(detail=False, methods=['post'], url_path='create')
    def create_task(self, request):
        """创建飞行任务 (POST /flight-task)"""
        try:
            headers, base_url = WaylineFingerprintManager.get_api_headers_and_host()
            url = f"{base_url}/openapi/v0.1/flight-task"

            print(f"📡 [Proxy] Forwarding POST to {url}")
            # request.data 已经是解析后的 JSON (dict)
            resp = requests.post(url, headers=headers, json=request.data, timeout=10)

            res_json = resp.json()

            # 如果创建成功，保存到数据库
            if resp.status_code == 200 and res_json.get('code') == 0:
                try:
                    data = res_json.get('data', {})
                    task_uuid = data.get('task_uuid')

                    if task_uuid:
                        # 提取参数
                        req_data = request.data
                        # 兼容前端发送的 wayline_uuid 和 wayline_id 两种字段名
                        wayline_id = req_data.get('wayline_uuid') or req_data.get('wayline_id')
                        FlightTaskInfo.objects.create(
                            task_uuid=task_uuid,
                            name=req_data.get('name', '未命名任务'),
                            sn=req_data.get('sn'),
                            wayline_id=wayline_id,
                            params=req_data,
                            status='created',
                            is_protected_area=req_data.get('is_protected_area', False)
                        )
                        print(f"✅ [DB] Flight task recorded: {task_uuid}, wayline_id: {wayline_id}, is_protected_area: {req_data.get('is_protected_area', False)}")
                except Exception as db_e:
                    print(f"⚠️ [DB Error] Failed to record flight task: {db_e}")

            return Response(res_json, status=resp.status_code)
        except Exception as e:
            print(f"❌ [Proxy Error] Create task failed: {e}")
            return Response({"code": 500, "msg": str(e)}, status=500)

    @action(detail=True, methods=['post'], url_path='command')
    def device_command(self, request, pk=None):
        """
        设备控制命令 (POST /openapi/v0.1/device/{device_sn}/command)
        支持: return_home, return_home_cancel, flighttask_pause, flighttask_recovery

        注意：detail=True 时，Django 会将 URL 参数作为 pk 传递，不是 device_sn
        """
        try:
            device_sn = pk  # 使用 pk 作为 device_sn

            headers, base_url = WaylineFingerprintManager.get_api_headers_and_host()
            url = f"{base_url}/openapi/v0.1/device/{device_sn}/command"

            # 获取命令参数
            device_command = request.data.get('device_command')

            if not device_command:
                return Response({"code": 400, "msg": "缺少 device_command 参数"}, status=400)

            print(f"📡 [Proxy] Device Command: {device_command} -> {device_sn}")

            # 转发请求到司空API
            resp = requests.post(url, headers=headers, json=request.data, timeout=10)

            res_json = resp.json()
            print(f"✅ [Proxy] Command response: {res_json}")

            return Response(res_json, status=resp.status_code)
        except Exception as e:
            print(f"❌ [Proxy Error] Device command failed: {e}")
            return Response({"code": 500, "msg": str(e)}, status=500)



class FlightTaskInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    FlightTaskInfo read-only APIs.
    """
    queryset = FlightTaskInfo.objects.all().order_by("-created_at")
    serializer_class = FlightTaskInfoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["sn", "name", "task_uuid"]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
    filterset_fields = {
        "sn": ["exact", "icontains"],
        "created_at": ["gte", "lte", "range"],
    }

    @action(detail=False, methods=["get"], url_path="latest-by-sn")
    def latest_by_sn(self, request):
        sn = request.query_params.get("sn")
        if not sn:
            return Response(
                {"error": "sn parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        task = FlightTaskInfo.objects.filter(sn=sn).order_by("-created_at").first()
        if not task:
            return Response({})
        serializer = self.get_serializer(task)
        return Response(serializer.data)


class DronePositionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    无人机位置信息视图集
    提供位置数据查询、筛选和分析功能
    """
    queryset = DronePosition.objects.all()
    serializer_class = DronePositionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['device_sn', 'device_model']
    ordering_fields = ['timestamp', 'created_at', 'altitude', 'battery_percent']
    ordering = ['-timestamp']  # 默认按时间戳降序

    filterset_fields = {
        'device_sn': ['exact', 'icontains'],
        'device_model': ['exact', 'icontains'],
        'timestamp': ['gte', 'lte', 'range'],
        'altitude': ['gte', 'lte'],
        'battery_percent': ['gte', 'lte'],
    }

    @action(detail=False, methods=['get'])
    def latest_by_device(self, request):
        """
        获取每台设备的最新位置
        GET /api/drone-positions/latest_by_device/
        """
        from django.db.models import Max

        # 获取所有设备的最新时间戳
        latest_timestamps = DronePosition.objects.values('device_sn').annotate(
            latest_time=Max('timestamp')
        )

        # 获取每台设备的最新记录
        latest_positions = []
        for item in latest_timestamps:
            position = DronePosition.objects.filter(
                device_sn=item['device_sn'],
                timestamp=item['latest_time']
            ).first()
            if position:
                latest_positions.append(position)

        serializer = self.get_serializer(latest_positions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def track(self, request):
        """
        获取指定设备的飞行轨迹
        GET /api/drone-positions/track/?device_sn=xxx&start_time=xxx&end_time=xxx
        """
        device_sn = request.query_params.get('device_sn')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')

        if not device_sn:
            return Response(
                {"error": "必须提供 device_sn 参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = DronePosition.objects.filter(device_sn=device_sn)

        if start_time:
            queryset = queryset.filter(timestamp__gte=start_time)
        if end_time:
            queryset = queryset.filter(timestamp__lte=end_time)

        queryset = queryset.order_by('timestamp')
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            "device_sn": device_sn,
            "count": queryset.count(),
            "track": serializer.data
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        获取位置数据统计信息
        GET /api/drone-positions/statistics/
        """
        from django.db.models import Count, Avg, Max, Min

        # 按设备统计
        device_stats = DronePosition.objects.values('device_sn', 'device_model').annotate(
            record_count=Count('id'),
            avg_altitude=Avg('altitude'),
            max_altitude=Max('altitude'),
            min_altitude=Min('altitude'),
            latest_time=Max('timestamp'),
            earliest_time=Min('timestamp')
        ).order_by('-record_count')

        total_records = DronePosition.objects.count()
        total_devices = DronePosition.objects.values('device_sn').distinct().count()

        return Response({
            "total_records": total_records,
            "total_devices": total_devices,
            "device_statistics": list(device_stats)
        })



class DockStatusViewSet(viewsets.ModelViewSet):
    """
    机场状态管理ViewSet
    提供机场状态的CRUD和实时查询功能
    """
    queryset = DockStatus.objects.all()
    serializer_class = DockStatusSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["dock_sn", "dock_name"]
    ordering_fields = ["last_update_time", "created_at", "job_number"]
    ordering = ["-last_update_time"]

    filterset_fields = {
        "dock_sn": ["exact", "icontains"],
        "dock_name": ["exact", "icontains"],
        "is_online": ["exact"],
        "mode_code": ["exact"],
        "cover_state": ["exact"],
        "alarm_state": ["exact"],
        "last_update_time": ["gte", "lte", "range"],
    }

    @action(detail=False, methods=["get"])
    def all_docks(self, request):
        """
        获取所有机场的最新状态
        GET /api/dock-status/all_docks/
        """
        docks = DockStatus.objects.all().order_by("-last_update_time")
        serializer = self.get_serializer(docks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def online_docks(self, request):
        """
        获取所有在线机场
        GET /api/dock-status/online_docks/
        """
        docks = DockStatus.objects.filter(is_online=True).order_by("-last_update_time")
        serializer = self.get_serializer(docks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """
        获取指定机场的历史状态（从DronePosition表查询）
        GET /api/dock-status/{id}/history/?start_time=xxx&end_time=xxx
        """
        dock = self.get_object()
        start_time = request.query_params.get("start_time")
        end_time = request.query_params.get("end_time")

        # 这里可以扩展为查询历史记录表，目前返回当前状态
        return Response({
            "dock_sn": dock.dock_sn,
            "message": "历史记录功能待实现，当前仅返回最新状态",
            "current_status": self.get_serializer(dock).data
        })

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        获取机场统计信息
        GET /api/dock-status/statistics/
        """
        from django.db.models import Count, Avg, Sum

        total_docks = DockStatus.objects.count()
        online_docks = DockStatus.objects.filter(is_online=True).count()
        offline_docks = total_docks - online_docks
        
        # 统计有告警的机场
        alarm_docks = DockStatus.objects.exclude(alarm_state=0).count()
        
        # 计算平均任务次数
        avg_jobs = DockStatus.objects.aggregate(avg_jobs=Avg("job_number"))["avg_jobs"] or 0
        
        # 计算总累计时长
        total_acc_time = DockStatus.objects.aggregate(total_time=Sum("acc_time"))["total_time"] or 0

        return Response({
            "total_docks": total_docks,
            "online_docks": online_docks,
            "offline_docks": offline_docks,
            "alarm_docks": alarm_docks,
            "average_job_number": round(avg_jobs, 2),
            "total_accumulated_time_seconds": total_acc_time,
            "total_accumulated_time_hours": round(total_acc_time / 3600, 2)
        })

    @action(detail=True, methods=["post"])
    def update_from_mqtt(self, request, pk=None):
        """
        通过MQTT数据更新机场状态（内部使用）
        POST /api/dock-status/{id}/update_from_mqtt/
        Body: MQTT消息的data字段
        """
        dock = self.get_object()
        mqtt_data = request.data

        # 更新环境信息
        if "environment_temperature" in mqtt_data:
            dock.environment_temperature = mqtt_data["environment_temperature"]
        if "temperature" in mqtt_data:
            dock.temperature = mqtt_data["temperature"]
        if "humidity" in mqtt_data:
            dock.humidity = mqtt_data["humidity"]
        if "wind_speed" in mqtt_data:
            dock.wind_speed = mqtt_data["wind_speed"]
        if "rainfall" in mqtt_data:
            dock.rainfall = mqtt_data["rainfall"]

        # 更新位置信息
        if "latitude" in mqtt_data:
            dock.latitude = mqtt_data["latitude"]
        if "longitude" in mqtt_data:
            dock.longitude = mqtt_data["longitude"]
        if "height" in mqtt_data:
            dock.height = mqtt_data["height"]

        # 更新硬件状态
        if "mode_code" in mqtt_data:
            dock.mode_code = mqtt_data["mode_code"]
        if "cover_state" in mqtt_data:
            dock.cover_state = mqtt_data["cover_state"]
        if "putter_state" in mqtt_data:
            dock.putter_state = mqtt_data["putter_state"]

        # 保存原始数据
        dock.raw_osd_data = mqtt_data
        dock.last_update_time = django_timezone.now()
        dock.is_online = True
        dock.save()

        serializer = self.get_serializer(dock)
        return Response(serializer.data)


class SuspiciousImageViewSet(viewsets.ModelViewSet):
    """
    存疑/误报图片管理
    """
    queryset = SuspiciousImage.objects.all()
    serializer_class = SuspiciousImageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'alarm', 'inspect_image']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        获取存疑图片统计数据
        GET /api/v1/suspicious-images/stats/
        """
        total = self.get_queryset().count()
        pending = self.get_queryset().filter(status='PENDING').count()
        confirmed = self.get_queryset().filter(status='CONFIRMED').count()
        ignored = self.get_queryset().filter(status='IGNORED').count()
        return Response({
            'total': total,
            'pending': pending,
            'confirmed': confirmed,
            'ignored': ignored
        })

    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        导出存疑记录为CSV
        GET /api/v1/suspicious-images/export/
        """
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="suspicious_images.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Image Path', 'Status', 'Note', 'Created At'])
        
        for item in self.get_queryset():
            writer.writerow([
                item.id,
                item.image_path,
                item.get_status_display(),
                item.note,
                item.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
            
        return response


class InspectImageViewSet(viewsets.ModelViewSet):
    """
    巡检图片管理
    """
    queryset = InspectImage.objects.all()
    serializer_class = InspectImageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['inspect_task', 'detect_status', 'wayline']
    ordering_fields = ['created_at', 'id']
    ordering = ['id']

    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        导出巡检报表
        GET /api/v1/inspect-images/export/?start_date=2023-01-01&end_date=2023-01-31
        """
        import csv
        from django.http import HttpResponse
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = self.get_queryset()
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
            
        response = HttpResponse(content_type='text/csv')
        filename = f"inspection_report_{start_date or 'all'}_{end_date or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        # Add BOM for Excel compatibility with UTF-8
        response.write(u'\ufeff'.encode('utf8'))
        
        writer.writerow(['ID', 'Task', 'Wayline', 'Status', 'Image Path', 'Detect Type', 'Fault Items', 'Visible Items', 'Created At'])
        
        for item in queryset:
            task_name = item.inspect_task.external_task_id if item.inspect_task else '--'
            wayline_name = item.wayline.name if item.wayline else '--'
            status = item.get_detect_status_display()
            created_at = item.created_at.strftime('%Y-%m-%d %H:%M:%S')
            object_key = item.object_key
            
            # 解析 result 字段
            detect_type = ''
            fault_items = ''
            visible_items = ''
            
            if item.result:
                try:
                    result_data = item.result if isinstance(item.result, dict) else json.loads(str(item.result))
                    detect_type = result_data.get('detect_type', '')
                    
                    # 处理列表字段，转为逗号分隔字符串
                    faults = result_data.get('fault_items', [])
                    if isinstance(faults, list):
                        fault_items = ', '.join([str(f) for f in faults])
                    else:
                        fault_items = str(faults)
                        
                    visibles = result_data.get('visible_items', [])
                    if isinstance(visibles, list):
                        visible_items = ', '.join([str(v) for v in visibles])
                    else:
                        visible_items = str(visibles)
                except Exception as e:
                    print(f"Error parsing result for image {item.id}: {e}")
                    # 只有解析失败时才保留原始字符串，或者留空
                    pass
            
            writer.writerow([
                item.id,
                task_name,
                wayline_name,
                status,
                object_key,
                detect_type,
                fault_items,
                visible_items,
                created_at
            ])
            
        return response


