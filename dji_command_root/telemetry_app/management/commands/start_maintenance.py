import time
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from telemetry_app.models import DronePosition

class Command(BaseCommand):
    help = '每日维护服务：清理过期无人机位置数据（分批处理）'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 [Maintenance] 每日维护服务启动...'))
        self.stdout.write(self.style.SUCCESS('📅 计划执行时间：每天北京时间 00:00 (UTC 16:00)'))

        while True:
            # 1. 获取当前时间并计算下次执行时间
            now_utc = timezone.now()
            
            # 转换为北京时间 (UTC+8) 用于计算零点
            beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
            now_bj = now_utc.astimezone(beijing_tz)
            
            # 计算下一个零点
            # 如果当前已经过了零点（但在同一天内），则目标是明天的零点
            next_run_bj = (now_bj + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 计算需要休眠的秒数
            sleep_seconds = (next_run_bj - now_bj).total_seconds()
            
            self.stdout.write(f"⏳ 当前时间(BJ): {now_bj.strftime('%Y-%m-%d %H:%M:%S')}")
            self.stdout.write(f"⏳ 下次执行(BJ): {next_run_bj.strftime('%Y-%m-%d %H:%M:%S')}")
            self.stdout.write(f"💤 进入休眠，等待 {sleep_seconds:.1f} 秒 ({sleep_seconds/3600:.2f} 小时)...")
            
            # 休眠直到下一天零点
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            
            # 2. 醒来执行任务
            self.perform_maintenance()
            
            # 3. 稍微等待一下，防止计算误差导致立刻又进入循环判断
            time.sleep(5)

    def perform_maintenance(self):
        self.stdout.write(self.style.WARNING("🔄 开始执行每日维护任务..."))
        
        try:
            # --- 任务: 分批清理过期无人机位置数据 ---
            # 逻辑：保留最近 7 天的数据，每次清理 5000 条
            retention_days = 7
            batch_size = 5000
            sleep_interval = 0.5  # 每批次间隔 0.5 秒
            
            cutoff_date = timezone.now() - datetime.timedelta(days=retention_days)
            total_deleted = 0
            
            self.stdout.write(f"🧹 开始清理 {cutoff_date} 之前的过期数据...")

            while True:
                # 1. 获取一批要删除的 ID
                # 注意：values_list + limit 是高效的获取 ID 方式
                delete_ids = list(
                    DronePosition.objects.filter(timestamp__lt=cutoff_date)
                    .values_list('id', flat=True)[:batch_size]
                )
                
                if not delete_ids:
                    self.stdout.write("✅ 没有更多过期数据需要清理。")
                    break
                
                count_to_delete = len(delete_ids)
                
                # 2. 根据 ID 执行删除
                DronePosition.objects.filter(id__in=delete_ids).delete()
                
                total_deleted += count_to_delete
                self.stdout.write(f"   - 已删除本批次 {count_to_delete} 条记录 (累计: {total_deleted})")
                
                # 3. 休息一下，避免长时间锁表
                time.sleep(sleep_interval)
                
            self.stdout.write(self.style.SUCCESS(f"🎉 维护完成！共清理 {total_deleted} 条过期的无人机位置记录 (保留最近 {retention_days} 天)"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 维护任务执行出错: {str(e)}"))
        
        self.stdout.write("--------------------------------------------------")
