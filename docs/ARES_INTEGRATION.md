# ARES Integrace pro České Dodavatele

Systém automaticky načítá kompletní údaje o českých firmách z **ARES** (Administrativní registr ekonomických subjektů).

📌 **Pro zahraniční dodavatele** viz [FOREIGN_SUPPLIERS.md](./FOREIGN_SUPPLIERS.md)

## 🎯 Jak to funguje

### 1. Automatické vyhledávání

Když vytváříte nového dodavatele s IČO:

```python
result = fakturoid.submit_expense(invoice_data, auto_create_subject=True)
```

Systém postupně:

1. ✅ **Zkusí najít dodavatele v Fakturoidu podle IČO**
2. ✅ **Zkusí najít dodavatele v Fakturoidu podle jména**
3. ⚙️ **Pokud není nalezen, dotáže se ARES API**
4. ✓ **Vytvoří dodavatele s kompletními údaji z ARES**

### 2. Co poskytuje ARES

Z ARES získáme:
- ✅ Oficiální obchodní jméno
- ✅ Úplnou adresu (ulice, číslo, město, PSČ)
- ✅ IČO (registrační číslo)
- ✅ DIČ (daňové číslo)

### 3. Výhody

- 📋 **Přesné údaje** - data z oficiálního registru
- ⚡ **Rychlé** - ARES API je velmi rychlé
- 🔄 **Automatické** - funguje na pozadí
- 🇨🇿 **Jen pro ČR** - pro zahraniční firmy použije extrahovaná data

## 📝 Příklady použití

### Ruční test ARES lookup

```python
from src.fakturoid_client import FakturoidClient
from src.config import config

fakturoid = FakturoidClient(config)

# Vyhledat firmu podle IČO
company_data = fakturoid.get_company_from_ares("27082440")

if company_data:
    print(f"Název: {company_data['name']}")
    print(f"Adresa: {company_data['street']}, {company_data['city']}")
    print(f"DIČ: {company_data['vat_no']}")
```

### Vytvoření dodavatele s ARES lookup

```python
from src.ai_extractor import InvoiceData

# Faktura s českým dodavatelem
invoice = InvoiceData(
    invoice_number="FV001",
    issue_date="2025-01-15",
    supplier_name="Fakturoid s.r.o.",  # Může být nepřesné
    supplier_ico="27082440",  # IČO je klíčové!
    total_amount=1000.0
)

# Automaticky načte přesné údaje z ARES
result = fakturoid.submit_expense(invoice, auto_create_subject=True)
```

### Co se stane:

```
⚙ Creating new subject: Fakturoid s.r.o.
  → Fetching data from ARES for IČO: 27082440
  ✓ Got data from ARES: Fakturoid s.r.o.
  ✓ Subject created with ID: 12345
```

## 🔍 Detekce duplicit

Systém nejprve zkontroluje, jestli dodavatel už neexistuje:

1. **Podle IČO** (nejspolehlivější)
2. **Podle jména** (fallback)

To zabraňuje vytváření duplicitních záznamů.

## ⚠️ Fallback pro zahraniční firmy

Pokud dodavatel nemá IČO nebo ARES lookup selže, použijí se extrahovaná data z faktury:

```
⚙ Creating new subject: Foreign Company Ltd.
  ⚠ ARES lookup failed, using extracted data
  ✓ Subject created with ID: 12346
```

Pro zahraniční firmy systém extrahuje detailní adresu (ulice, město, PSČ, země) a VAT číslo.  
Více info: [FOREIGN_SUPPLIERS.md](./FOREIGN_SUPPLIERS.md)

## 🔧 Technické detaily

### ARES API Endpoint

```
GET https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ICO}
```

### Timeouty

- ARES request timeout: **10 sekund**
- Při selhání pokračuje s extrahovanými daty

### Čištění IČO

IČO je automaticky vyčištěno od mezer a pomlček:
- `"123 456 78"` → `"12345678"`
- `"123-456-78"` → `"12345678"`

## 📊 Statistiky

V notebooku můžete sledovat, co se děje:

```python
# V Cell 5 nebo 7 vidíte output:
✓ Found existing subject by IČO: Fakturoid s.r.o.
# nebo
⚙ Creating new subject: New Company s.r.o.
  → Fetching data from ARES for IČO: 12345678
  ✓ Got data from ARES: New Company s.r.o.
  ✓ Subject created with ID: 99999
```

## 🎓 Best Practices

1. **Vždy extrahujte IČO** z faktur českých dodavatelů
2. **Nechte systém načíst ARES data** - budou přesnější
3. **Zkontrolujte logy** - uvidíte, jestli ARES fungoval
4. **Pro zahraniční faktury** - extrahujte co nejpřesnější data

## 🐛 Troubleshooting

### ARES vrací 404
- IČO neexistuje nebo je neplatné
- Zkontrolujte IČO na https://wwwinfo.mfcr.cz/ares/

### ARES timeout
- Dočasný problém s ARES API
- Systém použije extrahovaná data

### Duplicitní dodavatelé
- Systém hledá podle IČO i jména
- Pokud máte duplicity, sloučte je ručně ve Fakturoidu

