from django.db import models
from django.utils import timezone

# Create your models here.

class PDFDocument(models.Model):
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(default=timezone.now)
    processing_time = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"PDF Document {self.id} - {self.status}"

class ProcessingJob(models.Model):
    folder_path = models.CharField(max_length=500)
    uploaded_at = models.DateTimeField(default=timezone.now)
    total_files = models.IntegerField(default=0)
    processed_count = models.IntegerField(default=0)
    total_processing_time = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"Processing Job {self.id} - {self.status}"

class ProcessedFile(models.Model):
    job = models.ForeignKey(ProcessingJob, on_delete=models.CASCADE, related_name='files')
    file_path = models.CharField(max_length=500)
    processing_time = models.FloatField()
    status = models.CharField(max_length=20, default='completed')
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Processed File {self.file_path}"
