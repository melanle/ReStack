document.getElementById('uploadForm').addEventListener('submit', function(event) {
    event.preventDefault();
    
    let formData = new FormData(this);

    fetch('/predict', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        let resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = '<h2>Results</h2>';
        
        data.forEach(result => {
            resultsDiv.innerHTML += `
                <div class="result">
                    <h3>${result.Filename}</h3>
                    <p><strong>Total Score:</strong> ${result['Total Score'].toFixed(2)}</p>
                    <p><strong>Section Scores:</strong> ${JSON.stringify(result['Section Scores'])}</p>
                </div>
            `;
        });
    })
    .catch(error => console.error('Error:', error));
});
