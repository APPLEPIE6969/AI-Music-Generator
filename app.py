import os
import requests
from flask import Flask, render_template, request, send_file, jsonify
from pydub import AudioSegment
import io
# This loads the .env file locally, but does nothing on Render (which is fine)
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# GET KEY FROM ENVIRONMENT
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

MODELS = {
    "musicgen": "https://api-inference.huggingface.co/models/facebook/musicgen-small",
    "riffusion": "https://api-inference.huggingface.co/models/riffusion/riffusion-model-v1",
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_music():
    data = request.json
    prompt = data.get('prompt')
    model_key = data.get('model')
    output_format = data.get('format', 'mp3')

    if not prompt or not model_key:
        return jsonify({"error": "Missing prompt or model"}), 400

    if model_key not in MODELS:
        return jsonify({"error": "Model not found"}), 404

    api_url = MODELS[model_key]
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": prompt}

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code != 200:
            return jsonify({"error": f"API Error: {response.text}"}), 503
        audio_bytes = response.content
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    try:
        # CONVERT AUDIO
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        output_buffer = io.BytesIO()
        audio_segment.export(output_buffer, format=output_format)
        output_buffer.seek(0)
        
        mime = "audio/mp4" if output_format == "m4a" else f"audio/{output_format}"
        return send_file(output_buffer, mimetype=mime, as_attachment=True, download_name=f"generated.{output_format}")
    except Exception as e:
        return jsonify({"error": f"FFmpeg Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
