import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hiconvert.settings')
application = get_wsgi_application()

# For Gunicorn
app = application
