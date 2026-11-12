from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app) # Permite que tu frontend OVEN se conecte sin bloqueos

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
            for e in info['entries']:
                results.append({
                    'id': e['id'],
                    'title': e.get('title', 'Desconocido'),
                    'artist': e.get('uploader', 'Desconocido'),
                    'cover': f"https://i.ytimg.com/vi/{e['id']}/hqdefault.jpg",
                    'dur': e.get('duration', 0),
                    'src': '' # Se llena al momento de reproducir
                })
            return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stream')
def stream():
    video_id = request.args.get('id')
    ydl_opts = {'format': 'bestaudio/best', 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_id, download=False)
            return jsonify({'url': info['url']})
    except:
        return jsonify({'error': 'Error extracting audio'}), 500
  
