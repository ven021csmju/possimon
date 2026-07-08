import cv2
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image
import io

class QRReaderService:
    @staticmethod
    def extract_qr_data(file_content: bytes) -> str:
        """
        Extract QR data from image bytes.
        Returns the raw QR data string or None if not found.
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(file_content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None
            
            # Decode QR codes
            decoded_objects = decode(img)
            
            if not decoded_objects:
                # Try with PIL as fallback
                pil_img = Image.open(io.BytesIO(file_content))
                decoded_objects = decode(pil_img)
            
            if decoded_objects:
                # Return the data of the first QR code found
                return decoded_objects[0].data.decode('utf-8')
            
            return None
        except Exception as e:
            # In production, log this error
            return None
