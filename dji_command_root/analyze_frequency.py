
import re
import sys
from datetime import datetime

def analyze_frequency(file_path, target_sn=None):
    print(f"📂 正在分析日志频率: {file_path}")
    print(f"🎯 目标SN: {target_sn if target_sn else '所有设备'}")
    print("=" * 60)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ 找不到文件: {file_path}")
        return

    # 分割消息块
    blocks = re.split(r'-{80}\n', content)
    
    # 存储时间戳
    timestamps = []
    
    # 消息类型统计
    type_counts = {
        'osd': 0,
        'events': 0,
        'requests': 0,
        'services_reply': 0,
        'other': 0
    }

    for block in blocks:
        if not block.strip():
            continue
            
        # 1. 提取 Topic
        topic_match = re.search(r'Topic: (.+)', block)
        if not topic_match:
            continue
        topic = topic_match.group(1).strip()
        
        # 如果指定了 SN，进行过滤
        if target_sn and target_sn not in topic and target_sn not in block:
            continue
            
        # 2. 提取时间戳
        # 格式: [2026-01-18 01:05:26.854]
        time_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]', block)
        if time_match:
            ts_str = time_match.group(1)
            ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S.%f')
            timestamps.append((ts, topic))
            
        # 3. 统计类型
        if '/osd' in topic:
            type_counts['osd'] += 1
        elif '/events' in topic:
            type_counts['events'] += 1
        elif '/requests' in topic:
            type_counts['requests'] += 1
        elif '/services_reply' in topic:
            type_counts['services_reply'] += 1
        else:
            type_counts['other'] += 1

    if not timestamps:
        print("⚠️ 未找到匹配的消息记录")
        return

    # 计算频率
    timestamps.sort(key=lambda x: x[0])
    start_time = timestamps[0][0]
    end_time = timestamps[-1][0]
    duration = (end_time - start_time).total_seconds()
    
    total_msgs = len(timestamps)
    avg_freq = total_msgs / duration if duration > 0 else 0
    
    print(f"\n📊 总体统计")
    print(f"   - 总消息数: {total_msgs}")
    print(f"   - 持续时间: {duration:.2f} 秒")
    print(f"   - 平均频率: {avg_freq:.2f} 条/秒")
    
    print(f"\n📑 消息类型分布")
    for k, v in type_counts.items():
        if v > 0:
            print(f"   - {k}: {v} 条 ({v/total_msgs*100:.1f}%)")

    # 专门分析 OSD (位置) 频率
    osd_times = [t[0] for t in timestamps if '/osd' in t[1]]
    if len(osd_times) > 1:
        intervals = []
        for i in range(1, len(osd_times)):
            diff = (osd_times[i] - osd_times[i-1]).total_seconds()
            intervals.append(diff)
            
        avg_interval = sum(intervals) / len(intervals)
        min_interval = min(intervals)
        max_interval = max(intervals)
        
        print(f"\n📍 位置信息 (OSD) 频率分析")
        print(f"   - OSD消息数: {len(osd_times)}")
        print(f"   - 平均间隔: {avg_interval:.3f} 秒 (约 {1/avg_interval:.2f} Hz)")
        print(f"   - 最小间隔: {min_interval:.3f} 秒")
        print(f"   - 最大间隔: {max_interval:.3f} 秒")
        
        print("\n   🔍 前10个间隔详情:")
        for i in range(min(10, len(intervals))):
            print(f"      {i+1}. {intervals[i]:.3f}s")
    else:
        print("\n📍 位置信息 (OSD) 频率分析")
        print("   ⚠️ OSD 消息数量不足以计算频率")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyze_frequency.py <日志文件路径> [SN过滤]")
    else:
        file = sys.argv[1]
        sn = sys.argv[2] if len(sys.argv) > 2 else None
        analyze_frequency(file, sn)
