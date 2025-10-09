# iÚčto → Fakturoid Migration Plan

Plán pro **jednorázový převod** všech faktur z iÚčto.cz do Fakturoidu (roky 2013-2021).

## 🎯 Cíl projektu

Převést kompletní účetní historii z iÚčto do Fakturoidu:
- ✅ Faktury vystavené (issued invoices) → Fakturoid invoices
- ✅ Faktury přijaté (received expenses) → Fakturoid expenses
- ✅ Období: 2013-2021
- ✅ Automaticky označit jako zaplacené podle data splatnosti
- ✅ Přeskočit duplicity (pokud už existují ve Fakturoidu)

---

## 📁 Struktura projektu

```
fakturoid/
├── src/                          # Stávající AI extrakce (běžné použití)
│   ├── agent.py
│   ├── ai_extractor.py
│   └── ...
│
├── iucto_migration/              # NOVÉ - jednorázový převod z iÚčto
│   ├── __init__.py
│   ├── iucto_client.py          # iÚčto API client
│   ├── data_mapper.py           # Mapování iÚčto → Fakturoid
│   ├── transfer_agent.py        # Orchestrace převodu
│   └── payment_marker.py        # Označení jako zaplacené
│
├── notebooks/
│   ├── 01-06_...                # Stávající (AI extrakce)
│   └── iucto_migration/         # NOVÉ - testování migrace
│       ├── 01_iucto_connection.ipynb
│       ├── 02_test_transfer_2013.ipynb
│       ├── 03_full_migration.ipynb
│       └── 04_mark_as_paid.ipynb
│
├── scripts/
│   └── migrate_iucto.py         # CLI pro hromadný převod
│
├── config/
│   └── migration_settings.yaml  # Konfigurace migrace
│
└── docs/
    └── iucto-transfer-plan.md   # Tento dokument
```

**Důvod oddělení:**
- AI extrakce (`src/`) = **opakovaná operace** (běžné zpracování nových faktur)
- iÚčto migrace (`iucto_migration/`) = **jednorázová operace** (historická data)

**Název složky:** `iucto_migration` - jasně označuje že jde o migraci z iÚčto

---

## 🔌 iÚčto API - Analýza

### Endpoint dokumentace:
https://iucto.docs.apiary.io/

### Klíčové endpointy:

#### 1. Faktury vystavené (Issued Invoices)
```
GET /api/invoices
GET /api/invoices/{id}
```

**Parametry:**
- `year` - rok (např. 2013)
- `status` - paid/unpaid/all
- Filter podle data

#### 2. Faktury přijaté (Received Invoices/Expenses)
```
GET /api/expenses
GET /api/expenses/{id}
```

**Parametry:**
- `year` - rok
- `status` - paid/unpaid/all

#### 3. Autentizace
- **API Key** v headeru: `X-Api-Key`
- Získáno z nastavení iÚčto účtu

---

## 🗺️ Data Mapping: iÚčto → Fakturoid

### Faktury vystavené (Issued)

| iÚčto pole | Fakturoid pole | Poznámka |
|------------|----------------|----------|
| `number` | `number` | Číslo faktury |
| `issue_date` | `issued_on` | Datum vystavení |
| `due_date` | `due_on` | Datum splatnosti |
| `customer.name` | `subject_name` nebo `subject_id` | Hledat existujícího klienta |
| `customer.ico` | `subject.registration_no` | IČO |
| `customer.dic` | `subject.vat_no` | DIČ |
| `items[]` | `lines[]` | Položky faktury |
| `total` | vypočítá se z lines | Celková částka |
| `paid` | → použít pro payment | Je zaplaceno? |
| `paid_date` | → použít pro payment | Datum zaplacení |

### Faktury přijaté (Received/Expenses)

| iÚčto pole | Fakturoid pole | Poznámka |
|------------|----------------|----------|
| `number` | `original_number` | Číslo faktury dodavatele |
| `issue_date` | `issued_on` | Datum vystavení |
| `due_date` | `due_on` | Datum splatnosti |
| `received_date` | `received_on` | Datum přijetí |
| `supplier.name` | `subject_name` nebo `subject_id` | Hledat existujícího dodavatele |
| `supplier.ico` | `subject.registration_no` | IČO |
| `supplier.dic` | `subject.vat_no` | DIČ |
| `items[]` | `lines[]` | Položky |
| `paid` | → použít pro payment | Je zaplaceno? |
| `paid_date` | → použít pro payment | Datum zaplacení |

---

## 📝 Implementační kroky

### Fáze 1: Příprava (Notebooky)

#### `migration/01_iucto_connection.ipynb`
- Připojení k iÚčto API
- Test autentizace
- Načtení seznamu faktur z roku 2013
- Zobrazení struktury dat

#### `migration/02_test_transfer_2013.ipynb`
- Výběr 5-10 testovacích faktur z roku 2013
- Mapování dat iÚčto → Fakturoid
- Test vytvoření ve Fakturoidu
- Kontrola výsledků
- Test označení jako zaplacené

### Fáze 2: Core moduly

#### `migration/iucto_client.py`
```python
class IUctoClient:
    """Client pro iÚčto API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://app.iucto.cz/api"
    
    def get_issued_invoices(self, year: int) -> List[Dict]:
        """Načte vystavené faktury za rok."""
        pass
    
    def get_received_invoices(self, year: int) -> List[Dict]:
        """Načte přijaté faktury za rok."""
        pass
    
    def get_invoice_detail(self, invoice_id: int) -> Dict:
        """Načte detail faktury."""
        pass
```

#### `migration/data_mapper.py`
```python
class IUctoToFakturoidMapper:
    """Mapuje data z iÚčto na Fakturoid formát."""
    
    def map_issued_invoice(self, iucto_invoice: Dict) -> Dict:
        """Převede vystavenou fakturu."""
        pass
    
    def map_received_invoice(self, iucto_expense: Dict) -> Dict:
        """Převede přijatou fakturu."""
        pass
    
    def find_or_create_subject(self, iucto_entity: Dict) -> int:
        """Najde nebo vytvoří subjekt (klient/dodavatel)."""
        pass
```

#### `migration/transfer_agent.py`
```python
class TransferAgent:
    """Orchestruje celý převod."""
    
    def __init__(self, iucto_client, fakturoid_client):
        self.iucto = iucto_client
        self.fakturoid = fakturoid_client
    
    def transfer_year(self, year: int, dry_run: bool = True):
        """Převede faktury za rok."""
        pass
    
    def check_duplicates(self, invoice_number: str) -> bool:
        """Zkontroluje existenci faktury."""
        pass
```

#### `migration/payment_marker.py`
```python
class PaymentMarker:
    """Označuje faktury jako zaplacené."""
    
    def mark_invoice_paid(self, invoice_id: int, payment_date: str):
        """Označí fakturu jako zaplacenou."""
        pass
    
    def auto_mark_paid(self, invoice_data: Dict):
        """Automaticky označí podle due_date nebo issue_date."""
        pass
```

### Fáze 3: Testování (rok 2013)

#### `migration/03_full_migration.ipynb`
- Načtení všech faktur 2013
- Kontrola duplicit
- Převod do Fakturoidu (s potvrzením)
- Označení jako zaplacené
- Statistiky a report

### Fáze 4: Hromadný převod (2013-2021)

#### `scripts/migrate_iucto.py` - CLI skript
```bash
python scripts/migrate_iucto.py --year 2013 --dry-run
python scripts/migrate_iucto.py --year 2013 --execute
python scripts/migrate_iucto.py --year-range 2013-2021 --execute
```

---

## 🔄 Workflow migrace

### 1. Příprava
```
1. Získat iÚčto API klíč
2. Nastavit v .env: IUCTO_API_KEY=...
3. Otestovat připojení (notebook 01)
```

### 2. Testovací převod (2013, malý vzorek)
```
1. Načíst 5 faktur z 2013
2. Zobrazit data z iÚčto
3. Ukázat jak budou vypadat ve Fakturoidu
4. Manuálně potvrdit převod
5. Zkontrolovat ve Fakturoidu
```

### 3. Celý rok 2013
```
1. Načíst všechny faktury 2013
2. Filtrovat duplicity
3. Převést do Fakturoidu
4. Označit jako zaplacené
5. Generovat report:
   - Kolik převedeno
   - Kolik přeskočeno (duplicity)
   - Kolik chyb
```

### 4. Roky 2014-2021
```
1. Opakovat pro každý rok
2. S automatickým přeskakováním duplicit
3. S progress barem
4. S detailním logováním
```

---

## 📊 Kontrola duplicit

### Strategie detekce:

**Pro vystavené faktury:**
1. Hledat podle `number` (číslo faktury)
2. Hledat podle `variable_symbol`
3. Kombinace číslo + klient + částka

**Pro přijaté faktury:**
1. Hledat podle `original_number`
2. Hledat podle dodavatel + částka + datum

---

## ✅ Označení jako zaplacené

### Logika:

```python
if invoice.paid and invoice.paid_date:
    # Označit jako zaplacené k datu paid_date
    payment_date = invoice.paid_date
    
elif invoice.paid and not invoice.paid_date:
    # Označit jako zaplacené k datu splatnosti
    payment_date = invoice.due_date or invoice.issue_date
    
else:
    # Nechat jako nezaplacené
    payment_date = None
```

### Fakturoid API pro platby:

```
POST /api/v3/accounts/{slug}/invoices/{id}/fire.json?event=pay
POST /api/v3/accounts/{slug}/expenses/{id}/fire.json?event=pay

Body:
{
  "paid_on": "2013-12-31",
  "paid_amount": 1000.00
}
```

---

## 🧪 Testovací strategie

### Test 1: Připojení
- ✅ iÚčto API funguje
- ✅ Fakturoid API funguje
- ✅ Načtení seznamu faktur

### Test 2: Malý vzorek (5 faktur z 2013)
- ✅ Mapování dat funguje správně
- ✅ Subjekty se vytváří/hledají
- ✅ Faktury se vytváří ve Fakturoidu
- ✅ Platby se označují správně

### Test 3: Celý rok 2013 (reálný test)
- ✅ Zpracování všech faktur
- ✅ Handling chyb
- ✅ Duplicity se přeskakují
- ✅ Report je správný

### Test 4: Jeden rok navíc (2014)
- ✅ Ověření že proces funguje i pro další roky
- ✅ Žádné duplicity z 2013

---

## 📋 Konfigurace migrace

### `config/migration_settings.yaml`

```yaml
iucto:
  base_url: "https://app.iucto.cz/api"
  timeout: 30

migration:
  # Roky k převodu
  start_year: 2013
  end_year: 2021
  
  # Typy dokumentů
  transfer_issued: true      # Vystavené faktury
  transfer_received: true    # Přijaté faktury
  
  # Zpracování plateb
  auto_mark_paid: true
  payment_date_strategy: "due_date"  # due_date, paid_date, issue_date
  
  # Duplicity
  skip_duplicates: true
  duplicate_detection:
    - number
    - variable_symbol
    - amount_and_date
  
  # Dávkování
  batch_size: 50
  delay_between_batches: 2  # sekundy (rate limiting)

# Logování migrace
logging:
  migration_log: "logs/migration.log"
  report_file: "logs/migration_report.json"
```

### `.env` - přidat:

```bash
# iÚčto API Key
IUCTO_API_KEY=your_iucto_api_key_here
```

---

## 🔧 Implementace - Core Moduly

### 1. `iucto_migration/iucto_client.py`

```python
import requests
from typing import List, Dict, Optional
from datetime import datetime

class IUctoClient:
    """Client pro komunikaci s iÚčto API."""
    
    def __init__(self, api_key: str, base_url: str = "https://app.iucto.cz/api"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """Test API připojení."""
        try:
            response = self.session.get(f"{self.base_url}/account")
            return response.status_code == 200
        except:
            return False
    
    def get_issued_invoices(
        self, 
        year: int,
        status: str = "all"  # all, paid, unpaid
    ) -> List[Dict]:
        """Načte vystavené faktury za rok."""
        url = f"{self.base_url}/invoices"
        params = {
            'year': year,
            'status': status
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_received_invoices(
        self, 
        year: int,
        status: str = "all"
    ) -> List[Dict]:
        """Načte přijaté faktury za rok."""
        url = f"{self.base_url}/expenses"
        params = {
            'year': year,
            'status': status
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_invoice_detail(self, invoice_id: int) -> Dict:
        """Načte detailní informace o faktuře."""
        url = f"{self.base_url}/invoices/{invoice_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
```

### 2. `iucto_migration/data_mapper.py`

```python
from typing import Dict, List
from datetime import datetime

class IUctoToFakturoidMapper:
    """Mapuje data z iÚčto formátu na Fakturoid formát."""
    
    def __init__(self, fakturoid_client):
        self.fakturoid = fakturoid_client
    
    def map_issued_invoice(self, iucto_invoice: Dict) -> Dict:
        """Převede vystavenou fakturu z iÚčto na Fakturoid formát.
        
        iÚčto struktura:
        {
          "id": 123,
          "number": "2013001",
          "issue_date": "2013-01-15",
          "due_date": "2013-01-29",
          "variable_symbol": "2013001",
          "customer": {
            "name": "Firma s.r.o.",
            "ico": "12345678",
            "dic": "CZ12345678"
          },
          "items": [
            {
              "name": "Služba",
              "quantity": 1,
              "unit_price": 1000,
              "vat_rate": 21
            }
          ],
          "total": 1210,
          "paid": true,
          "paid_date": "2013-01-20"
        }
        """
        
        # Najít nebo vytvořit klienta
        subject_id = self._get_or_create_subject(
            iucto_invoice['customer'],
            is_supplier=False
        )
        
        # Mapovat položky
        lines = []
        for item in iucto_invoice.get('items', []):
            lines.append({
                'name': item['name'],
                'quantity': str(item['quantity']),
                'unit_price': str(item['unit_price']),
                'vat_rate': item.get('vat_rate', 21)
            })
        
        # Sestavit Fakturoid fakturu
        fakturoid_invoice = {
            'subject_id': subject_id,
            'number': iucto_invoice['number'],
            'variable_symbol': iucto_invoice.get('variable_symbol'),
            'issued_on': iucto_invoice['issue_date'],
            'due_on': iucto_invoice.get('due_date'),
            'lines': lines
        }
        
        return fakturoid_invoice, iucto_invoice.get('paid'), iucto_invoice.get('paid_date')
    
    def map_received_invoice(self, iucto_expense: Dict) -> Dict:
        """Převede přijatou fakturu z iÚčto na Fakturoid expense formát."""
        
        # Najít nebo vytvořit dodavatele
        subject_id = self._get_or_create_subject(
            iucto_expense['supplier'],
            is_supplier=True
        )
        
        # Mapovat položky
        lines = []
        for item in iucto_expense.get('items', []):
            lines.append({
                'name': item['name'],
                'quantity': str(item['quantity']),
                'unit_price': str(item['unit_price']),
                'vat_rate': item.get('vat_rate', 21)
            })
        
        # Sestavit Fakturoid expense
        fakturoid_expense = {
            'subject_id': subject_id,
            'original_number': iucto_expense['number'],
            'variable_symbol': iucto_expense.get('variable_symbol'),
            'issued_on': iucto_expense['issue_date'],
            'due_on': iucto_expense.get('due_date'),
            'received_on': iucto_expense.get('received_date') or iucto_expense['issue_date'],
            'taxable_fulfillment_due': iucto_expense.get('taxable_fulfillment_due') or iucto_expense['issue_date'],
            'lines': lines,
            'document_type': 'invoice'
        }
        
        return fakturoid_expense, iucto_expense.get('paid'), iucto_expense.get('paid_date')
    
    def _get_or_create_subject(self, entity: Dict, is_supplier: bool) -> int:
        """Najde nebo vytvoří subjekt (využívá stávající FakturoidClient)."""
        # Použije existující get_or_create_subject z fakturoid_client.py
        pass
```

### 3. `iucto_migration/transfer_agent.py`

```python
class TransferAgent:
    """Orchestruje převod z iÚčto do Fakturoidu."""
    
    def __init__(self, iucto_client, fakturoid_client, config):
        self.iucto = iucto_client
        self.fakturoid = fakturoid_client
        self.config = config
        self.mapper = IUctoToFakturoidMapper(fakturoid_client)
    
    def transfer_year(
        self, 
        year: int,
        dry_run: bool = True,
        transfer_issued: bool = True,
        transfer_received: bool = True
    ) -> Dict:
        """Převede faktury za rok.
        
        Returns:
            Report s statistikami
        """
        report = {
            'year': year,
            'issued': {'total': 0, 'transferred': 0, 'skipped': 0, 'errors': 0},
            'received': {'total': 0, 'transferred': 0, 'skipped': 0, 'errors': 0},
            'details': []
        }
        
        # Převod vystavených faktur
        if transfer_issued:
            issued = self.iucto.get_issued_invoices(year)
            report['issued']['total'] = len(issued)
            
            for invoice in issued:
                result = self._transfer_issued_invoice(invoice, dry_run)
                report['details'].append(result)
                
                if result['status'] == 'transferred':
                    report['issued']['transferred'] += 1
                elif result['status'] == 'skipped':
                    report['issued']['skipped'] += 1
                else:
                    report['issued']['errors'] += 1
        
        # Převod přijatých faktur
        if transfer_received:
            received = self.iucto.get_received_invoices(year)
            report['received']['total'] = len(received)
            
            for expense in received:
                result = self._transfer_received_invoice(expense, dry_run)
                report['details'].append(result)
                
                if result['status'] == 'transferred':
                    report['received']['transferred'] += 1
                elif result['status'] == 'skipped':
                    report['received']['skipped'] += 1
                else:
                    report['received']['errors'] += 1
        
        return report
    
    def _transfer_issued_invoice(self, iucto_invoice: Dict, dry_run: bool) -> Dict:
        """Převede jednu vystavenou fakturu."""
        try:
            # Kontrola duplicity
            if self._is_duplicate_issued(iucto_invoice):
                return {
                    'type': 'issued',
                    'number': iucto_invoice['number'],
                    'status': 'skipped',
                    'reason': 'duplicate'
                }
            
            # Mapování dat
            fakturoid_data, is_paid, paid_date = self.mapper.map_issued_invoice(iucto_invoice)
            
            if dry_run:
                return {
                    'type': 'issued',
                    'number': iucto_invoice['number'],
                    'status': 'dry_run',
                    'data': fakturoid_data
                }
            
            # Vytvoření ve Fakturoidu
            created = self.fakturoid.create_invoice(fakturoid_data)
            
            # Označení jako zaplacené
            if is_paid:
                payment_date = paid_date or iucto_invoice.get('due_date') or iucto_invoice['issue_date']
                self._mark_invoice_paid(created['id'], payment_date)
            
            return {
                'type': 'issued',
                'number': iucto_invoice['number'],
                'status': 'transferred',
                'fakturoid_id': created['id'],
                'fakturoid_number': created['number'],
                'paid': is_paid
            }
            
        except Exception as e:
            return {
                'type': 'issued',
                'number': iucto_invoice.get('number', 'N/A'),
                'status': 'error',
                'error': str(e)
            }
    
    def _is_duplicate_issued(self, iucto_invoice: Dict) -> bool:
        """Zkontroluje jestli faktura už existuje ve Fakturoidu."""
        # Načíst faktury z Fakturoidu a hledat shodu
        pass
    
    def _mark_invoice_paid(self, invoice_id: int, payment_date: str):
        """Označí fakturu jako zaplacenou."""
        pass
```

---

## 📈 Progress Tracking

### Migration Report Structure:

```json
{
  "migration_date": "2025-10-08",
  "years": [2013, 2014, ..., 2021],
  "summary": {
    "total_invoices": 850,
    "total_expenses": 420,
    "transferred": 1200,
    "skipped": 50,
    "errors": 20
  },
  "by_year": {
    "2013": {
      "issued": {"total": 85, "transferred": 80, "skipped": 5, "errors": 0},
      "received": {"total": 42, "transferred": 40, "skipped": 2, "errors": 0}
    },
    ...
  }
}
```

---

## ⚠️ Rizika a mitigace

| Riziko | Pravděpodobnost | Dopad | Mitigace |
|--------|-----------------|-------|----------|
| API rate limiting | Střední | Střední | Batch processing + delays |
| Duplicitní faktury | Vysoká | Nízký | Kontrola před vytvořením |
| Chybějící subjekty | Střední | Střední | Auto-create s ARES lookup |
| Nevalidní data | Nízká | Vysoký | Validace před odesláním |
| API změny | Nízká | Vysoký | Testování na malém vzorku |

---

## 📝 CLI Skript - Usage

```bash
# Dry run - zobrazí co by se stalo
python scripts/migrate_iucto.py --year 2013 --dry-run

# Test na 5 fakturách
python scripts/migrate_iucto.py --year 2013 --limit 5

# Převod celého roku 2013
python scripts/migrate_iucto.py --year 2013 --execute

# Převod všech let 2013-2021
python scripts/migrate_iucto.py --year-range 2013-2021 --execute

# Jen vystavené faktury
python scripts/migrate_iucto.py --year 2013 --issued-only

# Jen přijaté faktury
python scripts/migrate_iucto.py --year 2013 --received-only

# Bez automatického označování jako zaplacené
python scripts/migrate_iucto.py --year 2013 --no-mark-paid
```

---

## 🎯 Milestones

### Week 1: Příprava a testování
- [ ] Získat iÚčto API klíč
- [ ] Vytvořit `migration/` strukturu
- [ ] Implementovat `IUctoClient`
- [ ] Notebook 01: Test připojení
- [ ] Načíst 5 testovacích faktur

### Week 2: Mapování a test převod
- [ ] Implementovat `DataMapper`
- [ ] Notebook 02: Test převodu 5 faktur
- [ ] Kontrola ve Fakturoidu
- [ ] Opravy a ladění

### Week 3: Celý rok 2013
- [ ] Implementovat `TransferAgent`
- [ ] Notebook 03: Převod všech faktur 2013
- [ ] Označení jako zaplacené
- [ ] Generování reportu

### Week 4: Hromadný převod
- [ ] CLI skript `migrate_iucto.py`
- [ ] Progress bar a logging
- [ ] Převod 2014-2021
- [ ] Finální report

---

## ✅ Success Criteria

1. ✅ Všechny faktury 2013-2021 převedeny
2. ✅ Žádné duplicity vytvořeny
3. ✅ Zaplacené faktury správně označeny
4. ✅ < 1% chybovost
5. ✅ Detailní report vygenerován
6. ✅ Kontrolní test: shodují se součty v iÚčto a Fakturoidu

---

## 🔍 Kontrolní checklist

Po dokončení migrace:

- [ ] Počet faktur v iÚčto == počet ve Fakturoidu (minus duplicity)
- [ ] Náhodný vzorek 10 faktur - manuální kontrola
- [ ] Kontrola plateb - zaplacené faktury mají payment
- [ ] Kontrola subjektů - všichni klienti/dodavatelé existují
- [ ] Report uložen a zkontrolován
- [ ] Backup iÚčto dat před archivací

---

**Poznámka:** Tento plán předpokládá že:
1. iÚčto API je dostupné a funkční
2. Máte platný API klíč
3. Data v iÚčto jsou validní
4. Fakturoid účet má dostatečný limit pro počet faktur

**Odhadovaná doba:** 3-4 týdny (včetně testování)

**Odhadovaný počet API calls:** ~5000-10000 (závisí na počtu faktur)

---

**Created:** 2025-10-08  
**Status:** Planning  
**Target:** Migration complete by 2025-11-08

