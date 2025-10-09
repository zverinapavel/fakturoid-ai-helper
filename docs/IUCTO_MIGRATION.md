# iÚčto Migrace - Uživatelský průvodce

Průvodce pro jednorázový převod faktur z iÚčto.cz do Fakturoidu (2013-2021).

## 🎯 Co tento nástroj dělá

Jednorázový převod všech historických faktur:
- ✅ **Vystavené faktury** (issued invoices) → Fakturoid invoices
- ✅ **Přijaté faktury** (expenses) → Fakturoid expenses
- ✅ **Automatické označení jako zaplacené** podle dat z iÚčto
- ✅ **Přeskočení duplicit** (pokud faktura už ve Fakturoidu existuje)

## 📋 Prerekvizity

1. ✅ Účet na iÚčto.cz s přístupem k API
2. ✅ Účet na Fakturoid
3. ✅ Hotová instalace Fakturoid Invoice Processor
4. ✅ iÚčto API klíč

---

## 🔑 Získání iÚčto API klíče

1. Přihlaste se do **iÚčto.cz**
2. Přejděte do **Nastavení → API**
3. Vygenerujte nový API klíč
4. Zkopírujte klíč

---

## ⚙️ Nastavení

### 1. Přidejte API klíč do `.env`:

```bash
# Přidejte na konec .env souboru:
IUCTO_API_KEY=your_iucto_api_key_here
```

### 2. Upravte `config/migration_settings.yaml` (volitelné):

```yaml
migration:
  start_year: 2013      # Od kterého roku
  end_year: 2021        # Do kterého roku
  skip_duplicates: true # Přeskočit duplikáty
  auto_mark_paid: true  # Automaticky označit jako zaplacené
  batch_size: 50        # Kolik faktur v dávce
```

---

## 🧪 Testování (DŮLEŽITÉ!)

### Krok 1: Test připojení

```bash
python scripts/migrate_iucto.py --test-connection
```

Ověří, že se můžete připojit k iÚčto i Fakturoidu.

### Krok 2: Dry run na rok 2013

```bash
python scripts/migrate_iucto.py --year 2013 --dry-run
```

Zobrazí co by se stalo, **ale nic nevytvoří**.

### Krok 3: Test na 5 fakturách z 2013

```bash
python scripts/migrate_iucto.py --year 2013 --limit 5 --execute
```

Převede prvních 5 faktur **skutečně**.

### Krok 4: Zkontrolujte ve Fakturoidu

- Přihlaste se do Fakturoidu
- Zkontrolujte vytvořené faktury
- Ověřte že data jsou správně
- Zkontrolujte že jsou označené jako zaplacené

### Krok 5: Celý rok 2013

Pokud je vše OK:

```bash
python scripts/migrate_iucto.py --year 2013 --execute
```

---

## 🚀 Hromadný převod (po testování)

### Všechny roky najednou:

```bash
python scripts/migrate_iucto.py --year-range 2013-2021 --execute
```

### Nebo rok po roku:

```bash
python scripts/migrate_iucto.py --year 2014 --execute
python scripts/migrate_iucto.py --year 2015 --execute
# atd...
```

---

## 📊 Možnosti CLI

### Základní příkazy:

```bash
# Test připojení
python scripts/migrate_iucto.py --test-connection

# Dry run (simulace)
python scripts/migrate_iucto.py --year 2013 --dry-run

# Skutečný převod
python scripts/migrate_iucto.py --year 2013 --execute

# Rozsah let
python scripts/migrate_iucto.py --year-range 2013-2021 --execute
```

### Filtry:

```bash
# Jen vystavené faktury
python scripts/migrate_iucto.py --year 2013 --issued-only --execute

# Jen přijaté faktury
python scripts/migrate_iucto.py --year 2013 --received-only --execute

# Bez označení jako zaplacené
python scripts/migrate_iucto.py --year 2013 --no-mark-paid --execute

# Limit počtu (pro testování)
python scripts/migrate_iucto.py --year 2013 --limit 10 --execute
```

---

## 📓 Jupyter Notebooky

Pro interaktivní testování a kontrolu:

```bash
jupyter notebook
```

### Dostupné notebooky:

1. **`notebooks/iucto_migration/01_iucto_connection.ipynb`**
   - Test připojení k iÚčto
   - Načtení vzorku faktur
   - Zobrazení struktury dat

2. **`notebooks/iucto_migration/02_test_transfer_2013.ipynb`** (TODO)
   - Převod 5-10 testovacích faktur
   - Kontrola mapování dat
   - Manuální ověření

3. **`notebooks/iucto_migration/03_full_migration.ipynb`** (TODO)
   - Převod celého roku
   - Monitoring progress
   - Generování reportu

---

## 📈 Co se děje při migraci

### Pro každou fakturu:

1. **Načtení z iÚčto** → API call
2. **Kontrola duplicity** → Hledá ve Fakturoidu podle čísla
3. **Mapování dat** → iÚčto formát → Fakturoid formát
4. **Vytvoření subjektu** → Pokud ještě neexistuje
5. **Vytvoření faktury** → API call do Fakturoidu
6. **Označení jako zaplacené** → Pokud byla v iÚčto zaplacená

### Označení jako zaplacené:

**Priorita data platby:**
1. `paid_date` (skutečné datum platby z iÚčto)
2. `due_date` (datum splatnosti)
3. `issue_date` (datum vystavení - fallback)

---

## 📄 Reporty

### Po každém běhu se vytvoří:

```
logs/
├── migration.log                    # Detailní log
├── migration_report_2013.json       # Report za rok 2013
├── migration_report_2014.json       # Report za rok 2014
└── migration_report_complete.json   # Souhrnný report
```

### Struktura reportu:

```json
{
  "year": 2013,
  "timestamp": "2025-10-08T15:30:00",
  "issued": {
    "total": 85,
    "transferred": 80,
    "skipped": 5,
    "errors": 0
  },
  "received": {
    "total": 42,
    "transferred": 40,
    "skipped": 2,
    "errors": 0
  }
}
```

---

## ⚠️ Důležité poznámky

### Duplicity

- Systém kontroluje duplicity podle **čísla faktury**
- Pokud faktura s daným číslem už existuje → **přeskočí**
- Neaktualizuje existující faktury

### Subjekty (klienti/dodavatelé)

- Používá stejný systém jako běžná AI extrakce
- Hledá podle IČO/DIČ/VAT/jména
- Pro české firmy používá ARES lookup
- Vytvoří nového subjektu pokud není nalezen

### Platby

- Označí jako "zaplacené" ve Fakturoidu
- Neimportuje bankovní transakce (jen status)
- Používá datum podle strategie v konfiguraci

### Rate Limiting

- Batch processing (default: 50 faktur)
- Pauza mezi batches (default: 2 sekundy)
- Chrání před API rate limity

---

## 🐛 Troubleshooting

### "IUCTO_API_KEY not found"

```bash
# Zkontrolujte .env
cat .env | grep IUCTO

# Přidejte pokud chybí:
echo "IUCTO_API_KEY=your_key" >> .env
```

### "Connection to iÚčto failed"

- Zkontrolujte API klíč je platný
- Zkontrolujte že účet je aktivní
- Zkuste test připojení: `--test-connection`

### "Duplicate subject created"

- Systém se snaží najít existující
- Pokud má firmy mírně odlišné názvy, vytvoří duplicitu
- Můžete je sloučit ve Fakturoidu po migraci

### "Too many API calls" / "Rate limit"

- Zvyšte `delay_between_batches` v konfiguraci
- Snižte `batch_size`
- Migrujte po menších blocích (rok po roku)

---

## ✅ Kontrolní checklist

Po dokončení migrace:

- [ ] Zkontrolujte počty: iÚčto vs Fakturoid
- [ ] Náhodný vzorek 10 faktur - manuální kontrola
- [ ] Zkontrolujte že jsou označeny jako zaplacené
- [ ] Zkontrolujte subjekty (klienti/dodavatelé)
- [ ] Zkontrolujte reporty v `logs/`
- [ ] Archivujte iÚčto data (pokud chcete)

---

## 📞 Podpora

Pokud narazíte na problémy:

1. Zkontrolujte `logs/migration.log`
2. Zkontrolujte `logs/migration_report_*.json`
3. Použijte notebook pro detailní debugging
4. Zkuste menší batch (--limit 5)

---

**Version:** 0.1.0  
**Created:** 2025-10-08  
**Purpose:** One-time migration from iÚčto to Fakturoid

