# iÚčto Migration Tools

Nástroje pro jednorázový převod faktur z iÚčto.cz do Fakturoidu.

## 📁 Soubory v této složce

- **`iucto_client.py`** - Client pro iÚčto API
- **`data_mapper.py`** - Převod iÚčto → Fakturoid formát
- **`transfer_agent.py`** - Orchestrace převodu
- **`README.md`** - Tento soubor

## 🎯 Účel

Tato složka obsahuje kód pro **jednorázový převod** historických dat z iÚčto:
- Roky 2013-2021
- Vystavené i přijaté faktury
- S automatickým označením jako zaplacené

**⚠️ Poznámka:** Toto NENÍ pro běžné použití. Pro běžné zpracování nových faktur použijte `src/` moduly.

## 📚 Použití

### CLI skript:

```bash
# Test připojení
python scripts/migrate_iucto.py --test-connection

# Dry run (test bez vytváření)
python scripts/migrate_iucto.py --year 2013 --dry-run

# Skutečný převod
python scripts/migrate_iucto.py --year 2013 --execute

# Všechny roky
python scripts/migrate_iucto.py --year-range 2013-2021 --execute
```

### V Pythonu:

```python
from iucto_migration.iucto_client import IUctoClient
from iucto_migration.transfer_agent import TransferAgent
from src.fakturoid_client import FakturoidClient
from src.config import config

# Initialize
iucto = IUctoClient(api_key="your_key")
fakturoid = FakturoidClient(config)

# Create agent
agent = TransferAgent(iucto, fakturoid, config={'skip_duplicates': True})

# Transfer year
report = agent.transfer_year(2013, dry_run=True)
print(agent.generate_report(report))
```

### V Jupyter Notebooku:

```bash
jupyter notebook notebooks/iucto_migration/01_iucto_connection.ipynb
```

## 📖 Dokumentace

- **Detailní plán**: `docs/iucto-transfer-plan.md`
- **Uživatelský průvodce**: `docs/IUCTO_MIGRATION.md`
- **Konfigurace**: `config/migration_settings.yaml`

## ⚙️ Konfigurace

Upravte `config/migration_settings.yaml`:

```yaml
migration:
  start_year: 2013
  end_year: 2021
  skip_duplicates: true
  auto_mark_paid: true
  batch_size: 50
```

## 🔐 Credentials

Přidejte do `.env`:

```bash
IUCTO_API_KEY=your_iucto_api_key_here
```

---

**Vytvořeno:** 2025-10-08  
**Účel:** One-time migration from iÚčto to Fakturoid  
**Status:** Ready for testing

