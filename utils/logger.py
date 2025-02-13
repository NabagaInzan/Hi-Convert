import logging
import os
from datetime import datetime

class Logger:
    def __init__(self):
        self.setup_logger()

    def setup_logger(self):
        # Créer le dossier logs s'il n'existe pas
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Créer un fichier log avec la date
        log_file = os.path.join(log_dir, f'hiconvert_{datetime.now().strftime("%Y%m%d")}.log')
        
        # Configuration du logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('HiConvert')

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def warning(self, message):
        self.logger.warning(message)

# Instance globale du logger
app_logger = Logger()
