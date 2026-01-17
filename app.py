import os
import requests
from flask import Flask, render_template, request, send_file, jsonify
from pydub import AudioSegment
import io
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
STABILITY_KEY = os.getenv("STABILTY_AI")
UDIO_KEY = os.getenv("UDIO_AI") 

# Open Source Models (HuggingFace)
HF_MODELS = {
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

    if not prompt:
        return jsonify({"error": "Please enter a prompt."}), 400

    audio_bytes = None

    # ==========================================
    # 1. STABILITY AI (Stable Audio)
    # ==========================================
    if model_key == "stable-audio":
        if not STABILITY_KEY:
            return jsonify({"error": "Stability API Key missing."}), 500

        api_url = "https://api.stability.ai/v2beta/audio/stable-audio-2/text-to-audio"
        headers = {"Authorization": f"Bearer {STABILITY_KEY}", "Accept": "audio/*"}
        
        # Multipart form data structure
        body_data = {
            "prompt": prompt,
            "model": "stable-audio-2.0",
            "output_format": output_format,
            "duration": 40 
        }
        files = {"none": ""} 

        try:
            response = requests.post(api_url, headers=headers, data=body_data, files=files)
            if response.status_code != 200:
                return jsonify({"error": f"Stability Error: {response.text}"}), response.status_code
            audio_bytes = response.content
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==========================================
    # 2. UDIO AI (Beta/Wrapper)
    # ==========================================
    elif model_key == "udio":
        if not UDIO_KEY:
            return jsonify({"error": "Udio API Key missing."}), 500

        # ⚠️ NOTE: Replace this URL with your specific Udio Provider/Wrapper URL
        # Example: generic placeholder or specific wrapper endpoint
        api_url = "https://api.udio.com/v1/generate" 
        
        headers = {
            "Authorization": f"Bearer {UDIO_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "is_instrumental": False,
            "format": output_format
        }

        try:
            # Udio generation is often async (returns a task ID). 
            # If your API returns audio bytes directly, this works.
            # If it returns a JSON with a URL, we catch that below.
            response = requests.post(api_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                return jsonify({"error": f"Udio Error: {response.text}"}), response.status_code
            
            # Check if response is JSON (URL) or Bytes (Audio)
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                resp_json = response.json()
                if 'audio_url' in resp_json:
                    # Download from the URL provided by Udio
                    audio_bytes = requests.get(resp_json['audio_url']).content
                else:
                    return jsonify({"error": "Udio generation started but no audio URL found yet (Async API?)"}), 200
            else:
                audio_bytes = response.content

        except Exception as e:
            return jsonify({"error": f"Udio Connection Failed: {str(e)}"}), 500

    # ==========================================
    # 3. OPEN SOURCE (MusicGen / Riffusion)
    # ==========================================
    elif model_key in HF_MODELS:
        api_url = HF_MODELS[model_key]
        headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
        payload = {"inputs": prompt}

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code != 200:
                return jsonify({"error": f"HuggingFace Error: {response.text}"}), 503
            audio_bytes = response.content
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Invalid Model Selected"}), 400

    # ==========================================
    # AUDIO PROCESSING & RETURN
    # ==========================================
    try:
        if not audio_bytes:
            return jsonify({"error": "No audio data received."}), 500

        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        output_buffer = io.BytesIO()
        audio_segment.export(output_buffer, format=output_format)
        output_buffer.seek(0)
        
        mime = "audio/mp4" if output_format == "m4a" else f"audio/{output_format}"
        return send_file(output_buffer, mimetype=mime, as_attachment=True, download_name=f"generated_track.{output_format}")

    except Exception as e:
        return jsonify({"error": f"Processing Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
