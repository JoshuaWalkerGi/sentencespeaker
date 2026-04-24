import os
import io
import traceback
import subprocess
from flask import Flask, request, jsonify, send_file, send_from_directory
from openai import OpenAI
from pydub import AudioSegment
import imageio_ffmpeg
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')

# Set converter once at startup so export() works
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()


def _mp3_to_segment(mp3_bytes):
    """Decode MP3 bytes via ffmpeg to raw PCM, bypassing pydub's ffprobe dependency."""
    proc = subprocess.run(
        [AudioSegment.converter, '-hide_banner', '-loglevel', 'error',
         '-i', 'pipe:0', '-f', 's16le', '-ac', '1', '-ar', '24000', 'pipe:1'],
        input=mp3_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed: {proc.stderr.decode(errors='replace')}")
    return AudioSegment(data=proc.stdout, sample_width=2, frame_rate=24000, channels=1)


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.get_json()
    sentences = data.get('sentences', [])
    repetitions = int(data.get('repetitions', 5))
    pause_per_word = float(data.get('pause_per_word', 2.0))
    voice = data.get('voice', 'nova')
    model = data.get('model', 'tts-1')
    accent = data.get('accent', 'default')

    accent_instructions = {
        'es-es': 'You are a native Spanish speaker from Spain. Speak with a natural Castilian Spanish accent and pronunciation.',
        'es-latam': 'You are a native Spanish speaker from Latin America. Speak with a natural Latin American Spanish accent and pronunciation.',
    }
    instructions = accent_instructions.get(accent)
    if instructions:
        model = 'gpt-4o-mini-tts'

    if not sentences:
        return jsonify({'error': 'No sentences provided'}), 400

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return jsonify({'error': 'Server is not configured with an OpenAI API key'}), 500

    client = OpenAI(api_key=api_key)
    combined = AudioSegment.empty()

    try:
        for sentence in sentences:
            tts_params = dict(model=model, voice=voice, input=sentence, response_format='mp3')
            if instructions:
                tts_params['instructions'] = instructions
            response = client.audio.speech.create(**tts_params)
            mp3_bytes = response.content if hasattr(response, 'content') else response.read()
            segment = _mp3_to_segment(mp3_bytes)
            silence_ms = int(len(sentence.split()) * pause_per_word * 1000)
            silence = AudioSegment.silent(duration=max(silence_ms, 0))
            for _ in range(repetitions):
                combined += segment + silence
    except Exception as e:
        print(f"[generate error] {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

    buf = io.BytesIO()
    combined.export(buf, format='mp3')
    buf.seek(0)

    return send_file(
        buf,
        mimetype='audio/mpeg',
        as_attachment=True,
        download_name='sentences_audio.mp3'
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
