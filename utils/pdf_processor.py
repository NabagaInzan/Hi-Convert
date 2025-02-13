import os
import time
import pandas as pd
from pdf2image import convert_from_path
import easyocr
import numpy as np
import re
from .logger import app_logger

class PDFProcessor:
    def __init__(self):
        self.reader = easyocr.Reader(['fr'])
        self.poppler_path = r'C:\poppler\Library\bin'
        self.logger = app_logger

    def process_directory(self, directory_path):
        """
        Traite tous les fichiers plan.pdf dans le répertoire et ses sous-répertoires
        """
        try:
            # Vérifier si le dossier existe
            if not os.path.exists(directory_path):
                error_msg = f"Le dossier n'existe pas : {directory_path}"
                self.logger.error(error_msg)
                return [], error_msg

            # Compter le nombre total de fichiers plan.pdf
            total_files = sum(len([f for f in files if f.lower() == "plan.pdf"]) 
                            for _, _, files in os.walk(directory_path))
            
            if total_files == 0:
                msg = f"Aucun fichier 'plan.pdf' trouvé dans {directory_path}"
                self.logger.warning(msg)
                return [], msg

            processed_files = 0
            results = []
            start_time = time.time()

            for root, _, files in os.walk(directory_path):
                for file_name in files:
                    if file_name.lower() == "plan.pdf":
                        file_path = os.path.join(root, file_name)
                        # Utiliser le nom du dernier dossier comme nom du fichier CSV
                        folder_name = os.path.basename(root)
                        
                        try:
                            start_file_time = time.time()
                            csv_path = self.process_file(file_path, folder_name)
                            processing_time = time.time() - start_file_time
                            
                            results.append({
                                'file': file_path,
                                'csv': csv_path,
                                'time': processing_time,
                                'status': 'success'
                            })
                            
                            self.logger.info(f"Fichier traité avec succès: {file_path}")
                            self.logger.info(f"CSV créé: {csv_path}")
                            processed_files += 1
                            
                        except Exception as e:
                            error_msg = f"Erreur lors du traitement de {file_path}: {str(e)}"
                            self.logger.error(error_msg)
                            results.append({
                                'file': file_path,
                                'error': str(e),
                                'status': 'error'
                            })

            total_time = time.time() - start_time
            summary = f"Terminé. Temps total: {total_time:.2f} secondes, Fichiers traités: {processed_files}/{total_files}"
            self.logger.info(summary)
            
            return results, summary

        except Exception as e:
            error_msg = f"Erreur lors du traitement du répertoire: {str(e)}"
            self.logger.error(error_msg)
            return [], error_msg

    def process_file(self, file_path, folder_name):
        """
        Traite un fichier PDF et extrait les coordonnées
        """
        self.logger.info(f"Début du traitement du fichier : {file_path}")

        try:
            # Conversion du PDF en images
            images = convert_from_path(file_path, poppler_path=self.poppler_path)
            self.logger.info(f"PDF converti en {len(images)} images")

            numbers = []
            for i, image in enumerate(images):
                image_np = np.array(image)
                results = self.reader.readtext(image_np)
                self.logger.info(f"Page {i+1}: {len(results)} zones de texte détectées")

                # Extraction des nombres avec leurs coordonnées
                for result in results:
                    bbox, text, confidence = result
                    extracted_numbers = re.findall(r'\b\d{5,}(?:\.\d+)?\b', text)
                    
                    for num in extracted_numbers:
                        try:
                            value = float(num.replace(',', '.'))
                            if value > 100000:
                                numbers.append({
                                    'value': value,
                                    'bbox': bbox,
                                    'confidence': confidence,
                                    'page': i + 1,
                                    'text': text
                                })
                                self.logger.info(f"Nombre extrait: {value} (confiance: {confidence:.2f}, page: {i+1})")
                        except ValueError as ve:
                            self.logger.warning(f"Impossible de convertir en nombre: {num} - {str(ve)}")

            if len(numbers) == 0:
                self.logger.warning(f"Aucun nombre valide trouvé dans {file_path}")
                raise ValueError("Aucune coordonnée valide trouvée dans le document")

            if len(numbers) % 2 != 0:
                self.logger.warning(f"Nombre impair de coordonnées trouvées dans {file_path}")

            # Création des listes X et Y
            coordinates_data = []
            for i in range(0, len(numbers) - 1, 2):
                coordinates_data.append({
                    'X': numbers[i]['value'],
                    'Y': numbers[i + 1]['value'] if i + 1 < len(numbers) else None
                })

            df = pd.DataFrame(coordinates_data)

            # Utiliser le nom du dossier pour le fichier CSV
            csv_path = os.path.join(os.path.dirname(file_path), f"{folder_name}.csv")
            df.to_csv(csv_path, index=False, sep=';', encoding='utf-8')
            
            self.logger.info(f"Fichier CSV créé : {csv_path} avec {len(coordinates_data)} paires de coordonnées")
            return csv_path

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de {file_path}: {str(e)}")
            raise
