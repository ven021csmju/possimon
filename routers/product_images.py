from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Product, ProductImage
from services.image_service import ImageService
from schemas import ProductImageOut
from typing import List

router = APIRouter(tags=["Product Images"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/products/{product_id}/images", response_model=ProductImageOut)
async def upload_image(
    product_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Upload file
    image_url, file_path = await ImageService.upload_product_image(file, product_id)
    
    # Save to DB
    new_image = ProductImage(
        product_id=product_id,
        image_url=image_url,
        file_path=file_path
    )
    db.add(new_image)
    db.commit()
    db.refresh(new_image)
    
    return new_image

@router.get("/products/{product_id}/images", response_model=List[ProductImageOut])
def get_product_images(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product.images

@router.delete("/images/{image_id}")
def delete_image(image_id: int, db: Session = Depends(get_db)):
    image = db.query(ProductImage).filter(ProductImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete physical file
    ImageService.delete_image_file(image.file_path)
    
    # Delete from DB
    db.delete(image)
    db.commit()
    
    return {"message": "Image deleted successfully"}
