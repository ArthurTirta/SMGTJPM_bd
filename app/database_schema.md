# Database Schema: Jeans Table

Table Name: `jeans`

## Columns:

1. **id** (Integer, Primary Key, Auto-increment)
   - Unique identifier for each jeans product

2. **selling_price** (JSON)
   - Current selling price with currency
   - Format: {'USD': 285.9978}

3. **discount** (Float)
   - Discount percentage (0.0 to 100.0)
   - Default: 0.0

4. **category_id** (Integer, Indexed)
   - Category identifier for the jeans
   - Common value: 56

5. **meta_info** (Text)
   - Detailed product information including fit, size, measurements, and care instructions

6. **product_id** (String, 255 chars, Unique, Indexed)
   - Unique hash identifier for the product

7. **pdp_url** (Text)
   - Product detail page URL

8. **sku** (String, 255 chars, Indexed)
   - Stock Keeping Unit identifier

9. **brand** (String, 255 chars, Indexed)
   - Brand name (e.g., "RALPH LAUREN")

10. **department_id** (Integer, Indexed)
    - Department identifier
    - Common value: 2

11. **last_seen_date** (Date)
    - Last date the product was seen/available

12. **launch_on** (Date)
    - Product launch date

13. **mrp** (JSON)
    - Maximum Retail Price with currency
    - Format: {'USD': 285.9978}

14. **product_name** (String, 500 chars, Indexed)
    - Name of the jeans product

15. **feature_image_s3** (Text)
    - URL to the main product image

16. **channel_id** (Integer, Indexed)
    - Sales channel identifier
    - Common value: 14

17. **feature_list** (JSON)
    - Array of product features and specifications

18. **description** (Text)
    - Detailed product description

19. **style_attributes** (JSON)
    - Style-related attributes as JSON object

20. **pdp_images_s3** (JSON)
    - Array of product image URLs

## Example Queries:

```sql
-- Get all jeans from a specific brand
SELECT * FROM jeans WHERE brand = 'RALPH LAUREN' LIMIT 10;

-- Get jeans with discounts
SELECT product_name, brand, discount FROM jeans WHERE discount > 0 ORDER BY discount DESC LIMIT 20;

-- Get jeans by price range (you'll need to cast JSON to numeric)
SELECT product_name, brand, selling_price FROM jeans LIMIT 10;

-- Count jeans by brand
SELECT brand, COUNT(*) as total FROM jeans GROUP BY brand ORDER BY total DESC;

-- Get recent products
SELECT product_name, brand, last_seen_date FROM jeans ORDER BY last_seen_date DESC LIMIT 10;

-- Get jeans with price filtering
SELECT product_name, brand, (selling_price->>'USD')::numeric as price_usd 
FROM jeans 
WHERE (selling_price->>'USD')::numeric > 200 
ORDER BY price_usd DESC 
LIMIT 10;

-- Average price per brand
SELECT brand, 
       COUNT(*) as total_products,
       AVG((selling_price->>'USD')::numeric) as avg_price 
FROM jeans 
GROUP BY brand 
ORDER BY avg_price DESC;
```

## Notes:

- JSON fields (selling_price, mrp, feature_list, style_attributes, pdp_images_s3) need special handling when querying
- Use `selling_price->>'USD'` to extract USD value from JSON in PostgreSQL
- Use `(selling_price->>'USD')::numeric` to convert to number for calculations
- All text fields support full-text search capabilities
- Always use LIMIT clause to avoid retrieving too many rows
- Brand names are case-sensitive in queries
