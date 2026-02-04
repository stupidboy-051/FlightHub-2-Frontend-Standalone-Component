
import os
import sys
import argparse
import django
import requests

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dji_command_root.settings")
django.setup()

from telemetry_app.views import WaylineFingerprintManager, normalize_detect_code
from telemetry_app.models import AlarmCategory, Wayline, WaylineFingerprint

def list_waylines():
    print("Fetching waylines from API...")
    try:
        headers, base_url = WaylineFingerprintManager.get_api_headers_and_host()
        list_url = f"{base_url}/openapi/v0.1/wayline"
        res = requests.get(list_url, headers=headers, params={"page": 1, "page_size": 500}, timeout=15)
        
        if res.status_code != 200:
            print(f"Error: API returned {res.status_code} - {res.text}")
            return

        data = res.json().get('data', {})
        wayline_list = data.get('list', []) if isinstance(data, dict) else data
        
        print(f"\nFound {len(wayline_list)} waylines:")
        print("-" * 120)
        print(f"{'ID':<38} | {'Name':<40} | {'Status':<15} | {'Match'}")
        print("-" * 120)
        
        categories = AlarmCategory.objects.filter(parent__isnull=True)
        
        for item in wayline_list:
            w_id = item.get('id')
            w_name = item.get('name')
            w_name_lower = str(w_name).lower()
            
            # Try to match
            matched_cat = None
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
                        matched_cat = cat
                        break
                if matched_cat:
                    break
            
            match_str = f"✅ {matched_cat.name}" if matched_cat else "❌ No Match"
            
            # Check DB status
            db_status = "Not in DB"
            existing = Wayline.objects.filter(wayline_id=w_id).first()
            if existing:
                db_status = "In DB"
                if hasattr(existing, 'fingerprint'):
                    db_status += " (Has FP)"
                else:
                    db_status += " (No FP)"
            
            print(f"{w_id:<38} | {str(w_name)[:40]:<40} | {db_status:<15} | {match_str}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def force_sync(wayline_id, force_type=None):
    print(f"Force syncing wayline ID: {wayline_id}...")
    try:
        headers, base_url = WaylineFingerprintManager.get_api_headers_and_host()
        
        # 1. Get Details first to get name
        detail_url = f"{base_url}/openapi/v0.1/wayline/{wayline_id}"
        res = requests.get(detail_url, headers=headers, timeout=10)
        
        if res.status_code != 200:
             print(f"Error: Failed to get wayline details. HTTP {res.status_code}")
             print(f"Response: {res.text}")
             return
             
        data = res.json().get('data', {})
        w_name = data.get('name', f"Wayline-{wayline_id}")
        print(f"Target Name: {w_name}")
        
        # 2. Determine Category
        category_obj = None
        categories = AlarmCategory.objects.filter(parent__isnull=True)
        
        if force_type:
            print(f"Using forced type: {force_type}")
            # Try to find category by code
            for c in categories:
                if normalize_detect_code(c.code) == normalize_detect_code(force_type):
                    category_obj = c
                    break
            if not category_obj:
                print(f"Error: Could not find AlarmCategory for type '{force_type}'")
                print("Available types: " + ", ".join([c.code for c in categories]))
                return
        else:
            # Auto-detect
            print("Auto-detecting category...")
            w_name_lower = str(w_name).lower()
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
                        category_obj = cat
                        break
                if category_obj:
                    break
            
            if not category_obj:
                print("⚠️  Keyword matching failed.")
                print("❌ Cannot determine category automatically. Please use --type <code (e.g. protected_area)>")
                return

        print(f"Selected Category: {category_obj.name} ({category_obj.code})")
        
        # 3. Process
        print("Starting processing...")
        WaylineFingerprintManager.process_single_wayline(
            base_url, headers, wayline_id, w_name, category_obj
        )
        print("Done.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manual Wayline Sync Tool")
    parser.add_argument("--list", action="store_true", help="List all waylines from API and their match status")
    parser.add_argument("--sync", type=str, help="Force sync a wayline by ID")
    parser.add_argument("--type", type=str, help="Force specific detection type (e.g. protected_area, rail)")
    
    args = parser.parse_args()
    
    if args.list:
        list_waylines()
    elif args.sync:
        force_sync(args.sync, args.type)
    else:
        parser.print_help()
