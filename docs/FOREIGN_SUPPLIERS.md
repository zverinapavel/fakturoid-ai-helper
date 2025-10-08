# Podpora zahraničních dodavatelů

Systém nyní plně podporuje zahraniční dodavatele s detailní extrakcí adresy a VAT čísel.

## 🌍 Co se extrahuje z faktury

### Pro **české dodavatele** (CZ):
- ✅ **IČO** (`supplier_ico`) - 8 číslic
- ✅ **DIČ** (`supplier_dic`) - např. CZ12345678
- ✅ Adresa → načte se z **ARES** automaticky

### Pro **zahraniční dodavatele** (EU/non-EU):
- ✅ **VAT Number** (`supplier_vat_number`) - např. DE123456789, GB999999999
- ✅ **Ulice** (`supplier_street`) - např. "Hauptstraße 123"
- ✅ **Město** (`supplier_city`) - např. "Berlin"
- ✅ **PSČ** (`supplier_zip`) - např. "10115"
- ✅ **Země** (`supplier_country`) - ISO kód nebo název (DE, Germany, etc.)

## 📋 Extrahovaná pole

```python
class InvoiceData:
    # Supplier identification
    supplier_ico: Optional[str]           # Czech IČO (8 digits)
    supplier_dic: Optional[str]           # Czech DIČ (CZ...)
    supplier_vat_number: Optional[str]    # EU VAT (DE..., GB..., etc.)
    
    # Detailed address
    supplier_street: Optional[str]        # Street and number
    supplier_city: Optional[str]          # City
    supplier_zip: Optional[str]           # Postal code
    supplier_country: Optional[str]       # Country (ISO code)
    supplier_address: Optional[str]       # Fallback: complete address
```

## 🤖 AI Extraction

AI automaticky rozpozná:

### České faktury:
```json
{
  "supplier_name": "Fakturoid s.r.o.",
  "supplier_ico": "27082440",
  "supplier_dic": "CZ27082440",
  "supplier_country": "CZ"
}
```

### Německé faktury:
```json
{
  "supplier_name": "Example GmbH",
  "supplier_street": "Hauptstraße 123",
  "supplier_city": "Berlin",
  "supplier_zip": "10115",
  "supplier_country": "DE",
  "supplier_vat_number": "DE123456789"
}
```

### UK faktury:
```json
{
  "supplier_name": "Example Ltd",
  "supplier_street": "123 Oxford Street",
  "supplier_city": "London",
  "supplier_zip": "W1D 2HG",
  "supplier_country": "GB",
  "supplier_vat_number": "GB999999999"
}
```

### USA faktury:
```json
{
  "supplier_name": "Example Inc.",
  "supplier_street": "123 Main St",
  "supplier_city": "New York",
  "supplier_zip": "10001",
  "supplier_country": "US"
}
```

## 🔄 Automatické vytvoření dodavatele

### České firmy:
1. ✅ Hledá podle IČO
2. ✅ Pokud nenajde → volá **ARES**
3. ✓ Vytvoří s přesnými údaji z ARES

### Zahraniční firmy:
1. ✅ Hledá podle jména
2. ✅ Pokud nenajde → použije extrahovaná data
3. ✓ Vytvoří s detailní adresou z faktury

## 📝 Příklad použití

### V kódu:

```python
from src.ai_extractor import InvoiceData

# Německý dodavatel
invoice = InvoiceData(
    invoice_number="INV-2025-001",
    issue_date="2025-01-15",
    supplier_name="Deutsche Firma GmbH",
    total_amount=1000.00,
    currency="EUR",
    # Detailní adresa
    supplier_street="Berliner Straße 456",
    supplier_city="München",
    supplier_zip="80331",
    supplier_country="DE",
    # VAT číslo
    supplier_vat_number="DE987654321"
)

# Automaticky vytvoří dodavatele s kompletní adresou
result = fakturoid.submit_expense(invoice, auto_create_subject=True)
```

### Výstup:
```
⚙ Creating new subject: Deutsche Firma GmbH
  ✓ Subject created with ID: 12345
✓ Expense created successfully!
```

Ve Fakturoidu uvidíte dodavatele s:
- Název: Deutsche Firma GmbH
- Ulice: Berliner Straße 456
- Město: München
- PSČ: 80331
- Země: DE
- DIČ: DE987654321

## 🎯 Best Practices

### 1. Vždy extrahujte co nejvíce detailů
```python
# ✅ DOBŘE - detailní adresa
supplier_street="123 Main St"
supplier_city="New York"
supplier_zip="10001"
supplier_country="US"

# ❌ ŠPATNĚ - jen jeden string
supplier_address="123 Main St, New York, 10001, US"
```

### 2. ISO kódy zemí
Používejte ISO kódy (2 písmena):
- `CZ` - Česko
- `DE` - Německo
- `GB` - Velká Británie
- `US` - USA
- `FR` - Francie
- `AT` - Rakousko
- `SK` - Slovensko
- `PL` - Polsko

### 3. VAT čísla
Formát: `KÓDZEME + ČÍSLO`
- `DE123456789` - Německo
- `GB999999999` - UK
- `FR12345678901` - Francie
- `CZ12345678` - Česko (DIČ)

### 4. Fallback na supplier_address
Pokud AI nemůže rozdělit adresu:
```python
supplier_address="Celá adresa jako jeden řetězec"
```
Systém ji použije do pole `street` ve Fakturoidu.

## 🧪 Testování

### Cell 7 v notebooku `04_fakturoid_integration.ipynb`:
```python
# Test zahraničního dodavatele
foreign_invoice = InvoiceData(
    invoice_number="DE-2025-001",
    supplier_name="Example GmbH",
    supplier_street="Hauptstraße 123",
    supplier_city="Berlin",
    supplier_zip="10115",
    supplier_country="DE",
    supplier_vat_number="DE123456789",
    total_amount=500.00,
    currency="EUR"
)

result = fakturoid.submit_expense(foreign_invoice, auto_create_subject=True)
```

## 🔍 Detekce duplicit

Systém kontroluje duplicity:
1. **Podle IČO** (jen pro CZ)
2. **Podle jména** (všichni dodavatelé)

**Pozor:** Pro zahraniční firmy neexistuje centrální registr jako ARES, takže se spoléháme na název!

## ⚠️ Známá omezení

1. **Zahraniční firmy**
   - Není automatická validace VAT čísel (jako ARES pro CZ)
   - Možné duplicity při drobných rozdílech v názvu

2. **Adresy**
   - AI musí správně rozpoznat strukturu adresy
   - Pro složité adresy může použít `supplier_address` fallback

3. **Měny**
   - Fakturoid podporuje různé měny
   - Přepočty se nedělají automaticky

## 📊 Podporované země

Systém funguje pro **všechny země**, nejčastěji:

🇨🇿 **Česko** - s ARES lookup  
🇩🇪 **Německo**  
🇬🇧 **Velká Británie**  
🇺🇸 **USA**  
🇫🇷 **Francie**  
🇦🇹 **Rakousko**  
🇸🇰 **Slovensko**  
🇵🇱 **Polsko**  
🇳🇱 **Nizozemsko**  
🇮🇹 **Itálie**  

## 🆘 Troubleshooting

### AI neextrahuje detailní adresu
- Zkontrolujte, jestli je adresa viditelná na faktuře
- AI použije `supplier_address` jako fallback

### Duplicitní dodavatelé
- Hledejte přesně podle názvu
- Sloučte ručně ve Fakturoidu

### Chybné VAT číslo
- Zkontrolujte formát: `KÓDZEME + ČÍSLO`
- AI může udělat chybu při OCR

### Chybí země
- AI automaticky detekuje z VAT čísla nebo obsahu faktury
- Pokud chybí, nastaví se "CZ" jako výchozí (pokud má IČO)

