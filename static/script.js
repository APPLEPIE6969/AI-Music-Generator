document.getElementById('generateBtn').addEventListener('click', async () => {
    const prompt = document.getElementById('promptInput').value;
    const model = document.getElementById('modelSelect').value;
    // Get selected radio button for format
    const format = document.querySelector('input[name="format"]:checked').value;
    
    const loading = document.getElementById('loading');
    const result = document.getElementById('result');
    const errorMsg = document.getElementById('errorMsg');
    const btn = document.getElementById('generateBtn');

    // Validation
    if(!prompt) {
        errorMsg.innerText = "Please describe the song you want to create.";
        errorMsg.classList.remove('hidden');
        return;
    }

    // Reset UI State
    errorMsg.classList.add('hidden');
    result.classList.add('hidden');
    loading.classList.remove('hidden');
    btn.disabled = true;
    btn.classList.add('opacity-50', 'cursor-not-allowed');

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt, model, format})
        });
        
        if(!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || "Generation failed on server.");
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        // Update Player and Download
        const player = document.getElementById('player');
        const download = document.getElementById('download');
        const fileLabel = document.getElementById('fileTypeLabel');

        player.src = url;
        download.href = url;
        download.download = `sonicforge_track.${format}`;
        fileLabel.innerText = format.toUpperCase();
        
        // Show Result
        result.classList.remove('hidden');
        loading.classList.add('hidden');

    } catch (e) {
        loading.classList.add('hidden');
        errorMsg.innerText = "Error: " + e.message;
        errorMsg.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
    }
});
