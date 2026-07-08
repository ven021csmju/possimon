import os
import shutil
from app.storage.base import BaseStorage
from app.core.config import settings

class LocalStorage(BaseStorage):
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    def save(self, file_content: bytes, filename: str) -> str:
        file_path = os.path.join(self.upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_content)
        return file_path

    def delete(self, file_path: str):
        if os.path.exists(file_path):
            os.remove(file_path)
