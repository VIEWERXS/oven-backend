from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__)
CORS(app)

@app.route('/search')
def search():
    query = request.args.get('q', 'top hits')
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'extract_flat': True,
        'default_search': 'ytsearch15',
        'quiet': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch15:{query}", download=False)
            results = []
            for e in info.get('entries', []):
                if not e:
                    continue
                results.append({
                    'id': e.get('id'),
                    'title': e.get('title', 'Desconocido'),
                    'artist': e.get('uploader', 'Artista'),
                    'cover': f"https://i.ytimg.com/vi/{e.get('id')}/hqdefault.jpg",
                    'dur': e.get('duration') or 180
                })
            return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stream')
def stream():
    video_id = request.args.get('id')
    if not video_id:
        return jsonify({'error': 'No ID'}), 400
    url_yt = f"https://www.youtube.com/watch?v={video_id}" if len(video_id) == 11 else video_id
    ydl_opts = {'format': 'bestaudio[ext=m4a]/bestaudio/best', 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_yt, download=False)
            audio_url = info['url']
            headers = {}
            if 'Range' in request.headers:
                headers['Range'] = request.headers['Range']
            req = requests.get(audio_url, headers=headers, stream=True, timeout=20)
            resp_headers = {
                'Access-Control-Allow-Origin': '*',
                'Accept-Ranges': 'bytes',
                'Content-Type': req.headers.get('Content-Type', 'audio/mp4')
            }
            for h in ['Content-Length', 'Content-Range']:
                if h in req.headers:
                    resp_headers[h] = req.headers[h]
            return Response(
                stream_with_context(req.iter_content(chunk_size=32768)),
                status=req.status_code,
                headers=resp_headers
            )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
