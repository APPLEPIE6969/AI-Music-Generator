import os
import requests
from flask import Flask, render_template, request, send_file, jsonify
from pydub import AudioSegment
import io
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- LOAD KEYS ---
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
UDIO_KEY = os.getenv("UDIO_AI")
STABILITY_MASTER = os.getenv("STABILTY_AI") # The single key

# Load the Pool (STABILITY_KEY_1 to STABILITY_KEY_100)
STABILITY_POOL = []
for i in range(1, 101):
    k = os.getenv(f"STABILITY_KEY_{i}")
    if k:
        STABILITY_POOL.append(k.strip())

print(f"✅ Server Ready: Loaded {len(STABILITY_POOL)} pool keys.")

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

    if not prompt: return jsonify({"error": "Please enter a prompt."}), 400

    audio_bytes = None

    # ==========================================
    # 1. STABLE AUDIO (SINGLE MASTER KEY)
    # ==========================================
    if model_key == "stable-audio-standard":
        if not STABILITY_MASTER:
            return jsonify({"error": "Master Key (STABILTY_AI) is missing."}), 500
        
        try:
            api_url = "https://api.stability.ai/v2beta/audio/stable-audio-2/text-to-audio"
            headers = {"Authorization": f"Bearer {STABILITY_MASTER}", "Accept": "audio/*"}
            body = {"prompt": prompt, "model": "stable-audio-2.0", "output_format": output_format}
            files = {"none": ""} 

            response = requests.post(api_url, headers=headers, data=body, files=files)
            
            if response.status_code == 200:
                audio_bytes = response.content
            else:
                return jsonify({"error": f"Stability Error: {response.text}"}), response.status_code
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==========================================
    # 2. STABLE AUDIO (INFINITE POOL CYCLE)
    # ==========================================
    elif model_key == "stable-audio-infinite":
        if not STABILITY_POOL:
            return jsonify({"error": "No pool keys (STABILITY_KEY_1...) found."}), 500
        
        success = False
        last_err = ""

        # Loop through keys until one works
        for index, api_key in enumerate(STABILITY_POOL):
            print(f"🔄 [Pool] Trying Key #{index+1}...")
            try:
                api_url = "https://api.stability.ai/v2beta/audio/stable-audio-2/text-to-audio"
                headers = {"Authorization": f"Bearer {api_key}", "Accept": "audio/*"}
                body = {"prompt": prompt, "model": "stable-audio-2.0", "output_format": output_format}
                files = {"none": ""} 

                response = requests.post(api_url, headers=headers, data=body, files=files)
                
                if response.status_code == 200:
                    print(f"✅ Success on Key #{index+1}")
                    audio_bytes = response.content
                    success = True
                    break
                else:
                    print(f"❌ Key #{index+1} Failed: {response.status_code}")
                    last_err = response.text
            except Exception as e:
                print(f"⚠️ Key #{index+1} Error: {e}")
                last_err = str(e)
                continue
        
        if not success:
            return jsonify({"error": f"All {len(STABILITY_POOL)} keys failed. Last: {last_err}"}), 500

    # ==========================================
    # 3. UDIO AI
    # ==========================================
    elif model_key == "udio":
        if not UDIO_KEY: return jsonify({"error": "Udio Key missing"}), 500
        try:
            api_url = "https://api.udio.com/v1/generate" 
            headers = {"Authorization": f"Bearer {UDIO_KEY}", "Content-Type": "application/json"}
            payload = {"prompt": prompt, "is_instrumental": False, "format": output_format}
            
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code == 200:
                ct = response.headers.get("Content-Type", "")
                if "application/json" in ct:
                    audio_bytes = requests.get(response.json()['audio_url']).content
                else:
                    audio_bytes = response.content
            else:
                return jsonify({"error": response.text}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==========================================
    # 4 & 5. HUGGINGFACE (MusicGen / Riffusion)
    # ==========================================
    elif model_key in HF_MODELS:
        try:
            response = requests.post(HF_MODELS[model_key], headers={"Authorization": f"Bearer {HF_API_TOKEN}"}, json={"inputs": prompt})
            if response.status_code == 200:
                audio_bytes = response.content
            else:
                return jsonify({"error": f"HF Error: {response.text}"}), 503
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Invalid Model Selection"}), 400

    # ==========================================
    # OUTPUT PROCESSING
    # ==========================================
    try:
        if not audio_bytes: return jsonify({"error": "No data received"}), 500
        
        seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
        buf = io.BytesIO()
        seg.export(buf, format=output_format)
        buf.seek(0)
        
        m = "audio/mp4" if output_format == "m4a" else f"audio/{output_format}"
        return send_file(buf, mimetype=m, as_attachment=True, download_name=f"generated.{output_format}")
    except Exception as e:
        return jsonify({"error": f"Processing Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
