from django.core.files.storage import Storage
import requests
from django.conf import settings

class SupabaseStorage(Storage):
    def __init__(self, bucket='arkevent'):
        self.bucket = bucket
        self.url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}"
        self.headers = {
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        }

    def _save(self, name, content):
        file_path = f"{self.url}/{name}"
        response = requests.post(
            file_path,
            headers=self.headers,
            files={"file": content},
        )
        response.raise_for_status()
        return name

    def url(self, name):
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/{self.bucket}/{name}"
EOF
