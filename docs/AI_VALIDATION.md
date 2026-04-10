# AI Validace extrahovaných dat

Systém používá **dvoustupňovou AI extrakci** pro zajištění kvality dat.

## 🎯 Proč validace?

Občas se stává, že AI při extrakci udělá chybu:
- ❌ **Špatné line items**: Extrahuje poznámky místo položek (např. "Reverse charge" jako produkt)
- ❌ **Špatná měna**: Extrahuje "Kc" místo "CZK"
- ❌ **Chybné částky**: Line items se nesčítají na celkovou částku
- ❌ **Špatné datumy**: Nesprávný formát data

## 🔍 Jak validace funguje

### Krok 1: Primární extrakce
```python
# AI extrahuje data z faktury
invoice_data = ai_extractor.extract_invoice_data(invoice_file)
```

### Krok 2: AI validace (automatická)
AI dostane:
1. ✅ Původní dokument (faktura)
2. ✅ Extrahovaná data
3. ✅ Validační checklist

AI zkontroluje:
- **Line items**: Jsou to skutečné produkty/služby?
- **Částky**: Sedí matematika?
- **Formáty**: Jsou datumy a měny v pořádku?

### Krok 3: Korekce
Pokud AI najde chyby, vrátí opravená data:
```
✓ AI validation corrected some fields
  - line_items: [...old...] → null
  - currency: Kc → CZK
```

## 📋 Validační checklist

### 1. **Line Items**
```python
# ❌ ŠPATNĚ - poznámka jako položka
line_items: [
    {
        "description": "Reverse charge applies",
        "quantity": 1,
        "unit_price": 0
    }
]

# ✅ SPRÁVNĚ - skutečný produkt
line_items: [
    {
        "description": "Alien: Isolation (Game)",
        "quantity": 1,
        "unit_price": 171.28
    }
]

# ✅ SPRÁVNĚ - žádné validní line items
line_items: null  # Použije se fallback z total_amount
```

### 2. **Měna**
```python
# ❌ ŠPATNĚ
currency: "Kc"

# ✅ SPRÁVNĚ
currency: "CZK"
```

### 3. **Částky**
```python
# Zkontroluje, že:
total_amount ≈ sum(line_items)
```

### 4. **Datumy**
```python
# ❌ ŠPATNĚ
issue_date: "02/10/2024"

# ✅ SPRÁVNĚ
issue_date: "2024-10-02"
```

## 🎮 Použití

### Automatická validace (výchozí)
```python
# Validace je zapnutá automaticky
invoice_data = ai_extractor.extract_invoice_data(invoice_file)
```

Výstup:
```
✓ AI validation: data looks good
```
nebo
```
✓ AI validation corrected some fields
  - line_items: [...] → null
```

### Vypnutí validace
```python
# Pokud chcete validaci vypnout (rychlejší, ale méně přesné)
invoice_data = ai_extractor.extract_invoice_data(invoice_file, validate=False)
```

## 📊 Výhody

### ✅ Vyšší přesnost
- Zachytí chyby primární extrakce
- Opraví běžné formátovací problémy

### ✅ Automatické opravy
- Nemusíte ručně kontrolovat každou fakturu
- AI opraví, co ví jak opravit

### ✅ Transparentnost
- Vidíte, co bylo opraveno
- Můžete zkontrolovat změny

## ⚠️ Omezení

### Náklady
- **2× AI volání** na fakturu (extrakce + validace)
- Doporučeno pro produkční nasazení
- Pro testování můžete vypnout: `validate=False`

### Podpora
- ✅ **Anthropic (Claude)**: Plná podpora včetně PDF
- ✅ **OpenAI/DeepSeek/Groq**: Pouze obrázky
- ❌ **Ollama**: Lokální model (validace funguje, ale kvalita závisí na modelu)

### Časová náročnost
- Cca **+3-5 sekund** na fakturu
- Záleží na rychlosti AI API

## 🧪 Příklad

### Před validací:
```json
{
  "invoice_number": "786940972572357",
  "supplier_name": "Sony Interactive Entertainment",
  "total_amount": 207.25,
  "currency": "Kc",
  "line_items": [
    {
      "description": "This is not a VAT/GST invoice",
      "quantity": "1",
      "unit_price": "0"
    }
  ]
}
```

### Po validaci:
```json
{
  "invoice_number": "786940972572357",
  "supplier_name": "Sony Interactive Entertainment",
  "total_amount": 207.25,
  "currency": "CZK",
  "line_items": null
}
```

Změny:
```
✓ AI validation corrected some fields
  - currency: Kc → CZK
  - line_items: [{"description": "This is not a VAT/GST invoice"...}] → null
```

## 🔧 Konfigurace

### V config.yaml:
```yaml
ai:
  provider: "anthropic"
  model: "claude-sonnet-4-5-20250929"
  validate_extraction: true  # Zapnout/vypnout validaci globálně
```

### V kódu:
```python
# Přepsat globální nastavení
invoice_data = ai_extractor.extract_invoice_data(
    invoice_file, 
    validate=True  # nebo False
)
```

## 📈 Best Practices

### 1. Pro produkci
```python
# Vždy používejte validaci
validate=True  # výchozí
```

### 2. Pro vývoj/testování
```python
# Můžete vypnout pro rychlejší iteraci
validate=False
```

### 3. Monitoring
Sledujte kolik faktur je opravováno:
```python
if corrected_data != original_data:
    log.info(f"Invoice {invoice_id} corrected by AI validation")
```

### 4. Manuální kontrola
Pro důležité faktury doporučujeme:
1. ✅ AI validace (automatická)
2. ✅ Zobrazit uživateli před odesláním
3. ✅ Možnost ručně upravit

## 🎓 Další zlepšení

V budoucnu můžeme přidat:
- ☐ Třístupňovou validaci (extraction → validation → confirmation)
- ☐ Učení z oprav (fine-tuning)
- ☐ Confidence score pro každé pole
- ☐ Automatické parsování poznámek (reverse charge detection)

## 🆘 Troubleshooting

### Validace selže
```
⚠ Validation failed: ...
  Using original extraction
```
→ Používá se původní extrakce bez oprav

### Validace skipnuta
```
⚠ Validation skipped: Provider doesn't support PDF
```
→ OpenAI API nepodporuje PDF, použijte Anthropic nebo obrázky

### Nesprávné opravy
Pokud AI opravuje správně extrahovaná data:
1. Zkontrolujte validační prompt
2. Možná je v dokumentu něco neobvyklého
3. Můžete validaci vypnout: `validate=False`

