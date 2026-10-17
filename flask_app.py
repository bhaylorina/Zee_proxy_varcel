from flask import Flask, redirect, Response, request
import httpx
import json
import os

app = Flask(__name__)
@app.route('/')
def home():
    return "Server is awake!", 200

# --- HARDCODED TOKENS ---
X_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwbGF0Zm9ybV9jb2RlIjoiYW5kcm9pZF90dkBhcHBsaWNhdGlvbiIsImlzc3VlZEF0IjoiMjAyNi0xMC0xM1QxMDo1MDowNS41MTJaIiwicHJvZHVjdF9jb2RlIjoiemVlNUA5NzUiLCJ0dGwiOjg2NDAwMDAwLCJpYXQiOjE3OTE4ODg2MDV9.CqMvAgCfsuO6ZvTZIZLIyYRrRT_za7602DUr1nDrxIM"
X_GUEST_TOKEN = "Z5X_3b73636a7f73e8cbde96003d2040a37b2ea727ab6292e7a93b36ba3b985f6278"
X_DD_TOKEN = "eyJvc19uYW1lIjoiQW5kcm9pZCIsIm9zX3ZlcnNpb24iOiIxNyIsInBsYXRmb3JtX25hbWUiOiJzYW1zdW5nIiwicGxhdGZvcm1fdmVyc2lvbiI6IjM3IiwiZGV2aWNlX25hbWUiOiJTTS1TOTI4QiIsImFwcF9uYW1lIjoiY3R2X2FuZHJvaWQiLCJhcHBfdmVyc2lvbiI6IjUuOTAuNCIsInBsYXllcl9jYXBhYmlsaXRpZXMiOnsiYXVkaW9fY2hhbm5lbCI6WyJTVEVSRU8iXSwidmlkZW9fY29kZWMiOlsiSDI2NCIsIkhFVkMiXSwicmVzb2x1dGlvbiI6WyJIRCIsIkZIRCJdLCJkeW5hbWljX3JhbmdlIjpbIlNEUiIsIkhEUiIsIkhMRyIsIkhEUjEwKyJdfSwic2VjdXJpdHlfY2FwYWJpbGl0aWVzIjp7ImVuY3J5cHRpb24iOlsiV0lERVZJTkVfQUVTX0NUUiIsIldJREVWSU5FX0FFU19DQkNTIl0sIndpZGV2aW5lX3NlY3VyaXR5X2xldmVsIjpbIkwxIl0sImhkY3BfdmVyc2lvbiI6WyJIRENQX1YxIl19fQ=="
DEVICE_ID = "b1047afc-af02-4091-b212-89363a6f1b10"

META_FILE = "channels_meta.json"
channels_dict = {}
pre_generated_m3u = ""

# --- IN-MEMORY CACHE LOAD ---
def load_and_prepare():
    global channels_dict
    if not os.path.exists(META_FILE):
        print(f"[-] FATAL: {META_FILE} is MISSING!")
        return
    try:
        with open(META_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        channels_dict = {ch['id']: ch for ch in data}
        print(f"[+] SUCCESS: Loaded {len(channels_dict)} channels into Fast RAM Cache.")
    except Exception as e:
        print(f"[-] Failed to read {META_FILE}. Error: {e}")

load_and_prepare()

# --- ZEE5 API FETCH ENGINE (RAW STRING BYPASS) ---
def fetch_stream_url(channel_id, region_code):
    raw_query = f"content_id&show_id&device_id={DEVICE_ID}&session_id&check_parental_control=false&current_parental_control&country={region_code}&platform_name=ctv_android&channel_id={channel_id}&state={region_code}&translation=en&display_language=en&user_language=hi%2Cmr%2Cte%2Ckn%2Cta%2Cml%2Cbn%2Cen&collection_id&app_version=5.90.4&gender&age=0&brand=samsung&model=SM-S928B&utm_source&utm_medium&utm_campaign&utm_term&utm_content&version=15&is_marketing=0&is_latest=0&is_kids_profile=false"
    url = f"https://spapi.zee5.com/singlePlayback/v2/getDetails/secure?{raw_query}"
    
    payload_str = '{{"x-access-token":"{}","Authorization":"","X-Z5-Guest-Token":"{}","x-dd-token":"{}"}}'.format(X_ACCESS_TOKEN, X_GUEST_TOKEN, X_DD_TOKEN)
    
    headers = {
        'User-Agent': "com.graymatrix.did;Android TV;5.90.4(203231001);Android(17);samsung(SM-S928B)",
        'Accept': "*/*",
        'Accept-Encoding': "gzip",
        'g_id': "ae66e0cf-d257-4b55-9350-ddbd4982840c",
        'x-z5-appversion': "5.90.4",
        'x-z5-appversionnumber': "203231001",
        'x-z5-appplatform': "Android TV",
        'x-user-type': "guest",
        'x-access-token': X_ACCESS_TOKEN,
        'x-z5-device-id': DEVICE_ID,
        'x-z5-guest-token': X_GUEST_TOKEN,
        'content-type': "application/json; charset=utf-8"
    }

    try:
        with httpx.Client(http2=True, timeout=8.0) as client:
            resp = client.post(url, content=payload_str, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if 'keyOsDetails' in data and 'video_token' in data['keyOsDetails']:
                    return data['keyOsDetails']['video_token']
    except Exception:
        pass
    return None

# ==============================================================
# ROUTE 1: FAST 302 REDIRECTOR (For Player)
# ==============================================================
@app.route('/play/<channel_file>')
def play_channel(channel_file):
    channel_id = channel_file.replace(".m3u8", "")
    region = channels_dict.get(channel_id, {}).get('region', 'IN')
    
    stream_url = fetch_stream_url(channel_id, region)
    
    if stream_url:
        print(f"[PLAY] {channel_id} ({region}) -> OK")
        return redirect(stream_url, code=302)
    else:
        print(f"[FAIL] {channel_id} ({region}) -> Blocked/Expired")
        return "Channel Unavailable or Token Expired", 404

# ==============================================================
# ROUTE 2: INSTANT PRE-COMPILED PLAYLIST
# ==============================================================
@app.route('/playlist.m3u')
def get_playlist():
    global pre_generated_m3u
    
    if not channels_dict:
        return "Metadata file missing on server", 404

    # Generate M3U ONCE and cache it in RAM to serve instantly
    if not pre_generated_m3u:
        base_url = request.host_url.rstrip('/')
        m3u = "#EXTM3U\n"
        group_logo = "https://yt3.googleusercontent.com/lyA_tGOMIiCHSVvdjC8ExJE3BsXMjyjipa1vL5g736p7Gu1mAkTDqLbMttOYMVdgvEs0NYEtZw=s900-c-k-c0x00ffffff-no-rj"
        tv_ua = "com.graymatrix.did;Android TV;5.90.4(203231001);Android(17);samsung(SM-S928B)"

        for ch_id, ch_info in channels_dict.items():
            name = ch_info.get("name", ch_id)
            logo = ch_info.get("logo", "")
            region = ch_info.get("region", "IN")
            
            # Smart Categories
            category = "Entertainment"
            name_lower = name.lower()
            if any(x in name_lower for x in ["news", "taas", "kalak", "wion", "today", "bharatvarsh", "profit", "ndtv", "asianet", "aaj tak"]):
                category = "News"
            elif any(x in name_lower for x in ["cinema", "movie", "picture", "talkies", "biskope", "aflam", "thirai"]):
                category = "Movies"
            elif region in ["FR", "CA", "SG"]:
                category = "International"

            play_url = f"{base_url}/play/{ch_id}.m3u8"
            
            m3u += f'#EXTINF:-1 tvg-id="{ch_id}" tvg-name="{name}" tvg-logo="{logo}" tvg-category="{category}" group-title="ZEE5 Worldwide" group-logo="{group_logo}", {name}\n'
            m3u += f'#EXTVLCOPT:http-user-agent={tv_ua}\n'
            m3u += f'{play_url}\n'
        
        pre_generated_m3u = m3u
        print("[+] M3U compiled to memory successfully.")

    return Response(pre_generated_m3u, mimetype='application/x-mpegURL')

if __name__ == "__main__":
    print("\n🚀 ZEE5 UNIVERSAL GUEST PROXY SERVER RUNNING! 🚀\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
    
