from flask import Flask, jsonify, request
import yt_dlp, os

app = Flask(__name__)
API_KEY = os.environ.get('API_KEY', 'changeme')
COOKIES_FILE = '/app/cookies.txt'

def get_ydl_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    return opts

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'cookies': os.path.exists(COOKIES_FILE)})

@app.route('/set-cookies', methods=['POST'])
def set_cookies():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
    content = request.data.decode('utf-8')
    if not content.strip():
        return jsonify({'error': 'Empty cookies'}), 400
    with open(COOKIES_FILE, 'w') as f:
        f.write(content)
    return jsonify({'status': 'ok'})

@app.route('/list-formats')
def list_formats():
    """Debug: xem tất cả formats có sẵn"""
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
    video_id = request.args.get('id', '').strip()
    if not video_id:
        return jsonify({'error': 'Missing ?id='}), 400
    try:
        opts = get_ydl_opts()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )
            formats = []
            for f in (info.get('formats') or []):
                formats.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'vcodec': f.get('vcodec'),
                    'acodec': f.get('acodec'),
                    'height': f.get('height'),
                    'filesize': f.get('filesize'),
                    'has_url': bool(f.get('url'))
                })
            return jsonify({'total': len(formats), 'formats': formats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-url')
def get_url():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
    video_id = request.args.get('id', '').strip()
    if not video_id:
        return jsonify({'error': 'Missing ?id=VIDEO_ID'}), 400

    try:
        # Bước 1: lấy toàn bộ formats, không filter
        opts = get_ydl_opts()
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )

        all_formats = info.get('formats') or []
        if not all_formats:
            return jsonify({'error': 'No formats returned'}), 404

        # Bước 2: chọn format tốt nhất có URL
        # Ưu tiên: có cả video+audio, mp4, gần 720p
        def score(f):
            has_url = 1 if f.get('url') else 0
            has_audio = 1 if (f.get('acodec') and f.get('acodec') != 'none') else 0
            has_video = 1 if (f.get('vcodec') and f.get('vcodec') != 'none') else 0
            is_mp4 = 1 if f.get('ext') == 'mp4' else 0
            h = f.get('height') or 0
            quality_score = 10 - abs(h - 720) / 100
            return has_url * 100 + (has_audio + has_video) * 10 + is_mp4 * 5 + quality_score

        best = sorted(all_formats, key=score, reverse=True)[0]
        url = best.get('url')

        if not url:
            return jsonify({'error': 'Best format has no URL'}), 404

        return jsonify({
            'url': url,
            'title': info.get('title', ''),
            'quality': str(best.get('height') or 'unknown') + 'p',
            'ext': best.get('ext', 'mp4'),
            'format_id': best.get('format_id'),
            'duration': info.get('duration', 0)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
