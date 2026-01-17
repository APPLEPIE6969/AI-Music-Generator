document.getElementById('generateBtn').addEventListener('click', async () => {
    const prompt = document.getElementById('promptInput').value;
    const model = document.getElementById('modelSelect').value;
    const format = document.getElementById('formatSelect').value;
    const status = document.getElementById('status');
    const result = document.getElementById('result');
    const btn = document.getElementById('generateBtn');

    if(!prompt) return alert("Please enter a prompt");

    btn.disabled = true;
    status.innerText = "Generating... (Please wait 20-40s)";
    result.classList.add('hidden');

    try {
        const res = await fetch('/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt, model, format})
        });
        
        if(!res.ok) {
            const err = await res.json();
            throw new Error(err.error || "Failed");
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        
        document.getElementById('player').src = url;
        document.getElementById('download').href = url;
        document.getElementById('download').download = `track.${format}`;
        
        status.innerText = "";
        result.classList.remove('hidden');
    } catch (e) {
        status.innerText = "Error: " + e.message;
        status.classList.add("text-red-500");
    }
    btn.disabled = false;
});
