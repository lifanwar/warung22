# 📋 Warung22 Menu API

AI-powered menu chatbot and management API for Warung22 restaurant.

---

## 🚀 Installation

### NixOS (Recommended)

```bash
nix-shell
```

### Other Linux

```bash
pip install -r requirements.txt
```

### Environment Setup

Create `.env` file:

```bash
API_KEY=PujanggaTSDUU@2$$%!!!
SUPABASE_URL=your-supabase-url	SUPABASE_KEY=your-supabase-key
```

---

## 🚀 Usage

### CLI Mode

```bash
python main.py cli
```

### API Server

**Production:**
```bash
python main.py api
```

**Development:**
```bash
python main.py api --reload
```

Server runs on `http://localhost:8000`

---

## 📍 API Reference

### 👑 Authentication

All endpoints require API key in header:
```
X-API-Key: PujanggaTSDUU@2$$%!!!
```

### 🰘� Chatbot Endpoints

#### Health Check

```bash
curl http://localhost:8000/
```

#### Ask Question (AI Chatbot)

Ask Menu:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H 'X-API-Key: PujanggaTSDUU@2$$%!!!' \
  -d '{
	"question": "What menu items do you have?"
  }'
```

Edit Availability:
```bash
curl -X POST "http://localhost:8000/edit-menu" \
  -H "Content-Type: application/json" \
  -H 'X-API-Key: PujanggaTSDUU@2$$%!!!' \
  -d '{
    "question": "semua ikan habis"
  }'
```

#### Refresh Cache

```bash
curl -X POST http://localhost:8000/refresh \
  -H "X-API-Key: PujanggaTSDUU@2$$%!!!"
```

#### Cache Stats

```bash
curl http://localhost:8000/cache/stats \
  -H "X-API-Key: PujanggaTSDUU@2$$%!!!"
```

### 📋 CRUD Endpoints

#### 1️⃣ Get All Menu

```bash
curl http://localhost:8000/menu/ \
  -H 'X-API-Key: PujanggaTSDUU@2$$%!!!'
```

Response:
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
  }
]
```

###  2️⃣ Create Menu

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

Valid categories: `protein_ayam`, `ati_ampela`, `protein_ikan`, `protein_ringan`, `karbo`, `paket_hemat`, `menu_kuah`, `minum_cold`, `minum_hot`

###  3️⃣ Update Availability (Single)

Mark as sold out:
```bash
curl -X PATCH http://localhost:8000/menu/1/availability \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: PujanggaTSDUU@2$$%!!!' \
  -d '{"is_available": false}'
```

Mark as available:
```bash
curl -X PATCH ttp://localhost:8000/menu/1/availability \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: PujanggaTSDUU@2$$%!!!' \
  -d '{
	"is_available": true
  }'
```

#### 4️⃣ Update Availability (Bulk)

Update multiple items at once:
```bash
curl -X PATCH http://localhost:8000/menu/bulk/availability \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: PujanggaTSDUU@2$$%!!!' \
  -d '{
	"item_ids": [1, 2, 5, 10],
	"is_available": false
  }'
```

---

## 🚂 Error Codes

| Code | Description |
|------|-------------|
| 403 | Invalid API Key |
| 422 | Invalid input (e.g. invalid category) |
| 500 | Server error |

---

## ⚡️ Performance

- **First GET:** ~200ms (database query)
- **Subsequent GET:** ~5ms (cache hit)
- **Auto-cache refresh:** After CREATE/UPDATE

---

## 🎯 Features

- ✅ AI-powered chatbot (Perplexity + LangChain)
- ✅ In-memory caching with Supabase
- ✅ CRUD operations for menu management
- ✅ Bulk update availability
- ✅ API key authentication
- ✅ Realtime cache refresh

---

**Version:** 1.0.0  
**Last Updated:** November 27, 2025