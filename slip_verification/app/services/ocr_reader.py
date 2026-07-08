import easyocr
import numpy as np
import cv2
import re
from typing import Dict, Any, Optional
from app.core.config import settings

class OCRReaderService:
    def __init__(self):
        # Initialize the reader once
        self.reader = easyocr.Reader(settings.OCR_LANGUAGES)

    def extract_data(self, file_content: bytes) -> Dict[str, Any]:
        """
        Extract Amount, Date, Time, and Reference Number from slip.
        """
        try:
            nparr = np.frombuffer(file_content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Perform OCR
            results = self.reader.readtext(img, detail=0)
            full_text = " ".join(results)
            
            return {
                "amount": self._parse_amount(full_text),
                "reference_no": self._parse_ref_no(full_text),
                "datetime": self._parse_datetime(full_text),
                "raw_text": full_text
            }
        except Exception as e:
            return {"error": str(e)}

    def _parse_amount(self, text: str) -> Optional[float]:
        # Regex for amount: looks for numbers like 1,234.56 or 500.00
        # Common patterns: "จำนวนเงิน 1,200.00", "Amount: 500.00"
        match = re.search(r'(\d{1,3}(?:,\d{3})*\.\d{2})', text)
        if match:
            return float(match.group(1).replace(',', ''))
        return None

    def _parse_ref_no(self, text: str) -> Optional[str]:
        # Regex for Reference Number (usually long alphanumeric)
        # Often starts with letters or digits, 10-25 chars
        match = re.search(r'(?:Ref|เลขที่อ้างอิง|Reference)\s*:?\s*([A-Z0-9]{10,25})', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback: look for long alphanumeric sequences
        match = re.search(r'([A-Z0-9]{15,25})', text)
        if match:
            return match.group(0)
            
        return None

    def _parse_datetime(self, text: str) -> Optional[str]:
        # Very basic date/time parsing
        # Looks for "DD MMM YY HH:mm" or similar
        date_match = re.search(r'(\d{1,2}\s+[ก-ฮA-Z]{2,}\s+\d{2,4})', text)
        time_match = re.search(r'(\d{2}:\d{2}(?::\d{2})?)', text)
        
        if date_match and time_match:
            return f"{date_match.group(1)} {time_match.group(1)}"
        return None
