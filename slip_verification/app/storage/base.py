from abc import ABC, abstractmethod

class BaseStorage(ABC):
    @abstractmethod
    def save(self, file_content: bytes, filename: str) -> str:
        pass

    @abstractmethod
    def delete(self, file_path: str):
        pass
