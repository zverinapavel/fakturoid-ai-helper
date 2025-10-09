# Režimy zpracování faktur

Kompletní průvodce třemi režimy zpracování v `process_invoices.py`.

## 🎯 Přehled režimů

| Režim | Příkaz | Extrakce | Zobrazení | Potvrzení | Odeslání |
|-------|--------|----------|-----------|-----------|----------|
| **Manual** | `--manual` nebo bez flagu | ✅ | ✅ | ✅ Každá faktura | ✅ Jen schválené |
| **Auto** | `--auto` | ✅ | ❌ | ❌ | ✅ Všechny |
| **Extract-only** | `--extract-only` | ✅ | ✅ | ❌ | ❌ Žádné |

---

## 🔍 Režim 1: Manual (výchozí)

**Použití:**
```bash
python process_invoices.py
# nebo explicitně:
python process_invoices.py --manual
```

**Jak funguje:**
1. Zobrazí seznam faktur
2. Zeptá se na potvrzení začátku
3. Pro každou fakturu:
   - Extrahuje data pomocí AI
   - **Zobrazí detaily** (dodavatel, částka, položky)
   - **Zeptá se**: Odeslat? (y/n/q)
   - y = odešle do Fakturoidu
   - n = přeskočí na další
   - q = ukončí zpracování

**Příklad:**
```
============================================================
📄 Faktura 1/3: google-workspace.pdf
============================================================

⏳ Extrahuji data...

============================================================
📄 EXTRAHOVANÁ DATA
============================================================
Číslo faktury: 5369924648
Datum vystavení: 2025-09-30
Datum splatnosti: N/A
Variabilní symbol: N/A

🏢 Dodavatel: Google Cloud EMEA Limited
   VAT: IE3668997OH
   Adresa: Velasco, Clanwilliam Place
          Dublin 2
          Ireland

💰 Celková částka: 8.1 EUR
   DPH: N/A

📋 Položky faktury (2):
   1. Google Workspace
      1 x 6.75 = 6.75
   2. Storage fee
      1 x 1.35 = 1.35
============================================================

❓ Odeslat tuto fakturu do Fakturoidu?
   (y)es / (n)o / (q)uit: y

⏳ Odesílám do Fakturoidu...
✅ Úspěšně odesláno!
   ID: 3468050
   Číslo nákladu: FP20250184
```

**Výhody:**
- ✅ Plná kontrola nad každou fakturou
- ✅ Můžete přeskočit chybné faktury
- ✅ Vidíte všechna data před odesláním
- ✅ Bezpečné pro první použití

---

## ⚡ Režim 2: Auto

**Použití:**
```bash
python process_invoices.py --auto
```

**Jak funguje:**
1. Zobrazí seznam faktur
2. **Varování**: Odešlou se všechny faktury bez kontroly!
3. Zeptá se na potvrzení jednou
4. Zpracuje všechny faktury automaticky
5. Zobrazí souhrn

**Příklad:**
```
============================================================
FAKTUROID INVOICE PROCESSOR
============================================================
Mode: AUTO
...
============================================================

Found 3 invoice file(s):
  1. invoice1.pdf
  2. invoice2.jpg
  3. invoice3.pdf

⚠️  AUTO-SUBMIT MODE - Invoices will be submitted without review!
Continue? (y/n): y

Processing invoices...

============================================================
PROCESSING RESULTS
============================================================

1. ✅ invoice1.pdf
   Status: submitted
   Faktura: INV-001
   Dodavatel: Company A
   Částka: 1000 CZK
   Fakturoid ID: 123
   Číslo nákladu: FP20250185
...
```

**Výhody:**
- ⚡ Rychlé zpracování více faktur
- 🤖 Automatizace rutinních úkolů

**⚠️ Varování:**
- Nevidíte data před odesláním
- Nemůžete opravit chyby
- Doporučeno jen po testování

---

## 📋 Režim 3: Extract-only

**Použití:**
```bash
python process_invoices.py --extract-only
```

**Jak funguje:**
1. Extrahuje data ze všech faktur
2. **Zobrazí** extrahovaná data
3. **NEODEŠLE** do Fakturoidu
4. Faktury zůstávají v `data/invoices/`

**Příklad:**
```
============================================================
FAKTUROID INVOICE PROCESSOR
============================================================
Mode: EXTRACT-ONLY
...
============================================================

📋 EXTRACT-ONLY MODE - Data will be extracted but not submitted
Continue? (y/n): y

Extracting invoice data...

============================================================
PROCESSING RESULTS
============================================================

1. 📋 invoice1.pdf
   Status: extracted
   Faktura: INV-001
   Dodavatel: Company A
   Částka: 1000 CZK
   Položky:
      • Product A
      • Product B

2. 📋 invoice2.pdf
   ...

============================================================
SUMMARY: 3 total | 0 submitted | 0 skipped | 3 extracted | 0 errors
============================================================

📋 3 invoice(s) extracted
   No invoices were submitted (extract-only mode)
```

**Výhody:**
- 🧪 Testování extrakce bez odesílání
- 📊 Kontrola kvality AI extrakce
- 💾 Faktury zůstávají na místě

**Použití:**
- Testování nového AI modelu
- Kontrola přesnosti extrakce
- Debug problémů s extrakcí

---

## 🔧 Další možnosti

### Limit počtu faktur

```bash
# Zpracovat max 5 faktur
python process_invoices.py --manual --max 5
python process_invoices.py --auto --max 10
python process_invoices.py --extract-only --max 3
```

### Vlastní adresář

```bash
python process_invoices.py --manual --invoices-dir /path/to/invoices
```

---

## 📊 Co se zobrazuje v Manual a Extract-only režimu

### Základní info
```
Číslo faktury: 5369924648
Datum vystavení: 2025-09-30
Datum splatnosti: N/A
Variabilní symbol: N/A
```

### Dodavatel
```
🏢 Dodavatel: Google Cloud EMEA Limited
   VAT: IE3668997OH
   Adresa: Velasco, Clanwilliam Place
          Dublin 2
          Ireland
```

### Částky
```
💰 Celková částka: 8.1 EUR
   DPH: 1.35 EUR  (pokud je uvedeno)
```

### Položky faktury
```
📋 Položky faktury (2):
   1. Google Workspace
      1 x 6.75 = 6.75
   2. Storage fee
      1 x 1.35 = 1.35
```

### Poznámky
```
📝 Poznámky: Additional information about the invoice
```

---

## 💡 Kdy použít který režim

### 🔍 Manual → Pro běžné použití
- První použití systému
- Kontrola každé faktury
- Nestandardní faktury
- Chcete mít plnou kontrolu

### ⚡ Auto → Pro hromadné zpracování
- Mnoho standardních faktur
- Již jste systém otestovali
- Důvěřujete AI extrakci
- Chcete rychlé zpracování

### 📋 Extract-only → Pro testování
- Testování AI extrakce
- Kontrola kvality dat
- Chcete vidět co AI extrahuje
- Nechcete nic odesílat

---

## 🎮 Ovládání v Manual režimu

Při zobrazení každé faktury máte 3 možnosti:

| Odpověď | Akce |
|---------|------|
| `y` nebo `yes` | ✅ Odeslat do Fakturoidu |
| `n` nebo `no` | ⏭️ Přeskočit tuto fakturu |
| `q` nebo `quit` | ⏹️ Ukončit celé zpracování |

**Tip:** Stačí napsat jen první písmeno (y/n/q)

---

## 📝 Příklady použití

### Denní workflow (manual)
```bash
# 1. Přidejte nové faktury do data/invoices/
# 2. Spusťte manual režim
python process_invoices.py

# 3. Zkontrolujte každou fakturu
# 4. Potvrďte nebo přeskočte
# 5. Hotovo!
```

### Hromadné zpracování (auto)
```bash
# Jen pro důvěryhodné faktury!
python process_invoices.py --auto --max 20
```

### Test extrakce (extract-only)
```bash
# Otestujte kvalitu AI extrakce
python process_invoices.py --extract-only

# Zkontrolujte výsledky, ale nic se neodešle
```

---

## 🆘 FAQ

**Q: Který režim je výchozí?**  
A: Manual režim (pokud nezadáte žádný flag)

**Q: Můžu zastavit zpracování uprostřed?**  
A: Ano, v manual režimu stiskněte `q` nebo Ctrl+C

**Q: Co když udělám chybu a potvrdím špatnou fakturu?**  
A: Můžete ji smazat ve Fakturoidu nebo označit jako storno

**Q: Mohu upravit extrahovaná data před odesláním?**  
A: Momentálně ne - v plánu pro budoucí verzi. Prozatím použijte notebook pro ruční úpravy.

---

**Last Updated:** 2025-10-08  
**Version:** 0.1.0

