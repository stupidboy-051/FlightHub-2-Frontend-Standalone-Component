import time
import requests
import io
import datetime
import threading
from django.core.management.base import BaseCommand
from django.conf import settings
from telemetry_app.models import InspectTask, InspectImage, AlarmCategory
from telemetry_app.views import get_minio_client, auto_trigger_detect


class Command(BaseCommand):
    help = '启动保护区直播异常检测监听 (IP: 192.168.10.10)'

    def add_arguments(self, parser):
        parser.add_argument('--stream_id', type=str, required=True, help='流ID (例如 drone01)')
        parser.add_argument('--interval', type=float, default=3.0, help='截图间隔(秒)')

    def handle(self, *args, **options):
        stream_id = options['stream_id']
        interval = options['interval']

        # ================= 配置区 =================
        # Django (backend) 访问 ZLM 的内部地址
        ZLM_API_HOST = "http://zlm:80"
        ZLM_SECRET = "123456"  # 🔥 修复：与docker-compose中ZLM配置一致
        # =========================================

        # 1. 准备任务结构
        today_str = datetime.datetime.now().strftime('%Y%m%d')

        # 🔥 修改：使用与其他检测类型统一的父任务命名规则
        parent_task_id = f"{today_str}巡检任务"

        bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "dji")

        # A. 创建/获取父任务（与其他检测类型一致）
        parent_task, _ = InspectTask.objects.get_or_create(
            external_task_id=parent_task_id,
            defaults={
                "detect_status": "pending",  # 🔥 改为pending，与其他任务一致
                "bucket": bucket_name,
                "prefix_list": []  # 父任务没有具体路径
            }
        )

        # B. 确保有"保护区检测"这个分类
        category, _ = AlarmCategory.objects.get_or_create(
            code="protected_area",
            defaults={"name": "保护区", "match_keyword": "保护区"}
        )

        # C. 创建本次直播的子任务（命名与其他检测类型一致）
        now_time = datetime.datetime.now().strftime('%H%M%S')
        sub_task_id = f"{today_str}保护区检测直播_{stream_id}_{now_time}"

        # 定义上传路径前缀
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
            detect_status="processing"
        )

        print(f"🚀 [监听启动] Server: {ZLM_API_HOST} | Stream: {stream_id}")
        print(f"📂 [任务创建] [{parent_task_id}] -> [{sub_task_id}]")

        s3 = get_minio_client()

        # 2. 循环抽帧
        while True:
            try:
                # 1. 动态查找流信息
                media_list_api = f"{ZLM_API_HOST}/index/api/getMediaList"
                target_url = None
                
                try:
                    media_resp = requests.get(media_list_api, params={"secret": ZLM_SECRET}, timeout=5)
                    if media_resp.status_code == 200:
                        media_data = media_resp.json()
                        if media_data.get('code') == 0:
                            for item in media_data.get('data', []):
                                if item.get('stream') == stream_id:
                                    app_name = item.get('app')
                                    target_url = f"rtmp://127.0.0.1:1935/{app_name}/{stream_id}"
                                    break
                except Exception:
                    pass

                if not target_url:
                    print(f"⏳ [等待推流] 流 {stream_id} 未在线...")
                    time.sleep(interval)
                    continue

                # 2. 构造 ZLM 截图请求
                snap_api = f"{ZLM_API_HOST}/index/api/getSnap"
                params = {
                    "secret": ZLM_SECRET,
                    "url": target_url,
                    "timeout_sec": 15,
                    "expire_sec": 1
                }

                # 请求截图
                resp = requests.get(snap_api, params=params, timeout=20)

                if resp.status_code == 200:
                    image_data = None

                    # 智能判断: 如果是图片数据(FF D8开头)，直接用
                    if resp.content.startswith(b'\xff\xd8'):
                        image_data = resp.content
                    else:
                        # 否则尝试解析 JSON
                        try:
                            res_json = resp.json()
                            if res_json.get('code') == 0:
                                img_path = res_json.get('data')
                                if not img_path.startswith('http'):
                                    img_download_url = ZLM_API_HOST + img_path
                                else:
                                    img_download_url = img_path

                                img_resp = requests.get(img_download_url, timeout=10)
                                if img_resp.status_code == 200:
                                    image_data = img_resp.content
                        except Exception:
                            pass

                    # --- 上传逻辑 ---
                    if image_data:
                        file_bytes = io.BytesIO(image_data)
                        file_size = file_bytes.getbuffer().nbytes
                        fname = f"frame_{datetime.datetime.now().strftime('%H%M%S_%f')}.jpg"
                        object_key = f"{virtual_prefix}{fname}"

                        # 🔥【关键修复】Length 改为 ContentLength
                        s3.put_object(
                            Bucket=bucket_name,
                            Key=object_key,
                            Body=file_bytes,
                            ContentLength=file_size,
                            ContentType='image/jpeg'
                        )

                        # 入库
                        InspectImage.objects.create(
                            inspect_task=current_task,
                            object_key=object_key,
                            detect_status='pending',
                            wayline=current_task.wayline
                        )
                        print(f"📸 [截图成功] {fname} ({int(file_size / 1024)}KB) -> AI检测中...")

                        # 异步触发 AI
                        threading.Thread(target=auto_trigger_detect, args=(current_task,)).start()

                else:
                    print(f"📡 等待推流... Status: {resp.status_code}")

            except Exception as e:
                # 打印错误但不退出
                print(f"❌ 异常: {e}")

            time.sleep(interval)
