
import sys
import json
import re

def analyze_log(file_path):
    print(f"📂 正在分析日志文件: {file_path}")
    print("=" * 60)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ 找不到文件: {file_path}")
        return

    # 使用正则分割消息块
    # 匹配分隔符 "--------------------------------------------------------------------------------"
    blocks = re.split(r'-{80}\n', content)
    
    total_msgs = 0
    valid_position_msgs = 0
    ignored_msgs = 0
    
    for block in blocks:
        if not block.strip():
            continue
            
        # 提取 Topic
        topic_match = re.search(r'Topic: (.+)', block)
        if not topic_match:
            continue
            
        topic = topic_match.group(1).strip()
        total_msgs += 1
        
        # 提取完整 JSON
        # 优先找 "完整JSON: "，如果没有则尝试解析 Payload
        json_match = re.search(r'完整JSON: (.+)', block)
        data = None
        if json_match:
            try:
                data = json.loads(json_match.group(1))
            except:
                pass
        
        if data is None:
            # 尝试从 Payload 提取
            payload_match = re.search(r'Payload:\n(.+?)(\n\n|\Z)', block, re.DOTALL)
            if payload_match:
                try:
                    data = json.loads(payload_match.group(1))
                except:
                    pass

        # 开始诊断
        print(f"\n🔍 [消息 #{total_msgs}] Topic: {topic}")
        
        if data is None:
            print("   ⚠️  [跳过] 无法解析为 JSON，跳过分析")
            continue

        # 1. 检查 is_position_data 逻辑
        data_str = str(data)
        is_pos = ('osd' in topic) or \
                 ('latitude' in data_str) or \
                 ('lat' in data_str and 'lon' in data_str)
        
        if not is_pos:
            print("   ❌ [过滤] is_position_data = False")
            print("      原因: Topic不含'osd' 且 数据中无 'latitude' 或 'lat'/'lon'")
            ignored_msgs += 1
            continue
            
        print("   ✅ [通过] is_position_data = True")

        # 2. 检查 SN 提取
        sn = data.get('sn')
        topic_sn = None
        
        # 模拟 Topic SN 提取逻辑
        if '/osd' in topic or '/events' in topic:
            parts = topic.split('/')
            if topic.startswith('sys/') and len(parts) >= 5:
                topic_sn = parts[4]
            elif len(parts) >= 3:
                topic_sn = parts[2]
        
        final_sn = sn or topic_sn
        
        if not final_sn:
            print("   ❌ [失败] 无法提取 SN")
            print("      原因: Payload无'sn'字段，且无法从Topic提取")
            ignored_msgs += 1
            continue
            
        print(f"   ✅ [信息] 设备SN: {final_sn}")
        
        # 3. 检查设备类型
        if final_sn.startswith('8'):
            print("   🏭 [跳过] 识别为机场 (Dock)，不存入 DronePosition")
            continue
            
        # 4. 检查经纬度提取
        payload = data.get('data', data)
        lat = payload.get('latitude') or payload.get('lat')
        lon = payload.get('longitude') or payload.get('lon')
        
        # 尝试 output.ext
        if lat is None and 'output' in payload and 'ext' in payload['output']:
            ext = payload['output']['ext']
            lat = ext.get('latitude')
            lon = ext.get('longitude')
            print("   🔄 [信息] 尝试从 output.ext 提取坐标")

        if lat is not None and lon is not None:
            print(f"   🎉 [成功] 完整位置数据! -> 应该写入数据库")
            print(f"      坐标: ({lat}, {lon})")
            valid_position_msgs += 1
        else:
            print("   ❌ [失败] 经纬度提取失败")
            print(f"      数据预览: {list(payload.keys())}")
            ignored_msgs += 1

    print("\n" + "=" * 60)
    print("📊 分析总结")
    print(f"   - 总消息数: {total_msgs}")
    print(f"   - 有效位置消息 (理论应入库): {valid_position_msgs}")
    print(f"   - 被忽略/无效消息: {ignored_msgs}")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyze_logs.py <日志文件路径>")
    else:
        analyze_log(sys.argv[1])
