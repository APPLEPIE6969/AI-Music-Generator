document.getElementById('generateBtn').addEventListener('click', async () => {
    const prompt = document.getElementById('promptInput').value;
    const model = document.getElementById('modelSelect').value;
    const format = document.getElementById('formatSelect').value;
    const statusMsg = document.getElementById('statusMessage');
    const resultArea = document.getElementById('resultArea');
    const btn = document.getElementById('generateBtn');

    // Validation
    if (!prompt) {
        alert("Please enter a text prompt.");
        return;
    }

    // UI: Set Loading State
    btn.disabled = true;
    btn.innerHTML = `<div class="loader"></div> Generating...`;
    statusMsg.classList.remove('hidden', 'text-red-400');
    statusMsg.classList.add('text-slate-300');
    statusMsg.innerText = "Contacting model... this may take 10-60 seconds.";
    resultArea.classList.add('hidden');

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, model, format })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || "Generation failed.");
        }

        // Handle Audio Blob
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        // Update Player
        const audioPlayer = document.getElementById('audioPlayer');
        const downloadLink = document.getElementById('downloadLink');

        audioPlayer.src = url;
        downloadLink.href = url;
        downloadLink.download = `my-song-${Date.now()}.${format}`;

        // UI: Show Result
        statusMsg.classList.add('hidden');
        resultArea.classList.remove('hidden');

    } catch (error) {
        statusMsg.innerText = `Error: ${error.message}`;
        statusMsg.classList.add('text-red-400');
        statusMsg.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `Generate Music`;
    }
});
