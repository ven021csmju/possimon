import hashlib

class HashService:
    @staticmethod
    def generate_sha256(file_content: bytes) -> str:
        return hashlib.sha256(file_content).hexdigest()
