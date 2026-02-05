# Jeans Product Database AI Chat API

API FastAPI dengan kemampuan AI untuk query database produk jeans menggunakan natural language.

## Fitur

- 🤖 **AI Chat Interface**: Tanya tentang produk jeans dalam bahasa natural
- 🔍 **Query Database**: AI akan generate SQL query otomatis berdasarkan pertanyaan
- 🔒 **Read-Only**: Hanya operasi SELECT yang diperbolehkan untuk keamanan
- 📊 **PostgreSQL**: Integrasi dengan database PostgreSQL
- 🚀 **FastAPI**: Modern, cepat, dengan dokumentasi otomatis

## Arsitektur

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── deps.py          # Database dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Configuration settings
│   ├── __init__.py
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models (Jean)
│   └── main.py              # AI Router dengan endpoints
├── fastapi_app.py           # FastAPI application entry point
├── requirements_fastapi.txt # Dependencies
└── .env                     # Environment variables
```

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements_fastapi.txt
```

### 2. Setup Database

Pastikan PostgreSQL sudah berjalan dan database `smgt` sudah dibuat:

```sql
CREATE DATABASE smgt;
```

### 3. Setup Environment Variables

Copy `.env.example` menjadi `.env` dan isi dengan nilai yang sesuai:

```bash
cp .env.example .env
```

Edit `.env`:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smgt
GOOGLE_API_KEY=your_google_gemini_api_key_here
```

### 4. Import Data Jeans

Jalankan script import untuk mengisi tabel jeans:

```bash
python insert_database_from_csv.py
```

### 5. Jalankan Server

```bash
# Development mode dengan auto-reload
python fastapi_app.py

# Atau dengan uvicorn langsung
uvicorn fastapi_app:app --reload --host 0.0.0.0 --port 8000
```

Server akan berjalan di: `http://localhost:8000`

## API Endpoints

### 1. Health Check
```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "Jeans Product API"
}
```

### 2. AI Test Endpoint
```
GET /api/v1/ai/test
```

Response:
```json
{
  "status": "AI Backend is running!"
}
```

### 3. Chat with AI (Main Feature)
```
POST /api/v1/ai/chat
Content-Type: application/json
```

Request Body:
```json
{
  "message": "Berapa total produk jeans yang ada?"
}
```

Response:
```json
{
  "response": "Berdasarkan query database, terdapat 51 produk jeans dalam database."
}
```

## Contoh Pertanyaan

Anda bisa bertanya dalam bahasa natural, AI akan men-generate SQL query yang sesuai:

### Pertanyaan Dasar:
- "Berapa total produk jeans yang ada?"
- "Tampilkan 10 produk jeans pertama"
- "Apa saja brand yang tersedia?"

### Filter Brand:
- "Show me all RALPH LAUREN jeans"
- "Berapa banyak produk dari brand RALPH LAUREN?"

### Query Harga:
- "Tampilkan jeans yang paling mahal"
- "Produk jeans mana yang harganya di bawah 200 USD?"
- "Urutkan jeans berdasarkan harga dari tertinggi ke terendah"

### Diskon:
- "Produk mana yang sedang diskon?"
- "Tampilkan jeans dengan diskon terbesar"

### Query Kompleks:
- "Berapa rata-rata harga jeans per brand?"
- "Tampilkan 5 produk terbaru berdasarkan launch date"
- "Brand mana yang punya produk paling banyak?"

## Cara Kerja

1. User mengirim pertanyaan dalam bahasa natural
2. AI (Google Gemini) memproses pertanyaan dan memahami intent
3. AI memanggil function `generate_query_sql` dengan SQL query yang sesuai
4. System memvalidasi query (hanya SELECT yang diperbolehkan)
5. Query dieksekusi di database PostgreSQL
6. Hasil dikembalikan ke AI
7. AI memformat hasil menjadi respons yang user-friendly
8. Respons dikirim kembali ke user

## Keamanan

### Query Validation
- Hanya operasi `SELECT` yang diperbolehkan
- Keywords berbahaya diblokir: INSERT, UPDATE, DELETE, DROP, ALTER, etc.
- SQL injection protection melalui SQLAlchemy parameterized queries

### Database Session
- Session dibuat per-request
- Auto-close setelah request selesai
- Tidak ada persistent connection

## Testing

### Menggunakan cURL

```bash
# Test health
curl http://localhost:8000/health

# Test AI chat
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa total produk jeans?"}'
```

### Menggunakan Python

```python
import requests

url = "http://localhost:8000/api/v1/ai/chat"
data = {"message": "Show me all RALPH LAUREN jeans"}

response = requests.post(url, json=data)
print(response.json())
```

### Menggunakan Swagger UI

Buka browser dan akses: `http://localhost:8000/docs`

Di sana Anda dapat:
- Melihat semua endpoints
- Test API secara interaktif
- Melihat request/response schema

## Database Schema

Tabel `jeans` memiliki kolom:

- `id`: Integer, Primary Key
- `selling_price`: JSON (contoh: {'USD': 285.9978})
- `discount`: Float (0.0 - 100.0)
- `category_id`: Integer
- `meta_info`: Text (informasi detail produk)
- `product_id`: String, Unique (hash ID)
- `pdp_url`: Text (URL halaman produk)
- `sku`: String
- `brand`: String (nama brand)
- `department_id`: Integer
- `last_seen_date`: Date
- `launch_on`: Date (tanggal peluncuran)
- `mrp`: JSON (harga retail maksimum)
- `product_name`: String (nama produk)
- `feature_image_s3`: Text (URL gambar utama)
- `channel_id`: Integer
- `feature_list`: JSON (array fitur produk)
- `description`: Text (deskripsi produk)
- `style_attributes`: JSON (atribut style)
- `pdp_images_s3`: JSON (array URL gambar)

## Tips Query JSON Fields

Untuk query field JSON seperti `selling_price` atau `mrp`:

```sql
-- Extract value as text
SELECT selling_price->>'USD' as price FROM jeans;

-- Extract value as numeric for calculations
SELECT (selling_price->>'USD')::numeric as price 
FROM jeans 
WHERE (selling_price->>'USD')::numeric > 200;

-- Order by JSON value
SELECT * FROM jeans 
ORDER BY (selling_price->>'USD')::numeric DESC;
```

## Troubleshooting

### Error: "Database session not available"
- Pastikan database PostgreSQL sudah berjalan
- Check connection string di `.env`
- Verify tabel `jeans` sudah dibuat

### Error: "Query is not allowed"
- Hanya SELECT queries yang diperbolehkan
- Pastikan tidak ada keywords berbahaya (INSERT, UPDATE, DELETE, dll)

### Error: Google API
- Pastikan `GOOGLE_API_KEY` sudah di-set di `.env`
- Verify API key valid dan memiliki akses ke Gemini API
- Check quota API

## License

MIT License
