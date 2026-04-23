import os
import io
from flask import Flask, request, jsonify, send_file, send_from_directory
from openai import OpenAI
from pydub import AudioSegment
import imageio_ffmpeg
from dotenv import load_dotenv

load_dotenv()

AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

app = Flask(__name__, static_folder='static', static_url_path='')


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

    if not sentences:
        return jsonify({'error': 'No sentences provided'}), 400

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return jsonify({'error': 'Server is not configured with an OpenAI API key'}), 500

    client = OpenAI(api_key=api_key)
    combined = AudioSegment.empty()

    try:
        for sentence in sentences:
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=sentence,
                response_format='mp3'
            )
            segment = AudioSegment.from_mp3(io.BytesIO(response.content))
            silence_ms = int(len(sentence.split()) * pause_per_word * 1000)
            silence = AudioSegment.silent(duration=max(silence_ms, 0))
            for _ in range(repetitions):
                combined += segment + silence
    except Exception as e:
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
