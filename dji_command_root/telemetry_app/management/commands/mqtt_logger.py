import json
import os
import time
import random
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
import paho.mqtt.client as mqtt


class Command(BaseCommand):
    help = 'MQTT 日志记录器：将所有消息保存到文件供后续分析'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='mqtt_messages.log',
            help='日志输出文件路径 (默认: mqtt_messages.log)'
        )
        parser.add_argument(
            '--max-messages',
            type=int,
            default=10000,
            help='最大记录消息数量 (默认: 10000，0 表示无限制)'
        )
        parser.add_argument(
            '--duration',
            type=int,
            default=0,
            help='记录时长（秒），0 表示持续记录 (默认: 0)'
        )
        parser.add_argument(
            '--filter',
            type=str,
            default='',
            help='关键词过滤：只记录包含此字符串的消息'
        )
        parser.add_argument(
            '--sn',
            type=str,
            default='',
            help='SN过滤：只记录指定SN设备的消息'
        )

    def handle(self, *args, **options):
        # 配置参数
        output_file = options['output']
        self.max_messages = options['max_messages']
        self.duration = options['duration']
        self.filter_keyword = options['filter']
        self.filter_sn = options['sn']

        # MQTT 连接配置
        broker_ip = os.getenv('MQTT_BROKER_IP', 'my_emqx')
        broker_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
        username = os.getenv('MQTT_USER', '')
        password = os.getenv('MQTT_PASSWORD', '')

        # 状态变量
        self.message_count = 0
        self.start_time = time.time()
        self.log_file = open(output_file, 'w', encoding='utf-8')

        # 写入文件头
        self.log_file.write("=" * 80 + "\n")
        self.log_file.write(f"MQTT 消息日志记录\n")
        self.log_file.write(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.log_file.write(f"Broker: {broker_ip}:{broker_port}\n")
        self.log_file.write(f"最大消息数: {self.max_messages if self.max_messages > 0 else '无限制'}\n")
        self.log_file.write(f"记录时长: {self.duration}秒\n" if self.duration > 0 else "记录时长: 持续记录\n")
        self.log_file.write("=" * 80 + "\n\n")

        self.stdout.write(self.style.SUCCESS(f"📝 MQTT 日志记录器启动"))
        self.stdout.write(f"   - 输出文件: {output_file}")
        self.stdout.write(f"   - Broker: {broker_ip}:{broker_port}")
        self.stdout.write(f"   - 最大消息数: {self.max_messages if self.max_messages > 0 else '无限制'}")
        self.stdout.write(f"   - 记录时长: {self.duration}秒" if self.duration > 0 else "   - 记录时长: 持续记录")
        if self.filter_keyword:
            self.stdout.write(f"   - 关键词过滤: {self.filter_keyword}")
        if self.filter_sn:
            self.stdout.write(f"   - SN过滤: {self.filter_sn}")

        # 初始化 MQTT 客户端
        client_id = f"mqtt_logger_{random.randint(10000, 99999)}"
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        client.keepalive = 60

        if username:
            client.username_pw_set(username, password)

        # 绑定回调
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect

        try:
            # 开始连接循环
            self.stdout.write(f"🚀 正在连接到 EMQX...")
            client.connect(broker_ip, broker_port, 60)
            client.loop_forever()

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n⚠️  收到停止信号，正在保存日志..."))
            self.finalize_log()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 错误: {e}"))
            self.finalize_log()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """连接成功后订阅主题"""
        if rc == 0:
            self.stdout.write(self.style.SUCCESS('✅ 连接成功! 正在订阅主题...'))

            # 订阅所有司空相关主题
            topics = [
                ("thing/product/+/osd", 0),
                ("thing/product/+/events", 1),
                ("thing/product/+/services_reply", 1),
                ("thing/product/+/requests", 0),
                ("thing/product/+/drc/up", 0),  # 遥控器上行
                ("thing/product/+/drc/down", 0),  # 遥控器下行
                ("sys/product/+/+/osd", 0),
                ("sys/product/+/+/events", 1),
            ]
            client.subscribe(topics)
            self.stdout.write(f"   - 已订阅 {len(topics)} 类主题")
        else:
            self.stdout.write(self.style.ERROR(f'❌ 连接失败，返回码: {rc}'))

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        if rc != 0:
            self.stdout.write(self.style.WARNING('⚠️  连接断开，尝试重连...'))

    def on_message(self, client, userdata, msg):
        """记录所有消息到文件"""
        try:
            payload = msg.payload.decode('utf-8')
            
            # --- 过滤逻辑 ---
            if self.filter_sn and self.filter_sn not in msg.topic and self.filter_sn not in payload:
                return
            if self.filter_keyword and self.filter_keyword not in payload and self.filter_keyword not in msg.topic:
                return
            
            self.message_count += 1
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

            # 解析消息
            is_json = False
            try:
                data = json.loads(payload)
                payload_preview = json.dumps(data, ensure_ascii=False)[:500]
                is_json = True
            except:
                payload_preview = str(payload)[:500]

            # 写入日志文件
            self.log_file.write("-" * 80 + "\n")
            self.log_file.write(f"[{current_time}] 消息 #{self.message_count}\n")
            self.log_file.write(f"Topic: {msg.topic}\n")
            self.log_file.write(f"QoS: {msg.qos} | 大小: {len(msg.payload)} bytes\n")
            self.log_file.write(f"Payload:\n{payload_preview}...\n")
            
            if is_json:
                self.log_file.write(f"完整JSON: {json.dumps(data, ensure_ascii=False)}\n")
            
            self.log_file.write("\n")

            # 实时显示进度
            if self.message_count % 10 == 0:
                elapsed = time.time() - self.start_time
                self.stdout.write(f"📨 已记录 {self.message_count} 条消息 (运行 {elapsed:.0f}秒)")

            # 检查是否达到限制
            if self.max_messages > 0 and self.message_count >= self.max_messages:
                self.stdout.write(self.style.SUCCESS(f"\n✅ 已达到最大消息数限制 ({self.max_messages})"))
                self.finalize_log()
                client.disconnect()

            # 检查时长限制
            if self.duration > 0:
                elapsed = time.time() - self.start_time
                if elapsed >= self.duration:
                    self.stdout.write(self.style.SUCCESS(f"\n✅ 已达到记录时长限制 ({self.duration}秒)"))
                    self.finalize_log()
                    client.disconnect()

            # 定期刷新文件缓冲区
            if self.message_count % 50 == 0:
                self.log_file.flush()

        except Exception as e:
            self.log_file.write(f"❌ 记录消息时出错: {e}\n\n")

    def finalize_log(self):
        """完成日志记录"""
        elapsed = time.time() - self.start_time
        self.log_file.write("\n" + "=" * 80 + "\n")
        self.log_file.write(f"日志记录结束\n")
        self.log_file.write(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.log_file.write(f"总消息数: {self.message_count}\n")
        self.log_file.write(f"运行时长: {elapsed:.1f}秒\n")
        self.log_file.write("=" * 80 + "\n")
        self.log_file.close()

        self.stdout.write(self.style.SUCCESS(f"\n✅ 日志已保存到文件"))
        self.stdout.write(f"   - 总消息数: {self.message_count}")
        self.stdout.write(f"   - 运行时长: {elapsed:.1f}秒")
