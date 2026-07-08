# Slip Verification Service

A production-ready service to verify bank transfer slips using SHA256 hashing, QR code decoding, and OCR.

## Features
- **SHA256 Hashing**: Prevents duplicate slip uploads.
- **QR Code Verification**: Fast extraction of PromptPay data.
- **OCR Verification**: Extracts Amount, Date, Time, and Ref No using EasyOCR.
- **Audit Logs**: Full history of verification steps.
- **Clean Architecture**: Decoupled layers for scalability.

## Prerequisites
- Docker and Docker Compose

## Quick Start

1. **Start the service:**
   ```bash
   cd slip_verification
   docker-compose up --build
   ```

2. **Access the API Documentation:**
   Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

3. **Test with a slip:**
   Use the `/api/v1/payments/upload-slip` endpoint in Swagger UI or use `curl`:
   ```bash
   curl -X 'POST' \
     'http://localhost:8000/api/v1/payments/upload-slip' \
     -H 'accept: application/json' \
     -H 'Content-Type: multipart/form-data' \
     -F 'file=@your_slip.jpg;type=image/jpeg'
   ```

## Folder Structure
```text
app/
├── api/          # API Routes
├── core/         # Configuration & Exceptions
├── db/           # Database Connection
├── models/       # SQLAlchemy Models
├── schemas/      # Pydantic Schemas
├── services/     # Business Logic (OCR, QR, Hash)
├── repositories/ # Data Access Layer
├── storage/      # File Storage Logic
└── main.py       # FastAPI Entrypoint
```
