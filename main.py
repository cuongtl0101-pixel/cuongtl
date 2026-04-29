from flask import Flask, jsonify, request
import yt_dlp, os

app = Flask(__name__)
API_KEY = os.environ.get('API_KEY', 'changeme')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/get-url')
def get_url():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    video_id = request.args.get('id', '').strip()
    if not video_id:
        return jsonify({'error': 'Missing ?id=VIDEO_ID'}), 400

    ydl_opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )
            # Lấy URL từ format được chọn
            url = info.get('url')
            if not url and info.get('formats'):
                fmt = info['formats'][-1]
                url = fmt.get('url')

            if not url:
                return jsonify({'error': 'No URL found'}), 404

            return jsonify({
                'url': url,
                'title': info.get('title', ''),
                'quality': str(info.get('height', 'unknown')) + 'p',
                'ext': info.get('ext', 'mp4'),
                'duration': info.get('duration', 0)
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
