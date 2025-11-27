# 📋 Warung22 Menu CRUD API Documentation

API untuk mengelola menu Warung22 dengan operasi Create, Read, dan Update Availability.

## 🔡 Authentication

Semua endpoint memerlukan API Key di header:
```
X-API-Key: PujanggaTSDUU2@$$%!!!
```

---

## 📍 API Endpoints

### 1️⃣ Get All Menu Items

**Endpoint:** `GET /menu/`

**Request:**
```bash
curl http://localhost:8000/menu/ \
  -H 'X-API-Key: PujanggaTSDUU@2$$%!!!'
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "category": "protein_ayam",
    "name": "Ayam Crispy Jumbo",
    "harga": 90,
    "is_available": true,
    "created_at": "2025-11-27T18:00:00+02:00",
    "updated_at": "2025-11-27T18:00:00+02:00"
  },
  {
    "id": 2,
    "category": "protein_ayam",
    "name": "Geprek Jumbo",
    "harga": 90,
    "is_available": false,
    "created_at": "2025-11-27T18:00:00+02:00",
    "updated_at": "2025-11-27T20:10:00+02:00"
  }
]
```

---

### 2️⃣ Create New Menu Item

**Endpoint:** `POST /menu/`

**Request:**
```bash
curl -X POST http://localhost:8000/menu/ \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: PujanggaTSDUU@2$$%!!!' \
  -d '{
    "category": "protein_ayam",
    "name": "Ayam Geprek Special",
    "harga": 95,
    "is_available": true
  }'
```

**Response:** `201 Created`
```json
{
  "id": 54,
  "category": "protein_ayam",
  "name": "Ayam Geprek Special",
  "harga": 95,
  "is_available": true,
  "created_at": "2025-11-27T21:20:00+02:00",
  "updated_at": "2025-11-27T21:20:00+02:00"
}
```

**Valid Categories:**
- `protein_ayam`
- `ati_ampela`
- `protein_ikan`
- `protein_ringan`
- `karbo`
- `paket_hemat`
- `menu_kuah`
- `minum_cold`
- `minum_hot`

---

### 3️⃣ Update Menu Availability

**Endpoint:** `PATCH /menu/{item_id}/availability`

**Mark as SOLD OUT:**
```bash
curl -X PATCH http://localhost:8000/menu/1/availability \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: PujanggaTSDUU@2$$%!!!' \
  -d '{
	"is_available": false
  }'
```

**Mark as AVAILABLE:**
```bash
curl -X PATCH http://localhost:8000/menu/1/availability \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: PujanggaTSDUU@2$$%!!!' \
  -d '{
	"is_available": true
  }'
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "category": "protein_ayam",
  "name": "Ayam Crispy Jumbo",
  "harga": 90,
  "is_available": false,
  "created_at": "2025-11-27T18:00:00+02:00",
  "updated_at": "2025-11-27T21:25:00+02:00"
}
```

---

## 🚂 Error Responses

### Invalid API Key
**Status:** `403 Forbidden`
```json
{
  "detail": "Invalid API Key"
}
```

### Invalid Category
**Status:** `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "category"],
      "msg": "Value error, Category must be one of: protein_ayam, ati_ampela, ...",
      "input": "invalid_category"
    }
  ]
}
```

### Item Not Found
**Status:** `500 Internal Server Error`
```json
{
  "detail": "Failed to update availability: Item with ID 999 not found"
}
```

---

## ⚡‏ Performance

- **First GET request:** ~200ms (cache miss, query database)
- **Subsequent GET:** ~5ms (cache hit, from memory)
- **After CREATE/UPDATE:** Cache auto-refreshed

---

## 🚀 Quick Start

1. **Start server:**
   ```bash
   python main.py api
   ```

2. **Get all menu:**
   ```bash
   curl http://localhost:8000/menu/ -H 'X-API-Key: PujanggaTSDUU@2$$%!!!'
   ```

3. **Create menu:**
   ```bash
   curl -X POST http://localhost:8000/menu/ \
     -H 'Content-Type: application/json' \
     -H 'X-API-Key: PujanggaTSDUU@2$$%!!!' \
     -d '{"category":"minum_cold","name":"Es Teh Manis","harga":20}'
   ```

4. **Update availability:**
   ```bash
   curl -X PATCH http://localhost:8000/menu/1/availability \
     -H 'Content-Type: application/json' \
     -H 'X-API-Key: PujanggaTSDUU@2$$%!!!' \
     -d '{"is_available":false}'
   ```

---

**Version:** 1.0.0  
**Last Updated:** November 27, 2025