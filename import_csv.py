import csv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import models
from dotenv import load_dotenv

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

CSV_PATH = "Data/winemag-data-130k-v2.csv"

def import_data():
    db = SessionLocal()
    try:
        print("Starting CSV import...")
        
        # Lookups
        countries = {}
        regions = {}
        wineries = {}
        grapes = {}

        # Pre-load existing data if any
        for c in db.query(models.Country).all(): countries[c.name] = c.id
        for r in db.query(models.Region).all(): regions[r.name] = r.id
        for w in db.query(models.Winery).all(): wineries[w.name] = w.id
        for g in db.query(models.Grape).all(): grapes[g.name] = g.id

        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            batch_size = 1000
            count = 0
            limit = 5000
            
            for row in reader:
                if count >= limit:
                    break
                # 1. Handle Country
                country_name = row['country']
                if country_name and country_name not in countries:
                    c = models.Country(name=country_name)
                    db.add(c)
                    db.flush()
                    countries[country_name] = c.id
                
                # 2. Handle Region
                region_name = row['province'] or row['region_1']
                if region_name and region_name not in regions:
                    r = models.Region(name=region_name, country_id=countries.get(country_name))
                    db.add(r)
                    db.flush()
                    regions[region_name] = r.id

                # 3. Handle Winery
                winery_name = row['winery']
                if winery_name and winery_name not in wineries:
                    w = models.Winery(name=winery_name, country_id=countries.get(country_name), region_id=regions.get(region_name))
                    db.add(w)
                    db.flush()
                    wineries[winery_name] = w.id

                # 4. Handle Grape/Variety
                variety = row['variety']
                if variety and variety not in grapes:
                    g = models.Grape(name=variety)
                    db.add(g)
                    db.flush()
                    grapes[variety] = g.id

                # 5. Create Wine (as Product)
                try:
                    price = float(row['price']) if row['price'] else 0.0
                except ValueError:
                    price = 0.0

                wine = models.Wine(
                    name=row['title'],
                    price=price,
                    stock=100,
                    type="wine",
                    designation=row['designation'],
                    description=row['description'],
                    wine_type=row['variety'],
                    winery_id=wineries.get(winery_name),
                    region_id=regions.get(region_name),
                    country_id=countries.get(country_name),
                    vintage=None # Title usually has vintage but extraction is complex
                )
                
                if variety and variety in grapes:
                    # This might be slow if we do it row by row for 130k
                    # For simplicity, we'll skip the many-to-many grape relation in this batch
                    # or just add the main variety
                    pass

                db.add(wine)
                count += 1
                
                if count % batch_size == 0:
                    db.commit()
                    print(f"Imported {count} records...")
                    # Refresh lookups if needed or just keep going
            
            db.commit()
            print(f"Finished! Imported {count} wines.")

    except Exception as e:
        db.rollback()
        print(f"Error during import: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import_data()
