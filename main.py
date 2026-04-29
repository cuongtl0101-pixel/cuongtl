from flask import Flask, jsonify, request
import yt_dlp, os, tempfile, json

app = Flask(__name__)
API_KEY = os.environ.get('API_KEY', 'changeme')
COOKIES_FILE = '/app/cookies.txt'  # Mount hoặc set qua env

@app.route('/health')
def health():
    has_cookies = os.path.exists(COOKIES_FILE)
    return jsonify({'status': 'ok', 'cookies': has_cookies})

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
    }

    # Thêm cookies nếu có file
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )
            url = info.get('url')
            if not url and info.get('formats'):
                url = info['formats'][-1].get('url')

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

@app.route('/set-cookies', methods=['POST'])
def set_cookies():
    """Endpoint để upload cookies.txt content"""
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    content = request.data.decode('utf-8')
    if not content.strip():
        return jsonify({'error': 'Empty cookies'}), 400

    with open(COOKIES_FILE, 'w') as f:
        f.write(content)

    return jsonify({'status': 'ok', 'message': 'Cookies saved'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
