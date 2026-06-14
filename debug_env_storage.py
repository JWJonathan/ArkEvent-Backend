import os
import django
from django.conf import settings

# Set settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arkevent_backend.settings')
django.setup()

from django.core.files.storage import default_storage
from storages.backends.s3boto3 import S3Boto3Storage

print("--- DEBUG SETTINGS ---")
print(f"SUPABASE_S3_ENDPOINT_URL: {getattr(settings, 'SUPABASE_S3_ENDPOINT_URL', 'NOT SET')}")
print(f"SUPABASE_BUCKET_NAME: {getattr(settings, 'SUPABASE_BUCKET_NAME', 'NOT SET')}")
print(f"SUPABASE_S3_CUSTOM_DOMAIN: {getattr(settings, 'SUPABASE_S3_CUSTOM_DOMAIN', 'NOT SET')}")

print("\n--- STORAGE INSTANCE ---")
if isinstance(default_storage, S3Boto3Storage):
    print(f"Storage custom_domain: {default_storage.custom_domain}")
    test_path = "events/posters/Agricole-1-800x500.jpg"
    print(f"Generated URL: {default_storage.url(test_path)}")
else:
    print(f"Default storage is NOT S3Boto3Storage: {type(default_storage)}")
    # Try to manually instantiate it to see what happens
    try:
        s3_storage = S3Boto3Storage()
        print(f"Manually instantiated S3Boto3Storage custom_domain: {s3_storage.custom_domain}")
        print(f"Generated URL (Manual): {s3_storage.url('test.jpg')}")
    except Exception as e:
        print(f"Error instantiating S3Boto3Storage: {e}")
