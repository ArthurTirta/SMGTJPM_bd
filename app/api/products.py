"""
API endpoints for jeans products from smgt database.
"""
import json
import ast
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from decimal import Decimal
from datetime import date, datetime

from app.api.deps import get_db
from app.models import Jean

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
    }


def _jean_to_detail(jean: Jean) -> dict:
    """Convert Jean ORM to full detail response."""
    base = _jean_to_item(jean)
    base["description"] = jean.description
    base["meta_info"] = jean.meta_info
    base["feature_list"] = _serialize_value(jean.feature_list)
    base["pdp_images_s3"] = _serialize_value(jean.pdp_images_s3)
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
