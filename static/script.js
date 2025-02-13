document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const fileInfo = document.getElementById('fileInfo');
    const progressArea = document.getElementById('progressArea');
    const resultArea = document.getElementById('resultArea');
    const progressBar = document.querySelector('.progress-bar');
    const processingStatus = document.getElementById('processingStatus');
    const downloadBtn = document.getElementById('downloadBtn');

    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('border-primary');
    }

    function unhighlight(e) {
        dropZone.classList.remove('border-primary');
    }

    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'application/pdf') {
                showFileInfo(file);
            } else {
                alert('Veuillez sélectionner un fichier PDF.');
            }
        }
    }

    function showFileInfo(file) {
        const fileName = document.querySelector('.selected-file-name');
        fileName.textContent = `Fichier sélectionné : ${file.name}`;
        fileInfo.classList.remove('d-none');
    }

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            alert('Veuillez sélectionner un fichier PDF.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        fileInfo.classList.add('d-none');
        progressArea.classList.remove('d-none');
        progressBar.style.width = '0%';

        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Erreur lors du traitement du fichier');
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                progressBar.style.width = '100%';
                processingStatus.textContent = 'Traitement terminé !';
                showResult(data.csv_path);
            } else {
                throw new Error(data.error || 'Une erreur est survenue');
            }
        } catch (error) {
            alert(error.message);
            progressArea.classList.add('d-none');
            fileInfo.classList.remove('d-none');
        }
    });

    function showResult(csvPath) {
        progressArea.classList.add('d-none');
        resultArea.classList.remove('d-none');
        
        downloadBtn.onclick = function() {
            window.location.href = `/download/${csvPath}`;
        };
    }
});
