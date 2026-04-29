from flask import Flask, jsonify, request
import os, tempfile

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

    url = f'https://www.youtube.com/watch?v={video_id}'

    # Try pytubefix first
    try:
        from pytubefix import YouTube
        from pytubefix.cli import on_progress

        yt = YouTube(url, use_oauth=True, allow_oauth_cache=True)

        # Progressive stream: video+audio cùng file, tối đa 720p
        stream = (
            yt.streams.filter(progressive=True, file_extension='mp4')
              .order_by('resolution')
              .last()
        )

        if not stream:
            stream = yt.streams.get_lowest_resolution()

        if stream and stream.url:
            return jsonify({
                'url': stream.url,
                'title': yt.title,
                'quality': stream.resolution or 'unknown',
                'ext': 'mp4',
                'duration': yt.length
            })
    except Exception as e1:
        pass  # fallback to yt-dlp

    # Fallback: yt-dlp với cookies nếu có
    try:
        import yt_dlp

        cookies_content = os.environ.get('COOKIES_CONTENT', '')
        opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}

        if cookies_content:
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            tmp.write(cookies_content)
            tmp.close()
            opts['cookiefile'] = tmp.name

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        all_formats = info.get('formats') or []

        def score(f):
            has_url   = 1 if f.get('url') else 0
            has_audio = 1 if (f.get('acodec') and f.get('acodec') != 'none') else 0
            has_video = 1 if (f.get('vcodec') and f.get('vcodec') != 'none') else 0
            is_mp4    = 1 if f.get('ext') == 'mp4' else 0
            h = f.get('height') or 0
            q = 10 - abs(h - 720) / 100
            return has_url*100 + (has_audio+has_video)*10 + is_mp4*5 + q

        best = sorted(all_formats, key=score, reverse=True)[0]
        dl_url = best.get('url')
        if dl_url:
            return jsonify({
                'url': dl_url,
                'title': info.get('title', ''),
                'quality': str(best.get('height') or 'unknown') + 'p',
                'ext': best.get('ext', 'mp4'),
                'duration': info.get('duration', 0)
            })
    except Exception as e2:
        return jsonify({'error': f'Both methods failed. pytubefix: see logs. yt-dlp: {str(e2)}'}), 500

    return jsonify({'error': 'No URL found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
