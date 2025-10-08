# Quick Reference - Fakturoid Invoice Processor

Rychlá nápověda pro běžné úlohy.

## 🚀 Rychlý start

### 1. Automatické zpracování
```python
from src.agent import InvoiceProcessingAgent

agent = InvoiceProcessingAgent(auto_submit=True)
results = agent.process_batch(review=False)
```

### 2. S manuální kontrolou
```python
agent = InvoiceProcessingAgent()
results = agent.process_batch(review=True)
```

### 3. Extract → Review → Submit
```python
# Extrakce
result = agent.process_file(file_path, review=True)
invoice_data = InvoiceData(**result['extracted_data'])

# Kontrola a případně úprava dat
# ...

# Odeslání
submit_result = agent.submit_extracted(file_path, invoice_data)
```

## 📁 Názvy zpracovaných souborů

**Format:**
```
[Číslo nákladu] - [Dodavatel] - [Popis] - [Původní název].[přípona]
```

**Příklad:**
```
FP20240189 - Alza.cz a.s. - Test invoice - faktura.pdf
```

## ⚙️ Proměnné prostředí (.env)

### Povinné
```bash
ANTHROPIC_API_KEY=sk-ant-...
FAKTUROID_CLIENT_ID=...
FAKTUROID_CLIENT_SECRET=...
FAKTUROID_ACCOUNT_SLUG=...
```

### Volitelné
```bash
PROCESSING_MODE=manual      # nebo auto
AUTO_SUBMIT=false           # nebo true
INVOICES_DIR=data/invoices
PROCESSED_DIR=data/processed
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
```

## 🎯 Běžné workflow

### Denní použití
```bash
# 1. Přidejte faktury do data/invoices/
# 2. Spusťte zpracování
python process_invoices.py

# 3. Zkontrolujte výsledky
ls data/processed/
```

### V Jupyter notebooku
```python
# Cell 1: Import a inicializace
from src.agent import InvoiceProcessingAgent
from src.config import config

agent = InvoiceProcessingAgent(config)

# Cell 2: Test připojení
agent.test_connections()

# Cell 3: Zpracování
results = agent.process_batch(review=True, max_files=5)

# Cell 4: Zobrazení výsledků
for r in results:
    print(f"{r['file']}: {r['status']}")
```

## 🔍 Kontrola stavu

### Zobrazit konfiguraci
```python
from src.config import config

print(f"Invoices: {config.directories.invoices}")
print(f"Mode: {config.processing.mode}")
print(f"Auto-submit: {config.processing.auto_submit}")
```

### Zobrazit zpracované soubory
```python
from pathlib import Path
from datetime import datetime

processed = Path("data/processed")
files = sorted(processed.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)

for f in files[:10]:
    mtime = datetime.fromtimestamp(f.stat().st_mtime)
    print(f"{f.name} ({mtime:%Y-%m-%d %H:%M})")
```

### Zobrazit logy
```bash
tail -f logs/processor.log
```

## 🛠️ Troubleshooting

### Connection failed
```python
# Test připojení
from src.fakturoid_client import FakturoidClient
from src.config import config

client = FakturoidClient(config)
print(client.test_connection())
```

### API key chybí
```bash
# Zkontrolujte .env
cat .env | grep ANTHROPIC_API_KEY
cat .env | grep FAKTUROID_
```

### No files found
```bash
# Zkontrolujte adresář
ls -la data/invoices/
```

## 📊 Užitečné příkazy

### Najít faktury od dodavatele
```bash
ls data/processed/ | grep "Alza"
```

### Najít podle čísla nákladu
```bash
ls data/processed/ | grep "FP20240189"
```

### Počet zpracovaných faktur
```bash
ls data/processed/ | wc -l
```

### Najít poslední zpracované
```bash
ls -lt data/processed/ | head -10
```

## 📚 Další dokumentace

- **Setup**: `docs/setup_guide.md`
- **Env vars**: `docs/ENVIRONMENT_VARIABLES.md`
- **File naming**: `docs/FILE_NAMING.md`
- **ARES**: `docs/ARES_INTEGRATION.md`
- **Foreign suppliers**: `docs/FOREIGN_SUPPLIERS.md`

---
**Tip:** Pro více příkladů použijte `python example_usage.py`
