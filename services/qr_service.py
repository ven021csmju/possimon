import io
import qrcode
from fastapi import Response, HTTPException

def crc16(data: str):
    crc = 0xFFFF
    for i in range(len(data)):
        crc ^= ord(data[i]) << 8
        for j in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
        crc &= 0xFFFF
    return format(crc, '04X')

def generate_promptpay_payload(phone_or_id: str, amount: float = None):
    def f(id, val):
        return f"{id}{len(val):02d}{val}"

    target = phone_or_id.replace("-", "")
    if len(target) == 10 and target.startswith("0"):
        target = "0066" + target[1:]
    
    account_info = f("00", "A000000677010111")
    if len(target) == 13:
        account_info += f("01", target)
    else:
        account_info += f("02", target)

    payload = f("00", "01")
    payload += f("01", "11")
    payload += f("29", account_info)
    payload += f("53", "764")
    if amount:
        payload += f("54", f"{amount:.2f}")
    payload += f("58", "TH")
    payload += "6304"
    
    crc = crc16(payload)
    return payload + crc

def generate_qr_response(phone: str, amount: float):
    try:
        payload = generate_promptpay_payload(phone, amount)
        
        img = qrcode.make(payload)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
