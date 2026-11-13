import os, sys, time, threading
# Asegura que el binario de deno (instalado con pip) esté en el PATH para yt-dlp
os.environ["PATH"] = os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", "")

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__)
CORS(app, expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"])

BASE_OPTS = {"quiet": True, "noplaylist": True}
if os.path.exists("cookies.txt"):           # opcional: ver nota en el chat
    BASE_OPTS["cookiefile"] = "cookies.txt"

_cache, _lock = {}, threading.Lock()        # el <audio> pide varios Range: no re-extraer cada vez
TTL = 15 * 60


def get_info(video_id):
    now = time.time()
    with _lock:
        hit = _cache.get(video_id)
        if hit and now - hit[0] < TTL:
            return hit[1]
    opts = {**BASE_OPTS, "format": "bestaudio[ext=m4a]/bestaudio/best"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    data = {"url": info["url"], "headers": info.get("http_headers", {})}
    with _lock:
        _cache[video_id] = (now, data)
    return data


@app.route("/")
def health():
    return jsonify({"ok": True, "yt_dlp": yt_dlp.version.__version__})


@app.route("/search")
def search():
    query = request.args.get("q", "top hits")
    opts = {**BASE_OPTS, "extract_flat": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch15:{query}", download=False)
        results = [{
            "id": e.get("id"),
            "title": e.get("title", "Desconocido"),
            "artist": e.get("uploader") or e.get("channel") or "Artista",
            "cover": f"https://i.ytimg.com/vi/{e.get('id')}/hqdefault.jpg",
            "dur": e.get("duration") or 180,
        } for e in info.get("entries", []) if e]
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)[:300]}), 500


@app.route("/stream")
def stream():
    vid = request.args.get("id", "")
    if len(vid) != 11:
        return jsonify({"error": "ID inválido"}), 400
    try:
        data = get_info(vid)
        headers = dict(data["headers"])               # imprescindible: sin esto googlevideo da 403
        if "Range" in request.headers:
            headers["Range"] = request.headers["Range"]
        up = requests.get(data["url"], headers=headers, stream=True, timeout=20)
        if up.status_code >= 400:
            with _lock:
                _cache.pop(vid, None)
            return jsonify({"error": f"googlevideo HTTP {up.status_code}"}), 502
        h = {"Accept-Ranges": "bytes", "Content-Type": up.headers.get("Content-Type", "audio/mp4")}
        for k in ("Content-Length", "Content-Range"):
            if k in up.headers:
                h[k] = up.headers[k]
        return Response(stream_with_context(up.iter_content(chunk_size=65536)),
                        status=up.status_code, headers=h)
    except Exception as e:
        with _lock:
            _cache.pop(vid, None)
        return jsonify({"error": str(e)[:300]}), 500
                                
