import os
import requests
from flask import Flask, render_template, request, send_file, jsonify
from pydub import AudioSegment
import io
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ENV VARIABLES
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
# Using the exact spelling you requested:
STABILITY_KEY = os.getenv("STABILTY_AI") 

# HUGGINGFACE MODELS
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

    if not prompt or not model_key:
        return jsonify({"error": "Missing prompt or model"}), 400

    audio_bytes = None

    # ---------------------------------------------------
    # OPTION A: STABILITY AI (Stable Audio)
    # ---------------------------------------------------
    if model_key == "stable-audio":
        if not STABILITY_KEY:
            return jsonify({"error": "Stability API Key (STABILTY_AI) is missing on server."}), 500

        api_url = "https://api.stability.ai/v2beta/audio/stable-audio-2/text-to-audio"
        
        headers = {
            "Authorization": f"Bearer {STABILITY_KEY}",
            "Accept": "audio/*"
        }
        
        # Stability requires multipart/form-data. 
        # We pass 'data' for fields and a dummy 'files' dict to force multipart request.
        body_data = {
            "prompt": prompt,
            "model": "stable-audio-2.0",
            "output_format": output_format, # mp3 or wav supported natively
            "duration": 30 # Defaulting to 30s to save your credits
        }
        
        # This "none" file trick forces the library to use multipart/form-data
        files = {"none": ""} 

        try:
            response = requests.post(api_url, headers=headers, data=body_data, files=files)
            
            if response.status_code != 200:
                # Try to parse error message from Stability
                try:
                    err_msg = response.json().get('errors', response.text)
                except:
                    err_msg = response.text
                return jsonify({"error": f"Stability Error ({response.status_code}): {err_msg}"}), response.status_code
                
            audio_bytes = response.content
            
            # If the user requested the same format Stability returned, we can return directly
            # But to be safe and allow conversions (like to m4a), we fall through to FFmpeg below.
            
        except Exception as e:
            return jsonify({"error": f"Connection Failed: {str(e)}"}), 500

    # ---------------------------------------------------
    # OPTION B: HUGGINGFACE MODELS (MusicGen / Riffusion)
    # ---------------------------------------------------
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
        return jsonify({"error": "Model not found"}), 404

    # ---------------------------------------------------
    # AUDIO CONVERSION (Standardize output)
    # ---------------------------------------------------
    try:
        if not audio_bytes:
            return jsonify({"error": "No audio data received"}), 500

        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        output_buffer = io.BytesIO()
        audio_segment.export(output_buffer, format=output_format)
        output_buffer.seek(0)
        
        mime = "audio/mp4" if output_format == "m4a" else f"audio/{output_format}"
        return send_file(output_buffer, mimetype=mime, as_attachment=True, download_name=f"generated.{output_format}")

    except Exception as e:
        return jsonify({"error": f"Processing Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
