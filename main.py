from flask import Flask, jsonify, request
import yt_dlp, os, tempfile

app = Flask(__name__)
API_KEY = os.environ.get('API_KEY', 'changeme')

def get_cookies_file():
    """Lấy cookies từ env var, ghi ra temp file"""
    cookies_content = os.environ.get('COOKIES_CONTENT', '')
    if not cookies_content:
        return None
    # Ghi ra temp file mỗi lần gọi (tránh mất file khi Render sleep)
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    tmp.write(cookies_content)
    tmp.close()
    return tmp.name

@app.route('/health')
def health():
    has_cookies = bool(os.environ.get('COOKIES_CONTENT', ''))
    return jsonify({'status': 'ok', 'cookies': has_cookies})

@app.route('/get-url')
def get_url():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    video_id = request.args.get('id', '').strip()
    if not video_id:
        return jsonify({'error': 'Missing ?id=VIDEO_ID'}), 400

    cookies_file = get_cookies_file()

    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    if cookies_file:
        opts['cookiefile'] = cookies_file

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )

        all_formats = info.get('formats') or []
        if not all_formats:
            return jsonify({'error': 'No formats returned'}), 404

        def score(f):
            has_url   = 1 if f.get('url') else 0
            has_audio = 1 if (f.get('acodec') and f.get('acodec') != 'none') else 0
            has_video = 1 if (f.get('vcodec') and f.get('vcodec') != 'none') else 0
            is_mp4    = 1 if f.get('ext') == 'mp4' else 0
            h = f.get('height') or 0
            q = 10 - abs(h - 720) / 100
            return has_url*100 + (has_audio+has_video)*10 + is_mp4*5 + q

        best = sorted(all_formats, key=score, reverse=True)[0]
        url  = best.get('url')
        if not url:
            return jsonify({'error': 'No URL in best format'}), 404

        return jsonify({
            'url':       url,
            'title':     info.get('title', ''),
            'quality':   str(best.get('height') or 'unknown') + 'p',
            'ext':       best.get('ext', 'mp4'),
            'format_id': best.get('format_id'),
            'duration':  info.get('duration', 0)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cookies_file and os.path.exists(cookies_file):
            os.unlink(cookies_file)

@app.route('/list-formats')
def list_formats():
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
    video_id = request.args.get('id', '').strip()
    if not video_id:
        return jsonify({'error': 'Missing ?id='}), 400
    cookies_file = get_cookies_file()
    opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    if cookies_file:
        opts['cookiefile'] = cookies_file
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f'https://www.youtube.com/watch?v={video_id}',
                download=False
            )
        formats = [{'format_id': f.get('format_id'), 'ext': f.get('ext'),
                    'vcodec': f.get('vcodec'), 'acodec': f.get('acodec'),
                    'height': f.get('height'), 'has_url': bool(f.get('url'))}
                   for f in (info.get('formats') or [])]
        return jsonify({'total': len(formats), 'formats': formats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if cookies_file and os.path.exists(cookies_file):
            os.unlink(cookies_file)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
