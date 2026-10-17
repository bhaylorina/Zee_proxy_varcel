from flask import Flask, redirect, Response, request
import httpx
import json
import os
import logging
import traceback


# ==============================================================
# FLASK APP
# ==============================================================

app = Flask(__name__)


# ==============================================================
# LOGGING
# ==============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


# ==============================================================
# HOME
# ==============================================================

@app.route("/")
def home():
    return "Server is awake!", 200


# ==============================================================
# TOKENS / DEVICE
# ==============================================================

X_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwbGF0Zm9ybV9jb2RlIjoiYW5kcm9pZF90dkBhcHBsaWNhdGlvbiIsImlzc3VlZEF0IjoiMjAyNi0xMC0xN1QxMjozMDo1MC4wODRaIiwicHJvZHVjdF9jb2RlIjoiemVlNUA5NzUiLCJ0dGwiOjg2NDAwMDAwLCJpYXQiOjE3OTIyNDAyNTB9.eKmZfZ8VEP7ooNvKiLyYB2seGFaNMmvcwE8bRtwdiXo"
X_GUEST_TOKEN = "Z5X_b725b03106269f4955c84df62f0fd6fbd793eb8abc00fb5b62797202e707bb20"
X_DD_TOKEN = "eyJvc19uYW1lIjoiQW5kcm9pZCIsIm9zX3ZlcnNpb24iOiIxNyIsInBsYXRmb3JtX25hbWUiOiJzYW1zdW5nIiwicGxhdGZvcm1fdmVyc2lvbiI6IjM3IiwiZGV2aWNlX25hbWUiOiJTTS1TOTI4QiIsImFwcF9uYW1lIjoiY3R2X2FuZHJvaWQiLCJhcHBfdmVyc2lvbiI6IjUuOTAuNCIsInBsYXllcl9jYXBhYmlsaXRpZXMiOnsiYXVkaW9fY2hhbm5lbCI6WyJTVEVSRU8iXSwidmlkZW9fY29kZWMiOlsiSDI2NCIsIkhFVkMiXSwicmVzb2x1dGlvbiI6WyJIRCIsIkZIRCIsIlVIRCJdLCJkeW5hbWljX3JhbmdlIjpbIlNEUiIsIkhEUiIsIkhMRyIsIkhEUjEwKyJdfSwic2VjdXJpdHlfY2FwYWJpbGl0aWVzIjp7ImVuY3J5cHRpb24iOlsiV0lERVZJTkVfQUVTX0NUUiIsIldJREVWSU5FX0FFU19DQkNTIl0sIndpZGV2aW5lX3NlY3VyaXR5X2xldmVsIjpbIkwxIl0sImhkY3BfdmVyc2lvbiI6WyJIRENQX1YxIl19fQ=="

DEVICE_ID = "b1047afc-af02-4091-b212-89363a6f1b10"


# ==============================================================
# FILE / MEMORY CACHE
# ==============================================================

META_FILE = "channels_meta.json"

channels_dict = {}
pre_generated_m3u = ""


# ==============================================================
# LOAD CHANNEL METADATA
# ==============================================================

def load_and_prepare():

    global channels_dict

    logger.info("[STARTUP] Loading channel metadata...")

    if not os.path.exists(META_FILE):

        logger.error(
            f"[FATAL] {META_FILE} is MISSING!"
        )

        return

    try:

        with open(
            META_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        channels_dict = {
            ch["id"]: ch
            for ch in data
        }

        logger.info(
            f"[STARTUP] Successfully loaded "
            f"{len(channels_dict)} channels into RAM cache."
        )

    except json.JSONDecodeError:

        logger.exception(
            f"[STARTUP ERROR] {META_FILE} contains invalid JSON."
        )

    except Exception:

        logger.exception(
            "[STARTUP ERROR] Failed to load metadata."
        )


load_and_prepare()


# ==============================================================
# ZEE5 API FETCH ENGINE
# ==============================================================

def fetch_stream_url(channel_id, region_code):

    raw_query = (
        f"content_id"
        f"&show_id"
        f"&device_id={DEVICE_ID}"
        f"&session_id"
        f"&check_parental_control=false"
        f"&current_parental_control"
        f"&country={region_code}"
        f"&platform_name=ctv_android"
        f"&channel_id={channel_id}"
        f"&state={region_code}"
        f"&translation=en"
        f"&display_language=en"
        f"&user_language=hi%2Cmr%2Cte%2Ckn%2Cta%2Cml%2Cbn%2Cen"
        f"&collection_id"
        f"&app_version=5.90.4"
        f"&gender"
        f"&age=0"
        f"&brand=samsung"
        f"&model=SM-S928B"
        f"&utm_source"
        f"&utm_medium"
        f"&utm_campaign"
        f"&utm_term"
        f"&utm_content"
        f"&version=15"
        f"&is_marketing=0"
        f"&is_latest=0"
        f"&is_kids_profile=false"
    )

    url = (
        "https://spapi.zee5.com/"
        "singlePlayback/v2/getDetails/secure?"
        + raw_query
    )

    payload_str = (
        '{{"x-access-token":"{}","Authorization":"",'
        '"X-Z5-Guest-Token":"{}","x-dd-token":"{}"}}'
    ).format(
        X_ACCESS_TOKEN,
        X_GUEST_TOKEN,
        X_DD_TOKEN
    )

    headers = {
        "User-Agent":
            "com.graymatrix.did;Android TV;"
            "5.90.4(203231001);Android(17);"
            "samsung(SM-S928B)",

        "Accept": "*/*",

        "Accept-Encoding": "gzip",

        "g_id":
            "ae66e0cf-d257-4b55-9350-ddbd4982840c",

        "x-z5-appversion":
            "5.90.4",

        "x-z5-appversionnumber":
            "203231001",

        "x-z5-appplatform":
            "Android TV",

        "x-user-type":
            "guest",

        "x-access-token":
            X_ACCESS_TOKEN,

        "x-z5-device-id":
            DEVICE_ID,

        "x-z5-guest-token":
            X_GUEST_TOKEN,

        "content-type":
            "application/json; charset=utf-8"
    }


    # ----------------------------------------------------------
    # API REQUEST
    # ----------------------------------------------------------

    try:

        logger.info(
            f"[API] Requesting "
            f"channel={channel_id} "
            f"region={region_code}"
        )

        with httpx.Client(
            http2=True,
            timeout=8.0
        ) as client:

            resp = client.post(
                url,
                content=payload_str,
                headers=headers
            )


        # ------------------------------------------------------
        # BASIC RESPONSE LOG
        # ------------------------------------------------------

        logger.info(
            f"[API] channel={channel_id} "
            f"HTTP={resp.status_code} "
            f"bytes={len(resp.content)}"
        )


        # ------------------------------------------------------
        # NON-200 RESPONSE
        # ------------------------------------------------------

        if resp.status_code != 200:

            logger.error(
                f"[API ERROR] "
                f"channel={channel_id} "
                f"HTTP {resp.status_code}"
            )

            logger.error(
                f"[API ERROR BODY] "
                f"{resp.text[:5000]}"
            )

            return None


        # ------------------------------------------------------
        # JSON PARSE
        # ------------------------------------------------------

        try:

            data = resp.json()

        except Exception:

            logger.exception(
                f"[JSON ERROR] "
                f"channel={channel_id} "
                f"Response is not valid JSON."
            )

            logger.error(
                f"[RAW RESPONSE] "
                f"{resp.text[:5000]}"
            )

            return None


        # ------------------------------------------------------
        # CHECK keyOsDetails
        # ------------------------------------------------------

        if "keyOsDetails" not in data:

            logger.error(
                f"[API FORMAT ERROR] "
                f"channel={channel_id}: "
                f"'keyOsDetails' missing."
            )

            logger.error(
                "[RESPONSE JSON] "
                + json.dumps(
                    data,
                    ensure_ascii=False
                )[:10000]
            )

            return None


        # ------------------------------------------------------
        # CHECK video_token
        # ------------------------------------------------------

        if "video_token" not in data["keyOsDetails"]:

            logger.error(
                f"[TOKEN ERROR] "
                f"channel={channel_id}: "
                f"'video_token' missing."
            )

            logger.error(
                "[keyOsDetails] "
                + json.dumps(
                    data.get("keyOsDetails", {}),
                    ensure_ascii=False
                )[:10000]
            )

            return None


        # ------------------------------------------------------
        # SUCCESS
        # ------------------------------------------------------

        video_token = data["keyOsDetails"]["video_token"]

        logger.info(
            f"[SUCCESS] "
            f"channel={channel_id} "
            f"video_token received."
        )

        return video_token


    # ----------------------------------------------------------
    # HTTPX TIMEOUT
    # ----------------------------------------------------------

    except httpx.TimeoutException:

        logger.exception(
            f"[TIMEOUT] "
            f"channel={channel_id}: "
            f"ZEE5 API request timed out."
        )


    # ----------------------------------------------------------
    # HTTPX ERROR
    # ----------------------------------------------------------

    except httpx.HTTPError:

        logger.exception(
            f"[HTTPX ERROR] "
            f"channel={channel_id}"
        )


    # ----------------------------------------------------------
    # ANY OTHER ERROR
    # ----------------------------------------------------------

    except Exception:

        logger.exception(
            f"[UNKNOWN API ERROR] "
            f"channel={channel_id}"
        )


    return None


# ==============================================================
# ROUTE 1
# FAST 302 REDIRECTOR
# ==============================================================

@app.route("/play/<channel_file>")
def play_channel(channel_file):

    try:

        logger.info(
            f"[PLAY REQUEST] "
            f"{request.remote_addr} -> "
            f"{channel_file}"
        )


        # ------------------------------------------------------
        # REMOVE .m3u8
        # ------------------------------------------------------

        channel_id = channel_file.replace(
            ".m3u8",
            ""
        )


        # ------------------------------------------------------
        # GET REGION
        # ------------------------------------------------------

        channel_info = channels_dict.get(
            channel_id,
            {}
        )

        region = channel_info.get(
            "region",
            "IN"
        )


        logger.info(
            f"[PLAY] "
            f"channel={channel_id} "
            f"region={region}"
        )


        # ------------------------------------------------------
        # FETCH STREAM URL
        # ------------------------------------------------------

        stream_url = fetch_stream_url(
            channel_id,
            region
        )


        # ------------------------------------------------------
        # SUCCESS
        # ------------------------------------------------------

        if stream_url:

            logger.info(
                f"[PLAY SUCCESS] "
                f"{channel_id} "
                f"({region}) -> 302"
            )

            return redirect(
                stream_url,
                code=302
            )


        # ------------------------------------------------------
        # FAILED
        # ------------------------------------------------------

        logger.error(
            f"[PLAY FAILED] "
            f"{channel_id} "
            f"({region}) -> "
            f"No stream URL returned."
        )

        return (
            "Channel Unavailable or Token Expired",
            404
        )


    except Exception:

        logger.exception(
            f"[PLAY ROUTE ERROR] "
            f"channel_file={channel_file}"
        )

        return (
            "Internal Server Error",
            500
        )


# ==============================================================
# ROUTE 2
# INSTANT PRE-COMPILED PLAYLIST
# ==============================================================

@app.route("/playlist.m3u")
def get_playlist():

    global pre_generated_m3u

    try:

        logger.info(
            "[PLAYLIST] Playlist request received."
        )


        # ------------------------------------------------------
        # CHECK METADATA
        # ------------------------------------------------------

        if not channels_dict:

            logger.error(
                "[PLAYLIST ERROR] "
                "Channel metadata is empty."
            )

            return (
                "Metadata file missing on server",
                404
            )


        # ------------------------------------------------------
        # GENERATE ONLY ONCE
        # ------------------------------------------------------

        if not pre_generated_m3u:

            logger.info(
                "[PLAYLIST] "
                "Generating M3U in RAM..."
            )


            base_url = (
                request.host_url.rstrip("/")
            )


            m3u = "#EXTM3U\n"


            group_logo = (
                "https://yt3.googleusercontent.com/"
                "lyA_tGOMIiCHSVvdjC8ExJE3BsXMjyjipa1vL5g736p7Gu1mAkTDqLbMttOYMVdgvEs0NYEtZw="
                "s900-c-k-c0x00ffffff-no-rj"
            )


            tv_ua = (
                "com.graymatrix.did;Android TV;"
                "5.90.4(203231001);Android(17);"
                "samsung(SM-S928B)"
            )


            # --------------------------------------------------
            # LOOP CHANNELS
            # --------------------------------------------------

            for ch_id, ch_info in channels_dict.items():

                try:

                    name = ch_info.get(
                        "name",
                        ch_id
                    )

                    logo = ch_info.get(
                        "logo",
                        ""
                    )

                    region = ch_info.get(
                        "region",
                        "IN"
                    )


                    # --------------------------------------------------
                    # SMART CATEGORY
                    # --------------------------------------------------

                    category = "Entertainment"

                    name_lower = name.lower()


                    if any(
                        x in name_lower
                        for x in [
                            "news",
                            "taas",
                            "kalak",
                            "wion",
                            "today",
                            "bharatvarsh",
                            "profit",
                            "ndtv",
                            "asianet",
                            "aaj tak"
                        ]
                    ):

                        category = "News"


                    elif any(
                        x in name_lower
                        for x in [
                            "cinema",
                            "movie",
                            "picture",
                            "talkies",
                            "biskope",
                            "aflam",
                            "thirai"
                        ]
                    ):

                        category = "Movies"


                    elif region in [
                        "FR",
                        "CA",
                        "SG"
                    ]:

                        category = "International"


                    # --------------------------------------------------
                    # PLAY URL
                    # --------------------------------------------------

                    play_url = (
                        f"{base_url}/play/"
                        f"{ch_id}.m3u8"
                    )


                    # --------------------------------------------------
                    # EXTINF
                    # --------------------------------------------------

                    m3u += (
                        f'#EXTINF:-1 '
                        f'tvg-id="{ch_id}" '
                        f'tvg-name="{name}" '
                        f'tvg-logo="{logo}" '
                        f'tvg-category="{category}" '
                        f'group-title="ZEE5 Worldwide" '
                        f'group-logo="{group_logo}", '
                        f'{name}\n'
                    )


                    # --------------------------------------------------
                    # USER AGENT
                    # --------------------------------------------------

                    m3u += (
                        f"#EXTVLCOPT:http-user-agent="
                        f"{tv_ua}\n"
                    )


                    # --------------------------------------------------
                    # URL
                    # --------------------------------------------------

                    m3u += (
                        f"{play_url}\n"
                    )


                except Exception:

                    logger.exception(
                        f"[PLAYLIST CHANNEL ERROR] "
                        f"channel={ch_id}"
                    )


            # --------------------------------------------------
            # SAVE TO RAM
            # --------------------------------------------------

            pre_generated_m3u = m3u


            logger.info(
                "[PLAYLIST] "
                "M3U compiled successfully."
            )

            logger.info(
                f"[PLAYLIST] "
                f"Channels={len(channels_dict)} "
                f"Bytes={len(pre_generated_m3u)}"
            )


        else:

            logger.info(
                "[PLAYLIST] "
                "Serving cached M3U from RAM."
            )


        # ------------------------------------------------------
        # RETURN PLAYLIST
        # ------------------------------------------------------

        return Response(
            pre_generated_m3u,
            mimetype="application/x-mpegURL"
        )


    except Exception:

        logger.exception(
            "[PLAYLIST ROUTE ERROR]"
        )

        return (
            "Internal Server Error",
            500
        )


# ==============================================================
# GLOBAL FLASK ERROR HANDLER
# ==============================================================

@app.errorhandler(Exception)
def handle_unexpected_error(error):

    logger.exception(
        f"[FLASK ERROR] "
        f"{request.method} "
        f"{request.path}"
    )

    return (
        "Internal Server Error",
        500
    )


# ==============================================================
# HEALTH CHECK
# ==============================================================

@app.route("/healthz")
def healthz():

    return {
        "status": "ok",
        "channels": len(channels_dict)
    }, 200


# ==============================================================
# SERVER START
# ==============================================================

if __name__ == "__main__":

    logger.info(
        "=================================================="
    )

    logger.info(
        "🚀 ZEE5 UNIVERSAL GUEST PROXY SERVER STARTING 🚀"
    )

    logger.info(
        f"Channels loaded: {len(channels_dict)}"
    )

    logger.info(
        "=================================================="
    )

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
