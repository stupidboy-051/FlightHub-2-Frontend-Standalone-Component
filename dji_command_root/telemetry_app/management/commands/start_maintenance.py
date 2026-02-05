import time
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from telemetry_app.models import InspectTask, DronePosition

class Command(BaseCommand):
    help = '每日维护服务：重置任务状态并清理过期数据'

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
            # 实际上由于是 sleep 到点，醒来时已经是零点，所以直接算“明天零点”即可
            # 但为了防止刚启动时刚好是 00:00:01 导致 sleep 一整天，可以加个判断（虽然对于后台服务这通常没问题）
            # 这里简单起见，总是计算“明天零点”
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
            
            # 3. 稍微等待一下，防止计算误差导致立刻又进入循环判断（虽然逻辑上 next_run 是明天，不会重复）
            time.sleep(5)

    def perform_maintenance(self):
        self.stdout.write(self.style.WARNING("🔄 开始执行每日维护任务..."))
        
        try:
            # --- 任务 1: 重置未完成的任务 ---
            # 逻辑：将所有 'pending'(待检测) 和 'processing'(检测中) 的任务强制置为 'done'
            pending_tasks = InspectTask.objects.filter(detect_status__in=['pending', 'processing'])
            updated_count = pending_tasks.update(detect_status='done')
            self.stdout.write(self.style.SUCCESS(f"✅ 已重置 {updated_count} 个未完成任务为 'done'"))
            
            # --- 任务 2: 清理过期无人机位置数据 ---
            # 逻辑：保留最近 7 天的数据
            retention_days = 7
            cutoff_date = timezone.now() - datetime.timedelta(days=retention_days)
            deleted_info = DronePosition.objects.filter(timestamp__lt=cutoff_date).delete()
            # deleted_info 返回 (总数, {按表统计的字典})
            deleted_count = deleted_info[0]
            self.stdout.write(self.style.SUCCESS(f"✅ 已清理 {deleted_count} 条过期的无人机位置记录 (保留最近 {retention_days} 天)"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 维护任务执行出错: {str(e)}"))
        
        self.stdout.write("--------------------------------------------------")
