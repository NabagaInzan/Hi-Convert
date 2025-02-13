from django.shortcuts import render
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ProcessingJob, ProcessedFile
import time
from pdf2image import convert_from_path
import easyocr
import os
import logging
import threading
import pandas as pd
import numpy as np
import re
from django.conf import settings
from wsgiref.util import FileWrapper
import mimetypes
import multiprocessing
from functools import partial

logger = logging.getLogger('pdf_converter')

def index(request):
    jobs = ProcessingJob.objects.all().order_by('-uploaded_at')
    return render(request, 'pdf_converter/index.html', {'jobs': jobs})

@csrf_exempt
def process_folder(request):
    if request.method == 'POST' and 'folder_path' in request.POST:
        folder_path = request.POST.get('folder_path').strip()
        logger.info(f"Received folder path: {folder_path}")
        
        # Nettoyer et normaliser le chemin
        folder_path = os.path.normpath(folder_path)
        logger.info(f"Normalized path: {folder_path}")
        
        # Vérifier si le dossier existe directement
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            logger.info(f"Found valid folder at: {folder_path}")
            
            # Créer un nouveau job avec le chemin complet
            job = ProcessingJob.objects.create(folder_path=folder_path)
            logger.info(f"Created new job {job.id} for folder: {folder_path}")
            
            # Démarrer le traitement en arrière-plan
            thread = threading.Thread(target=process_files_thread, args=(job.id,))
            thread.start()
            
            return JsonResponse({
                'status': 'success',
                'job_id': job.id,
                'folder_path': folder_path
            })
        else:
            error_msg = f'Le dossier "{folder_path}" n\'existe pas ou n\'est pas accessible'
            logger.error(error_msg)
            return JsonResponse({
                'status': 'error',
                'message': error_msg
            })
            
    error_msg = 'Veuillez sélectionner un dossier valide'
    logger.error(error_msg)
    return JsonResponse({
        'status': 'error',
        'message': error_msg
    })

def process_image(image, reader):
    """Traite une seule image et retourne les coordonnées trouvées"""
    image_np = np.array(image)
    results = reader.readtext(
        image_np,
        decoder='greedy',  # Plus rapide que le décodeur par défaut
        batch_size=8,      # Augmente la vitesse sur GPU/CPU moderne
        paragraph=False,    # Pas besoin de regrouper en paragraphes
        detail=0           # Retourne uniquement le texte
    )
    
    numbers = []
    for text in results:
        # Recherche des nombres avec ou sans décimales
        extracted_numbers = re.findall(r'\b\d{5,}(?:\.\d+)?\b', text)
        for num in extracted_numbers:
            try:
                value = float(num.replace(',', '.'))
                if value > 100000:  # Filtre pour les coordonnées valides
                    numbers.append(value)
            except ValueError:
                continue
    return numbers

def process_files_thread(job_id):
    job = ProcessingJob.objects.get(id=job_id)
    logger.info(f"Starting processing job {job_id} for folder: {job.folder_path}")
    
    try:
        # Count total files and validate folder structure
        total_files = 0
        pdf_files = []
        
        for root, _, files in os.walk(job.folder_path):
            # Chercher plan.pdf indépendamment de la casse
            for file_name in files:
                if file_name.lower() == "plan.pdf":
                    file_path = os.path.join(root, file_name)
                    pdf_files.append(file_path)
                    total_files += 1
                    logger.info(f"Found plan file: {file_path}")
        
        if total_files == 0:
            logger.warning(f"No 'plan.pdf' files found in {job.folder_path}")
            job.status = 'no_files'
            job.save()
            return

        job.total_files = total_files
        job.status = 'processing'
        job.save()
        
        processed_files = 0
        start_time = time.time()

        # Initialiser EasyOCR une seule fois
        reader = easyocr.Reader(['fr'], gpu=False)  # GPU=False car plus stable sur CPU
        
        # Nombre de processeurs à utiliser (laisse un cœur libre)
        num_processes = max(1, multiprocessing.cpu_count() - 1)
        
        # Process each found PDF file
        for file_path in pdf_files:
            try:
                logger.info(f"Processing file: {file_path}")
                start_file_time = time.time()
                
                # Récupérer le chemin Poppler des paramètres
                poppler_path = settings.POPPLER_PATH
                logger.info(f"Using Poppler path: {poppler_path}")
                
                # Conversion du PDF en images avec le chemin Poppler spécifié
                images = convert_from_path(
                    file_path,
                    poppler_path=poppler_path,
                    thread_count=num_processes  # Utilise plusieurs threads pour la conversion
                )
                
                # Traitement parallèle des images
                with multiprocessing.Pool(num_processes) as pool:
                    process_func = partial(process_image, reader=reader)
                    results = pool.map(process_func, images)
                
                # Aplatir la liste des résultats
                numbers = [num for sublist in results for num in sublist]

                # S'assurer d'avoir un nombre pair de coordonnées
                if len(numbers) % 2 != 0:
                    numbers = numbers[:-1]

                # Diviser la liste en X et Y
                X = numbers[::2]
                Y = numbers[1::2]

                # Création du fichier CSV
                csv_path = os.path.splitext(file_path)[0] + ".csv"
                df = pd.DataFrame({
                    'X': X,
                    'Y': Y
                })
                # Sauvegarder avec le séparateur point-virgule et format français
                df.to_csv(csv_path, index=False, sep=';', decimal=',')
                
                processing_time = time.time() - start_file_time
                
                # Record processed file
                processed_file = ProcessedFile.objects.create(
                    job=job,
                    file_path=file_path,
                    processing_time=processing_time,
                    status='completed'
                )
                
                processed_files += 1
                job.processed_count = processed_files
                job.save()
                
                logger.info(f"Successfully processed {file_path} in {processing_time:.2f} seconds")
                logger.info(f"CSV file created at: {csv_path}")
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                ProcessedFile.objects.create(
                    job=job,
                    file_path=file_path,
                    processing_time=0,
                    status='failed'
                )

        total_processing_time = time.time() - start_time
        job.total_processing_time = total_processing_time
        job.status = 'completed'
        job.save()
        
        logger.info(f"Job {job_id} completed. Total time: {total_processing_time:.2f}s, Files processed: {processed_files}")
        
    except Exception as e:
        logger.error(f"Error in job {job_id}: {str(e)}")
        job.status = 'failed'
        job.save()

def download_csv(request, file_id):
    try:
        processed_file = ProcessedFile.objects.get(id=file_id)
        pdf_path = processed_file.file_path
        csv_path = os.path.splitext(pdf_path)[0] + ".csv"
        
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            raise Http404("Le fichier CSV n'existe pas")
            
        # Lire le contenu du fichier en une seule fois
        with open(csv_path, 'rb') as fh:
            content = fh.read()
            
        # Créer la réponse avec le contenu
        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(csv_path)}"'
        return response
            
    except ProcessedFile.DoesNotExist:
        logger.error(f"ProcessedFile with id {file_id} not found")
        raise Http404("Fichier non trouvé")
    except Exception as e:
        logger.error(f"Error downloading CSV: {str(e)}")
        raise Http404("Erreur lors du téléchargement du fichier")

def process_single_file(file_path):
    logger.info(f"Processing file: {file_path}")
    
    # Convert PDF to images
    images = convert_from_path(file_path)
    reader = easyocr.Reader(['fr'])
    numbers = []

    for i, image in enumerate(images):
        image_np = np.array(image)
        results = reader.readtext(image_np)

        # Extract numbers
        for result in results:
            text = result[1]
            extracted_numbers = re.findall(r'\b\d{5,}(?:\.\d+)?\b', text)
            valid_numbers = [float(num.replace(',', '.')) for num in extracted_numbers 
                           if float(num.replace(',', '.')) > 100000]
            numbers.extend(valid_numbers)

    # Split numbers into X and Y coordinates
    X = numbers[::2]
    Y = numbers[1::2]

    # Create CSV file
    csv_path = os.path.splitext(file_path)[0] + ".csv"
    df = pd.DataFrame(list(zip(X, Y)), columns=['X', 'Y'])
    df.to_csv(csv_path, index=False, header=True, sep=';')
    
    logger.info(f"Created CSV file: {csv_path}")
    return csv_path

def get_job_status(request, job_id):
    try:
        job = ProcessingJob.objects.get(id=job_id)
        processed_files = ProcessedFile.objects.filter(job=job)
        
        return JsonResponse({
            'status': job.status,
            'total_files': job.total_files,
            'processed_files': job.processed_count,
            'total_processing_time': job.total_processing_time,
            'files': [
                {
                    'id': f.id,
                    'path': f.file_path,
                    'csv_path': os.path.splitext(f.file_path)[0] + ".csv",
                    'processing_time': f.processing_time,
                    'status': f.status
                } for f in processed_files
            ]
        })
    except ProcessingJob.DoesNotExist:
        return JsonResponse({'status': 'error'}, status=404)
