# Fakturoid Invoice Processor - Průvodce v češtině

AI agent pro automatické zpracování faktur a jejich odeslání do systému Fakturoid.

## Co toto řešení dělá?

1. **Načte faktury** z adresáře (PDF nebo obrázky JPG/PNG)
2. **Vyčte data pomocí AI** (číslo faktury, dodavatel, částka, atd.)
3. **Zkontroluje správnost** vyčtených dat
4. **Odešle do Fakturoid** přes API (s možností manuálního schválení)

## Požadavky

- Python 3.11 nebo novější
- UV package manager
- Anthropic API klíč (pro AI model Claude)
- Účet na Fakturoid s API přístupem

## Rychlý start

### 1. Instalace UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Instalace závislostí

```bash
cd /Users/pavelzverina/AiProjects/fakturoid

# Vytvoření virtuálního prostředí a instalace balíčků
uv sync

# Aktivace prostředí
source .venv/bin/activate
```

### 3. Konfigurace

Vytvořte soubor `.env`:

```bash
ANTHROPIC_API_KEY=váš_anthropic_klíč
FAKTUROID_EMAIL=vas@email.cz
FAKTUROID_API_KEY=váš_fakturoid_klíč
FAKTUROID_ACCOUNT_SLUG=váš_účet
```

### 4. Použití

```bash
# Umístěte faktury do data/invoices/
# Pak spusťte:
python process_invoices.py
```

## Struktura projektu

```
fakturoid/
├── src/                   # Produkční kód
│   ├── config.py          # Konfigurace
│   ├── document_processor.py  # Načítání dokumentů
│   ├── ai_extractor.py    # AI extrakce dat
│   ├── fakturoid_client.py    # Klient pro Fakturoid API
│   └── agent.py           # Hlavní orchestrace
├── notebooks/             # Jupyter notebooky pro vývoj
│   ├── 01_document_loader.ipynb      # Test načítání
│   ├── 02_data_extraction.ipynb      # Test extrakce
│   ├── 03_validation.ipynb           # Test validace
│   ├── 04_fakturoid_integration.ipynb # Test Fakturoid
│   └── 05_orchestration.ipynb        # Kompletní pipeline
├── data/
│   ├── invoices/          # Vstupní faktury
│   └── processed/         # Archiv zpracovaných
├── config/
│   └── settings.yaml      # Nastavení aplikace
└── docs/
    └── setup_guide.md     # Detailní dokumentace
```

## Režimy zpracování

### Manuální kontrola (doporučeno pro začátek)

```python
from src.agent import InvoiceProcessingAgent

agent = InvoiceProcessingAgent(auto_submit=False)
results = agent.process_batch(review=True)
```

Každá faktura se zobrazí ke kontrole před odesláním.

### Automatický režim

```python
agent = InvoiceProcessingAgent(auto_submit=True)
results = agent.process_batch(review=False)
```

⚠️ Automaticky odešle všechny platné faktury bez kontroly!

## Co agent vyčte z faktury?

### Povinné údaje
- Číslo faktury
- Datum vystavení
- Název dodavatele
- Celková částka

### Volitelné údaje
- Datum splatnosti
- Variabilní symbol
- Adresa dodavatele
- IČO, DIČ
- Položky faktury s cenami
- Částka DPH
- Měna

## Vývoj pomocí notebooků

Projekt obsahuje Jupyter notebooky pro postupný vývoj a testování:

```bash
# Spuštění Jupyter
jupyter notebook

# Otevřete postupně:
# 1. 01_document_loader.ipynb    - test načítání dokumentů
# 2. 02_data_extraction.ipynb    - test AI extrakce
# 3. 03_validation.ipynb         - test validace dat
# 4. 04_fakturoid_integration.ipynb - test Fakturoid API
# 5. 05_orchestration.ipynb      - kompletní proces
```

## Použití z příkazové řádky

```bash
# Základní použití (s manuální kontrolou)
python process_invoices.py

# Automatický režim (bez kontroly)
python process_invoices.py --auto

# Zpracovat max 5 faktur
python process_invoices.py --max 5

# Nápověda
python process_invoices.py --help
```

## Nastavení

Upravte `config/settings.yaml`:

```yaml
# Režim zpracování
processing:
  mode: "manual"  # auto | manual | both
  auto_submit: false
  batch_size: 10

# AI model
ai:
  provider: "anthropic"
  model: "claude-sonnet-4-5-20250929"
  temperature: 0.0

# Povinná pole faktury
extraction:
  required_fields:
    - invoice_number    # Číslo faktury
    - issue_date        # Datum vystavení
    - supplier_name     # Dodavatel
    - total_amount      # Celková částka
```

## Řešení problémů

### Chyba připojení k Fakturoid

```python
from src.fakturoid_client import FakturoidClient
from src.config import config

client = FakturoidClient(
    email=config.fakturoid.email,
    api_key=config.fakturoid.api_key,
    account_slug=config.fakturoid.account_slug
)
print(client.test_connection())
```

### Špatná extrakce dat

- Ujistěte se, že obrázky jsou v dobré kvalitě
- Zkontrolujte API klíč Anthropic
- Zkontrolujte logy v `logs/processor.log`

Podrobný návod k řešení problémů najdete v [`docs/setup_guide.md`](setup_guide.md).

## Získání API klíčů

### Anthropic API klíč

1. Přejděte na [console.anthropic.com](https://console.anthropic.com)
2. Zaregistrujte se nebo se přihlaste
3. V sekci API Keys vytvořte nový klíč
4. Zkopírujte klíč do `.env` souboru

### Fakturoid API klíč

1. Přihlaste se do Fakturoid
2. Přejděte do Nastavení → API
3. Vygenerujte API klíč
4. Zkopírujte:
   - Email
   - API klíč
   - Account slug (subdoména vaší Fakturoid URL)

## Technologie

- **Python 3.11+**: Programovací jazyk
- **UV**: Rychlý správce Python balíčků
- **Anthropic Claude**: AI model pro čtení faktur
- **Fakturoid API**: Systém pro správu faktur
- **MCP**: Model Context Protocol pro komunikaci
- **Jupyter**: Interaktivní vývoj v noteboocích

## Příklad použití

```python
from src.agent import InvoiceProcessingAgent

# Inicializace agenta
agent = InvoiceProcessingAgent()

# Test připojení
if agent.test_connections():
    print("Připojení OK!")
    
    # Zpracování jedné faktury
    from pathlib import Path
    invoice_file = Path("data/invoices/faktura.pdf")
    result = agent.process_file(invoice_file, review=True)
    
    # Nebo dávkové zpracování
    results = agent.process_batch(review=True, max_files=10)
    
    # Výpis výsledků
    for r in results:
        print(f"{r['file']}: {r['status']}")
```

## Workflow vývoje

1. **Umístěte testovací faktury** do `data/invoices/`
2. **Otevřete první notebook** `01_document_loader.ipynb`
3. **Otestujte načítání** dokumentů
4. **Postupujte dalšími notebooky** až po kompletní pipeline
5. **Upravte kód** v `src/` podle potřeby
6. **Spusťte produkční skript** `process_invoices.py`

## Bezpečnost

⚠️ **Důležité:**
- Nikdy necommitujte `.env` soubor do Gitu
- API klíče uchovávejte v bezpečí
- První použití vždy s manuální kontrolou
- Zálohujte si originální faktury

## Podpora

Pro problémy a dotazy:
1. Zkontrolujte [`docs/setup_guide.md`](setup_guide.md)
2. Prohlédněte si příklady v noteboocích
3. Zkontrolujte logy v `logs/processor.log`

## Roadmapa

- [ ] Webové rozhraní pro kontrolu
- [ ] Podpora více formátů faktur
- [ ] Vícejazyčná podpora
- [ ] Pokročilá validační pravidla
- [ ] Integrace s emailem
- [ ] Detekce duplicit
- [ ] Export do dalších systémů

---

**Verze**: 0.1.0  
**Autor**: Pavel Zveřina  
**Poslední aktualizace**: Říjen 2025

