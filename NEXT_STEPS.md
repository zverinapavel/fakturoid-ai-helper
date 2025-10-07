# Next Steps - Co dělat dál?

Gratulujeme! Projekt Fakturoid Invoice Processor je úspěšně nastavený. 🎉

## Co bylo vytvořeno?

✅ Kompletní AI agent pro zpracování faktur  
✅ Integrace s Fakturoid API  
✅ 5 Jupyter notebooků pro vývoj  
✅ CLI skripty pro použití  
✅ Podrobná dokumentace (CZ + EN)  
✅ Konfigurace s YAML a .env soubory  
✅ Git repozitář s prvním commitem  

## Příští kroky (v pořadí)

### 1. Získejte API klíče (5 minut)

#### Anthropic API klíč
```
1. Jděte na: https://console.anthropic.com
2. Zaregistrujte se / Přihlaste se
3. Vytvořte API klíč
4. Zkopírujte ho
```

#### Fakturoid API klíč
```
1. Jděte na: https://app.fakturoid.cz
2. Nastavení → API
3. Vygenerujte API klíč
4. Zkopírujte: email, API klíč, account slug
```

### 2. Vytvořte .env soubor (2 minuty)

V kořenové složce projektu vytvořte soubor `.env`:

```bash
# Přímo v terminálu:
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-vaše_klíč_zde
FAKTUROID_EMAIL=vas@email.cz
FAKTUROID_API_KEY=váš_fakturoid_klíč
FAKTUROID_ACCOUNT_SLUG=váš_účet
PROCESSING_MODE=manual
AUTO_SUBMIT=false
LOG_LEVEL=INFO
EOF
```

Nebo vytvořte ručně a vložte své údaje.

### 3. Instalujte závislosti (2 minuty)

```bash
# Jste už ve správné složce
cd /Users/pavelzverina/AiProjects/fakturoid

# Instalace už proběhla, ale pokud chcete znovu:
uv sync

# Aktivace virtuálního prostředí
source .venv/bin/activate
```

### 4. Test konfigurace (1 minuta)

```bash
# Otestujte, že vše funguje
python -c "from src.config import config; print('✓ Config OK')"

# Nebo spusťte příklady
python example_usage.py
# → Vyberte možnost 4 nebo 5
```

### 5. Přidejte testovací faktury (1 minuta)

```bash
# Zkopírujte nějaké faktury do:
cp /cesta/k/vašim/fakturám/*.pdf data/invoices/
# nebo
cp /cesta/k/vašim/fakturám/*.jpg data/invoices/
```

Podporované formáty: PDF, JPG, PNG, GIF, WEBP

### 6. První test s notebookem (10 minut)

```bash
# Spusťte Jupyter
jupyter notebook

# Otevřete postupně:
# 1. notebooks/01_document_loader.ipynb
# 2. notebooks/02_data_extraction.ipynb
# 3. notebooks/05_orchestration.ipynb
```

V noteboocích uvidíte, jak systém funguje krok po kroku.

### 7. Zpracujte první fakturu (5 minut)

```bash
# S manuální kontrolou (doporučeno)
python process_invoices.py
```

Systém:
1. Najde faktury v `data/invoices/`
2. Zeptá se, zda chcete pokračovat
3. Vyčte data pomocí AI
4. Zobrazí výsledky ke kontrole
5. Zeptá se, zda odeslat do Fakturoid

## Možnosti zpracování

### A) Příkazová řádka (nejjednodušší)

```bash
# S manuální kontrolou
python process_invoices.py

# Automaticky (bez kontroly) - POZOR!
python process_invoices.py --auto

# Max 5 faktur
python process_invoices.py --max 5

# Nápověda
python process_invoices.py --help
```

### B) Python skript

```python
from src.agent import InvoiceProcessingAgent

# Inicializace
agent = InvoiceProcessingAgent()

# Test připojení
if agent.test_connections():
    # Zpracování s kontrolou
    results = agent.process_batch(review=True, max_files=5)
    
    # Výsledky
    for r in results:
        print(f"{r['file']}: {r['status']}")
```

### C) Jupyter notebook

```bash
jupyter notebook
# → Otevřete notebooks/05_orchestration.ipynb
# → Spusťte jednotlivé buňky
```

## Co očekávat?

### První faktura (10-30 sekund)
1. Načtení souboru ✓
2. AI extrakce dat (Claude) ⏱️ 10-20s
3. Validace ✓
4. Zobrazení výsledků ✓
5. Potvrzení odeslání (pokud manual) ✓
6. Odeslání do Fakturoid ⏱️ 2-5s
7. Přesun do processed/ ✓

### Co se vyčte?
- **Povinné**: číslo faktury, datum, dodavatel, částka
- **Volitelné**: splatnost, VS, IČO, DIČ, adresa, položky, DPH

## Denní používání

```bash
# 1. Přidejte faktury
cp nové_faktury/*.pdf data/invoices/

# 2. Spusťte zpracování
python process_invoices.py

# 3. Zkontrolujte a schvalte

# 4. Zkontrolujte výsledek ve Fakturoid

# 5. Hotovo! Zpracované faktury jsou v data/processed/
```

## Tipy pro začátek

1. **První spuštění**: Vždy s manuální kontrolou (`review=True`)
2. **Testujte s kopií**: První faktury zkuste na kopiích
3. **Kontrolujte logy**: `tail -f logs/processor.log`
4. **Pozor na auto-submit**: Používejte až po testování
5. **Zálohujte**: Originální faktury uchovejte

## Řešení problémů

### "ANTHROPIC_API_KEY not set"
```bash
# Zkontrolujte .env soubor
cat .env
# Ujistěte se, že obsahuje správný klíč
```

### "Fakturoid connection failed"
```python
# Test připojení
python -c "
from src.fakturoid_client import FakturoidClient
from src.config import config

client = FakturoidClient(
    email=config.fakturoid.email,
    api_key=config.fakturoid.api_key,
    account_slug=config.fakturoid.account_slug
)
print('Connection:', client.test_connection())
"
```

### "No invoice files found"
```bash
# Zkontrolujte obsah adresáře
ls -la data/invoices/
# Přidejte faktury
cp vaše_faktury/*.pdf data/invoices/
```

## Dokumentace

- **Rychlý start**: `QUICKSTART.md` (5 minut)
- **Kompletní návod**: `docs/setup_guide.md`
- **Český README**: `docs/czechREADME.md`
- **Příklady**: `example_usage.py`
- **Shrnutí projektu**: `PROJECT_SUMMARY.md`

## Užitečné příkazy

```bash
# Zobrazit konfiguraci
python -c "from src.config import config; import json; print(json.dumps(config.model_dump(), indent=2, ensure_ascii=False))"

# Zobrazit logy
tail -f logs/processor.log

# Spočítat faktury
ls data/invoices/*.pdf | wc -l
ls data/processed/ | wc -l

# Smazat zpracované (pokud testujete)
rm data/processed/*

# Znovu načíst prostředí
source .venv/bin/activate
```

## Přizpůsobení

### Změnit AI model
Upravte `config/settings.yaml`:
```yaml
ai:
  model: "claude-3-opus-20240229"  # Silnější model
```

### Změnit povinná pole
Upravte `config/settings.yaml`:
```yaml
extraction:
  required_fields:
    - invoice_number
    - issue_date
    - supplier_name
    - total_amount
    - custom_field  # Vaše pole
```

### Povolit auto-submit
Upravte `.env`:
```
AUTO_SUBMIT=true
```
⚠️ Používejte opatrně!

## Co když to nefunguje?

1. **Zkontrolujte .env**: Jsou tam všechny klíče?
2. **Aktivujte prostředí**: `source .venv/bin/activate`
3. **Nainstalujte znovu**: `uv sync`
4. **Zkontrolujte logy**: `tail -f logs/processor.log`
5. **Zkuste notebook**: `jupyter notebook` → 05_orchestration.ipynb

## Jste připraveni! 🚀

```bash
# Rychlý checklist:
# ☐ .env soubor vytvořen s API klíči
# ☐ uv sync proběhlo úspěšně
# ☐ Faktury v data/invoices/
# ☐ Spuštěn test: python example_usage.py

# Pokud vše ✓, spusťte:
python process_invoices.py
```

## Další kroky po prvním úspěchu

1. ✅ Zpracovat více faktur
2. ✅ Upravit konfiguraci podle potřeby
3. ✅ Vytvořit vlastní workflow
4. ✅ Automatizovat s cronem (volitelné)
5. ✅ Přidat vlastní pole (volitelné)

---

**Máte dotazy?**
- 📖 Přečtěte `QUICKSTART.md`
- 📚 Prostudujte `docs/setup_guide.md`
- 🇨🇿 České info v `docs/czechREADME.md`
- 💻 Příklady v `example_usage.py`
- 📓 Vyzkoušejte notebooky v `notebooks/`

**Hodně štěstí s prvními fakturami!** 🎯

