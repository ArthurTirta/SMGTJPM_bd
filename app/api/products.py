"""
API endpoints for jeans products from smgt database.
"""
import json
import ast
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from decimal import Decimal
from datetime import date, datetime

from app.api.deps import get_db
from app.models import Jean
from app.core import minio_utils

router = APIRouter()


def _extract_usd_price(raw):
    """
    Extract USD value from selling_price/mrp.
    Handles: dict (from SQLAlchemy JSON), JSON string, or Python literal from CSV (e.g. "{'USD': 285.9978}").
    """
    if raw is None:
        return None
    if isinstance(raw, dict):
        val = raw.get("USD")
    elif isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        obj = None
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            try:
                obj = ast.literal_eval(s)
            except (ValueError, SyntaxError):
                pass
        val = obj.get("USD") if isinstance(obj, dict) else None
    else:
        val = None
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)
    return None


def _serialize_value(val):
    """Convert to JSON-serializable type."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_serialize_value(v) for v in val]
    return val


def _jean_to_item(jean: Jean) -> dict:
    """Convert Jean ORM to API response item."""
    price_usd = _extract_usd_price(jean.selling_price)
    return {
        "id": jean.id,
        "product_id": jean.product_id,
        "product_name": jean.product_name or "",
        "brand": jean.brand or "",
        "price_usd": price_usd,
        "selling_price": _serialize_value(jean.selling_price),
        "discount": float(jean.discount) if jean.discount is not None else 0.0,
        "feature_image_s3": jean.feature_image_s3,
        "pdp_url": jean.pdp_url,
        "sku": jean.sku,
        "images_minio": _serialize_value(jean.images_minio),
    }


def _jean_to_detail(jean: Jean) -> dict:
    """Convert Jean ORM to full detail response."""
    base = _jean_to_item(jean)
    base["description"] = jean.description
    base["meta_info"] = jean.meta_info
    base["feature_list"] = _serialize_value(jean.feature_list)
    base["pdp_images_s3"] = _serialize_value(jean.pdp_images_s3)
    base["images_minio"] = _serialize_value(jean.images_minio)
    base["mrp"] = _serialize_value(jean.mrp)
    return base


@router.get("/jeans")
def list_jeans(
    db: Session = Depends(get_db),
    search: str = Query("", description="Search by product name or brand"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(12, ge=1, le=100, description="Items per page"),
):
    """
    List jeans products with optional search and pagination.
    Data from database smgt, table jeans.
    """
    q = db.query(Jean)
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                Jean.product_name.ilike(term),
                Jean.brand.ilike(term),
            )
        )
    total = q.count()
    offset = (page - 1) * per_page
    items = q.order_by(Jean.id).offset(offset).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page if total else 0
    return {
        "items": [_jean_to_item(j) for j in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.get("/jeans/{jeans_id}")
def get_jean_by_id(jeans_id: int, db: Session = Depends(get_db)):
    """Get a single jeans product by id (database smgt)."""
    jean = db.query(Jean).filter(Jean.id == jeans_id).first()
    if not jean:
        raise HTTPException(status_code=404, detail="Product not found")
    return _jean_to_detail(jean)


# ----- Image proxy (MinIO) -----


def _is_absolute_url(path: str) -> bool:
    """True if path looks like http:// or https:// (e.g. from feature_image_s3)."""
    s = (path or "").strip()
    return s.startswith("http://") or s.startswith("https://")


@router.get("/image/{filename:path}")
def get_product_image(filename: str):
    """
    Proxy image from MinIO, or redirect if filename is an absolute URL (e.g. feature_image_s3).
    Frontend uses: GET /api/v1/products/image/{key}.
    """
    if _is_absolute_url(filename):
        return RedirectResponse(url=filename)
    stream, content_type = minio_utils.get_file_stream(filename)
    if stream is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return StreamingResponse(stream, media_type=content_type)


# ----- CRUD with MinIO photo storage -----


def _upload_files(files: List[UploadFile]) -> List[str]:
    """Upload files to MinIO; return list of keys for images_minio."""
    keys = []
    for f in files or []:
        if not f.filename or not f.content_type:
            continue
        content_type = f.content_type or "application/octet-stream"
        key = minio_utils.upload_file(f.file, content_type)
        keys.append(key)
    return keys


@router.post("")
def create_product(
    db: Session = Depends(get_db),
    product_name: str = Form(...),
    brand: Optional[str] = Form(""),
    price_usd: Optional[float] = Form(None),
    discount: Optional[float] = Form(0.0),
    description: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(default=None),
):
    """Create a product (Jean) and upload photos to MinIO. Stored keys go to images_minio."""
    selling_price = {"USD": float(price_usd)} if price_usd is not None else None
    product_id = f"gen-{uuid.uuid4().hex[:16]}"
    keys = _upload_files(files)
    jean = Jean(
        product_name=product_name.strip(),
        brand=(brand or "").strip(),
        selling_price=selling_price,
        discount=float(discount or 0),
        description=description,
        sku=sku,
        product_id=product_id,
        images_minio=keys if keys else None,
    )
    db.add(jean)
    db.commit()
    db.refresh(jean)
    return _jean_to_detail(jean)


@router.put("/{product_id}")
def update_product(
    product_id: int,
    db: Session = Depends(get_db),
    product_name: Optional[str] = Form(None),
    brand: Optional[str] = Form(None),
    price_usd: Optional[float] = Form(None),
    discount: Optional[float] = Form(None),
    description: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    remove_keys: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(default=None),
):
    """Update product attributes, optionally remove photos by key, and/or append new photos."""
    jean = db.query(Jean).filter(Jean.id == product_id).first()
    if not jean:
        raise HTTPException(status_code=404, detail="Product not found")
    if product_name is not None:
        jean.product_name = product_name.strip()
    if brand is not None:
        jean.brand = brand.strip()
    if price_usd is not None:
        jean.selling_price = {"USD": float(price_usd)}
    if discount is not None:
        jean.discount = float(discount)
    if description is not None:
        jean.description = description
    if sku is not None:
        jean.sku = sku
    existing = list(jean.images_minio or [])
    if remove_keys:
        try:
            to_remove = json.loads(remove_keys) if remove_keys.strip().startswith("[") else [k.strip() for k in remove_keys.split(",") if k.strip()]
        except json.JSONDecodeError:
            to_remove = [k.strip() for k in remove_keys.split(",") if k.strip()]
        for k in to_remove:
            minio_utils.delete_file(k)
        existing = [k for k in existing if k not in to_remove]
    new_keys = _upload_files(files)
    jean.images_minio = existing + new_keys if (existing or new_keys) else None
    db.commit()
    db.refresh(jean)
    return _jean_to_detail(jean)


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete product and remove its photos from MinIO."""
    jean = db.query(Jean).filter(Jean.id == product_id).first()
    if not jean:
        raise HTTPException(status_code=404, detail="Product not found")
    keys = list(jean.images_minio or [])
    minio_utils.delete_files(keys)
    db.delete(jean)
    db.commit()
    return {"deleted": product_id}
