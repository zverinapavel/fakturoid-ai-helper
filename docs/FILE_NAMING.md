# Smart File Naming for Processed Invoices

When an invoice is successfully submitted to Fakturoid, it's automatically moved to the `processed/` directory with a descriptive, searchable filename.

## 📁 Filename Format

```
[Expense Number] - [Supplier Name] - [Description] - [Original Name].[ext]
```

### Components:

1. **Expense Number** - Číslo nákladu z Fakturoidu (např. `FP20240189`)
2. **Supplier Name** - Jméno dodavatele (sanitizované)
3. **Description** - Popis z první položky nebo poznámky (max 50 znaků)
4. **Original Name** - Původní název souboru
5. **Extension** - Původní přípona (`.pdf`, `.jpg`, atd.)

## 📋 Příklady

### Příklad 1: Kompletní data
**Vstup:**
- Soubor: `faktura.pdf`
- Číslo nákladu: `FP20240189`
- Dodavatel: `Alza.cz a.s.`
- První položka: `Test invoice for API integration`

**Výstup:**
```
FP20240189 - Alza.cz a.s. - Test invoice for API integration - faktura.pdf
```

### Příklad 2: Zahraniční faktura
**Vstup:**
- Soubor: `invoice_2024_001.pdf`
- Číslo nákladu: `FP20250181`
- Dodavatel: `Example GmbH`
- Poznámka: `Test invoice from German supplier`

**Výstup:**
```
FP20250181 - Example GmbH - Test invoice from German supplier - invoice_2024_001.pdf
```

### Příklad 3: Bez line items
**Vstup:**
- Soubor: `scan.jpg`
- Číslo nákladu: `FP20240190`
- Dodavatel: `Netflix International B.V.`
- Poznámka: `Subscription payment`

**Výstup:**
```
FP20240190 - Netflix International B.V. - Subscription payment - scan.jpg
```

### Příklad 4: Minimální data (fallback)
**Vstup:**
- Soubor: `document.pdf`
- Žádná data z Fakturoidu

**Výstup:**
```
20241008_143052_document.pdf
```
(Použije se timestamp jako fallback)

## 🔧 Jak to funguje

### 1. Automatické přejmenování při odesílání

```python
# Při použití auto_submit=True
agent = InvoiceProcessingAgent(config, auto_submit=True)
results = agent.process_batch(review=False)

# Soubor je automaticky přejmenován a přesunut
```

### 2. Manuální workflow s přejmenováním

```python
# Krok 1: Extrakce dat
result = agent.process_file(file_path, review=True)
invoice_data = InvoiceData(**result['extracted_data'])

# Krok 2: Kontrola dat
print(f"Supplier: {invoice_data.supplier_name}")
print(f"Amount: {invoice_data.total_amount}")

# Krok 3: Odeslání a přejmenování
submit_result = agent.submit_extracted(file_path, invoice_data)

# Soubor je nyní přejmenován a v processed/
```

## 🧹 Sanitizace názvů souborů

Systém automaticky čistí názvy souborů od neplatných znaků:

| Neplatný znak | Náhrada |
|---------------|---------|
| `/` | `-` |
| `\` | `-` |
| `:` | `-` |

**Příklad:**
- Dodavatel: `Company A/B & Co.`
- Výsledek: `Company A-B & Co.`

## 📏 Omezení délky

- **Popis**: Maximálně 50 znaků
  - Pokud je delší, je zkrácen
  - Příklad: `Very long description that exceeds the...` → `Very long description that exceeds the limit`

- **Celková délka**: Není omezena, ale většina OS má limit ~255 znaků
  - Pokud by byl název příliš dlouhý, systém to automaticky ošetří

## 🔄 Řešení konfliktů

Pokud soubor se stejným názvem již existuje:

```python
# Původní název
"FP20240189 - Alza.cz a.s. - Test - faktura.pdf"

# Pokud existuje, přidá se timestamp
"FP20240189 - Alza.cz a.s. - Test - faktura_20241008_143052_123456.pdf"
```

## 📊 Použití v kódu

### Metoda _move_to_processed()

```python
def _move_to_processed(
    self, 
    file_path: Path, 
    invoice_data: InvoiceData = None,
    fakturoid_response: Dict[str, Any] = None
):
    """Move and rename processed file."""
    # Automaticky sestaví název podle dostupných dat
    # Přesune soubor do processed/
    # Zaloguje: "Moved faktura.pdf → FP20240189 - ..."
```

### Použití

```python
# V process_file() - automaticky při auto_submit
self._move_to_processed(file_path, invoice_data, fakturoid_response)

# Manuálně přes submit_extracted()
agent.submit_extracted(file_path, invoice_data)
```

## 🎯 Výhody

### 1. Snadné vyhledávání
```bash
# Najít všechny faktury od dodavatele
ls processed/ | grep "Alza.cz"

# Najít fakturu podle čísla nákladu
ls processed/ | grep "FP20240189"

# Najít podle popisu
ls processed/ | grep "subscription"
```

### 2. Přehlednost
- Okamžitě vidíte, co soubor obsahuje
- Není třeba otevírat pro zjištění dodavatele
- Číslo nákladu umožňuje rychlé spojení s Fakturoide

### 3. Organizace
- Všechny faktury na jednom místě
- Jednoduchý export/backup
- Snadná archivace podle data (z času modifikace)

## 🔍 Debugging

### Logování
Každé přejmenování je zalogováno:

```
INFO - Moved faktura.pdf → FP20240189 - Alza.cz a.s. - Test invoice - faktura.pdf
```

### Kontrola výsledku

```python
# Po zpracování zkontrolujte processed/
import os
from pathlib import Path

processed_dir = Path("data/processed")
files = list(processed_dir.glob("*"))

for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
    print(f.name)
```

## ⚙️ Konfigurace

Adresář processed lze nastavit v `.env`:

```bash
PROCESSED_DIR=data/processed
# nebo
PROCESSED_DIR=/Users/yourname/Documents/ProcessedInvoices
```

## 📝 Poznámky

1. **Line items priorita**: Pokud faktura má line items, použije se description první položky. Pokud ne, použije se notes.

2. **Bezpečnost**: Systém nikdy nepřepíše existující soubor - vždy přidá timestamp.

3. **Fallback**: Pokud nejsou dostupná žádná data (např. chyba v odesílání), použije se timestamp + původní název.

4. **Encoding**: Názvy souborů jsou v UTF-8, podporují české znaky (háčky, čárky).

## 🆘 Troubleshooting

### Soubor nebyl přesunut

**Příčina:** Chyba při odesílání do Fakturoidu

**Řešení:** Zkontrolujte logy:
```bash
tail -f logs/processor.log
```

### Název je příliš dlouhý

**Příčina:** Velmi dlouhý popis nebo název dodavatele

**Řešení:** Popis je automaticky zkrácen na 50 znaků. Pokud je celkový název problém, systém použije zkrácený fallback.

### Duplicitní soubory

**Příčina:** Zpracování stejné faktury vícekrát

**Řešení:** Systém přidá timestamp - žádný soubor se neztratí. Můžete duplicity smazat ručně.

---

**Last Updated:** 2025-10-08  
**Version:** 0.1.0

