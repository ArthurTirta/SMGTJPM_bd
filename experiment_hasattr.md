# Dokumentasi Eksperimen `hasattr()` di Python

File `experiment_hasattr.py` dibuat untuk mendemonstrasikan bagaimana Python memeriksa keberadaan atribut pada sebuah objek secara dinamis menggunakan fungsi bawaan `hasattr()`.

## Apa itu `hasattr()`?

`hasattr(object, name)` adalah fungsi yang mengembalikan:
- `True`: Jika objek memiliki atribut dengan nama tersebut.
- `False`: Jika objek tidak memiliki atribut tersebut.

Ini sangat berguna ketika kita bekerja dengan objek yang strukturnya bisa berubah-ubah, seperti respons dari API (contohnya Gemini API di `main.py`).

## Penjelasan Kode Eksperimen

### 1. Objek Sederhana
Kita mendefinisikan class `Product`. Kita bisa memeriksa apakah atribut `name` atau `price` ada sebelum mengaksesnya untuk menghindari `AttributeError`.

### 2. Objek Dinamis (Mirip Gemini `Part`)
Dalam `main.py`, objek `Part` dari Gemini bisa berisi `text` saja, atau `function_call` saja.
```python
if hasattr(part, 'function_call') and part.function_call:
    # Proses panggilan fungsi
```
Kode di atas melakukan dua hal:
1. `hasattr(part, 'function_call')`: Memastikan atributnya **ada**.
2. `and part.function_call`: Memastikan nilainya **tidak None/kosong**.

## Cara Menjalankan Eksperimen

Buka terminal dan jalankan:
```bash
python experiment_hasattr.py
```

## Mengapa Ini Penting?
Tanpa `hasattr()`, jika Anda mencoba memanggil `part.function_call` pada objek yang hanya memiliki `text`, Python akan menghentikan program dengan error:
`AttributeError: 'Part' object has no attribute 'function_call'`
