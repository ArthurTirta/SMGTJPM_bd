import csv
import json
import ast
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, Jean

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def parse_json_field(value):
    """Parse string representation of dict/list to actual JSON"""
    if not value or value == '{}' or value == '[]':
        return None
    try:
        # Use ast.literal_eval to safely parse Python dict/list strings
        return ast.literal_eval(value)
    except:
        return None

def parse_float(value):
    """Parse float values, return None if empty"""
    if not value or value == '':
        return None
    try:
        return float(value)
    except:
        return None

def parse_date(value):
    """Parse date string to date object"""
    if not value or value == '':
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except:
        return None

def import_jeans_data():
    db = SessionLocal()
    
    try:
        csv_path = 'D:/UDEMY/Portofolio4/backend/assets/jeans_filtered.csv'
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            count = 0
            
            for row in csv_reader:
                try:
                    jean = Jean(
                        selling_price=parse_json_field(row['selling_price']),
                        discount=parse_float(row['discount']) or 0.0,
                        category_id=int(row['category_id']) if row['category_id'] else None,
                        meta_info=row['meta_info'] if row['meta_info'] else None,
                        product_id=row['product_id'],
                        pdp_url=row['pdp_url'] if row['pdp_url'] else None,
                        sku=row['sku'] if row['sku'] else None,
                        brand=row['brand'] if row['brand'] else None,
                        department_id=int(row['department_id']) if row['department_id'] else None,
                        last_seen_date=parse_date(row['last_seen_date']),
                        launch_on=parse_date(row['launch_on']),
                        mrp=parse_json_field(row['mrp']),
                        product_name=row['product_name'] if row['product_name'] else None,
                        feature_image_s3=row['feature_image_s3'] if row['feature_image_s3'] else None,
                        channel_id=int(row['channel_id']) if row['channel_id'] else None,
                        feature_list=parse_json_field(row['feature_list']),
                        description=row['description'] if row['description'] else None,
                        style_attributes=parse_json_field(row['style_attributes']),
                        pdp_images_s3=parse_json_field(row['pdp_images_s3'])
                    )
                    
                    db.add(jean)
                    count += 1
                    
                    # Commit every 10 rows to avoid memory issues
                    if count % 10 == 0:
                        db.commit()
                        print(f"Imported {count} records...")
                        
                except Exception as e:
                    print(f"Error importing row {count + 1}: {e}")
                    print(f"Product ID: {row.get('product_id', 'N/A')}")
                    db.rollback()
                    continue
            
            # Final commit
            db.commit()
            print(f"\n✓ Successfully imported {count} jeans records!")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting import...")
    import_jeans_data()