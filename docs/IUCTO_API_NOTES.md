# iÚčto API - Poznámky a řešení problémů

Poznámky k práci s iÚčto API na základě testování.

## ⚠️ SSL Certificate Issue

### Problém:
```
SSLError: certificate verify failed: Hostname mismatch
```

### Možné příčiny:
1. **Špatná URL** - možná je API na jiné subdoméně
2. **SSL certifikát** - server má problém s certifikátem
3. **Redirecty** - API endpoint může přesměrovávat

### Řešení:

#### Option 1: Zkontrolujte správnou URL

**✅ Správná URL:** `https://online.iucto.cz/api`

Ostatní URL varianty (pokud by byla potřeba):
- ❌ `app.iucto.cz/api` - stará/neplatná
- ❌ `api.iucto.cz` - neexistuje
- ✅ `online.iucto.cz/api` - **správně!**

**Konfigurace v `config/migration_settings.yaml`:**
```yaml
iucto:
  base_url: "https://online.iucto.cz/api"  # ✓ Správně
```

#### Option 2: Manuální test API

```bash
# Test v terminálu (bez SSL verifikace)
curl -k -H "X-Api-Key: your_key" https://app.iucto.cz/api/invoices?limit=1

# Nebo:
curl -k -H "X-Api-Key: your_key" https://api.iucto.cz/invoices?limit=1
```

Podívejte se jaká URL funguje.

#### Option 3: Kontaktujte iÚčto support

Zjistěte aktuální API endpoint:
- Email: podpora@iucto.cz
- Dokumentace: https://iucto.docs.apiary.io/

---

## 📋 Známé endpointy (z dokumentace)

Based on Apiary docs (https://iucto.docs.apiary.io/):

```
GET /api/invoices          # Vystavené faktury
GET /api/expenses          # Přijaté faktury
GET /api/invoices/{id}     # Detail faktury
GET /api/customers         # Klienti
GET /api/suppliers         # Dodavatelé
```

---

## 🔧 Dočasné workaround (pro testování)

Pokud potřebujete rychle otestovat a SSL nepomůže:

```python
# V iucto_client.py - přidat do __init__:
import urllib3
urllib3.disable_warnings()

self.session = requests.Session()
self.session.verify = False  # ⚠️ Jen pro testování!
```

**⚠️ POZOR:** Toto je bezpečnostní riziko! Používejte jen pro testování, ne v produkci.

---

## 🧪 Debugging kroky

### 1. Zkontrolujte API klíč

```python
import os
print(f"API Key: {os.getenv('IUCTO_API_KEY')[:10]}...")  # První 10 znaků
```

### 2. Test různých URL

```python
from iucto_migration.iucto_client import IUctoClient

urls = [
    "https://app.iucto.cz/api",
    "https://api.iucto.cz",
    "https://www.iucto.cz/api",
    "https://iucto.cz/api"
]

for url in urls:
    print(f"\nTrying: {url}")
    client = IUctoClient(api_key, base_url=url)
    if client.test_connection():
        print(f"✓ SUCCESS with {url}")
        break
```

### 3. Manuální HTTP test

```python
import requests

headers = {'X-Api-Key': 'your_key'}

# Test různé URL
response = requests.get('https://app.iucto.cz/api/invoices', 
                       headers=headers, 
                       params={'limit': 1},
                       verify=False)  # Vypne SSL check

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"Data: {response.json()}")
```

---

## 📞 Support

Pokud máte problémy s API:

1. **Zkontrolujte dokumentaci:** https://iucto.docs.apiary.io/
2. **Kontaktujte support:** podpora@iucto.cz
3. **Zeptejte se na:**
   - Správnou API base URL
   - Jak získat API klíč
   - Jaké endpointy jsou dostupné

---

## ✅ Jakmile API funguje

Pokud zjistíte správnou URL, upravte:

1. **`config/migration_settings.yaml`:**
```yaml
iucto:
  base_url: "https://correct-url-here/api"
```

2. **Nebo v notebooku:**
```python
iucto = IUctoClient(api_key, base_url="https://correct-url/api")
```

---

**Last Updated:** 2025-10-08  
**Status:** Investigating SSL/URL issues

