from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, Date, Text, JSON
from sqlalchemy.orm import relationship
from .database import Base


class Jean(Base):
    __tablename__ = "jeans"
    
    id = Column(Integer, primary_key=True, index=True)
    selling_price = Column(JSON)  # Store as JSON: {'USD': 285.9978}
    discount = Column(Float, default=0.0)
    category_id = Column(Integer, index=True)
    meta_info = Column(Text)
    product_id = Column(String(255), unique=True, index=True)  # Hash string
    pdp_url = Column(Text)
    sku = Column(String(255), index=True)
    brand = Column(String(255), index=True)
    department_id = Column(Integer, index=True)
    last_seen_date = Column(Date)
    launch_on = Column(Date)
    mrp = Column(JSON)  # Store as JSON: {'USD': 285.9978}
    product_name = Column(String(500), index=True)
    feature_image_s3 = Column(Text)
    channel_id = Column(Integer, index=True)
    feature_list = Column(JSON)  # Store as JSON array
    description = Column(Text)
    style_attributes = Column(JSON)  # Store as JSON object
    pdp_images_s3 = Column(JSON)  # Store as JSON array
    images_minio = Column(JSON)  # Store list of MinIO keys/filenames
