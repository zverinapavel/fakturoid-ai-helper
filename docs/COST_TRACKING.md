# 💰 Sledování nákladů na AI

Systém automaticky sleduje použití AI API a vypočítává náklady.

## 📊 Dashboardy poskytovatelů

### Anthropic (Claude)
🔗 **https://console.anthropic.com/settings/usage**
- Sleduje: Celkové náklady, použité tokeny, API klíče
- Billing: https://console.anthropic.com/settings/billing

### OpenAI
🔗 **https://platform.openai.com/usage**
- Sleduje: Náklady podle modelů, denní/měsíční usage
- Billing: https://platform.openai.com/account/billing

### DeepSeek
🔗 **https://platform.deepseek.com/usage**
- Sleduje: Tokeny a náklady

### Groq (ZDARMA)
🔗 **https://console.groq.com/usage**
- Free API s limity na minutu

## 🔍 Vestavěné sledování nákladů

Systém automaticky trackuje každé AI volání:

### Automatický výpis při použití
```python
ai_extractor = AIExtractor(config)
invoice_data = ai_extractor.extract_invoice_data(invoice_file)
```

Výstup:
```
💰 API Usage: 2,847 in + 425 out = $0.0149 (extract_pdf)
✓ AI validation: data looks good
💰 API Usage: 2,963 in + 215 out = $0.0121 (validation)
```

### Zobrazení celkového souhrnu
```python
# Po zpracování faktur
ai_extractor.print_usage_summary()
```

Výstup:
```
============================================================
📊 AI USAGE SUMMARY
============================================================
Provider: anthropic
Model: claude-sonnet-4-5-20250929
Total Requests: 4
Total Input Tokens: 11,230
Total Output Tokens: 1,650
Total Cost: $0.0581 USD
============================================================
```

### Získání stats programaticky
```python
stats = ai_extractor.get_usage_stats()
print(stats)
```

Výstup:
```python
{
    'total_requests': 4,
    'total_input_tokens': 11230,
    'total_output_tokens': 1650,
    'total_cost_usd': 0.0581,
    'requests': [
        {
            'timestamp': '2025-01-15T14:30:45',
            'operation': 'extract_pdf',
            'model': 'claude-sonnet-4-5-20250929',
            'provider': 'anthropic',
            'input_tokens': 2847,
            'output_tokens': 425,
            'cost_usd': 0.0149
        },
        # ... další requesty
    ]
}
```

## 💵 Cenové tabulky (za 1M tokenů)

### Anthropic Claude
| Model | Input | Output |
|-------|-------|--------|
| claude-sonnet-4-5-20250929 | $3.00 | $15.00 |
| claude-3-5-sonnet-20241022 | $3.00 | $15.00 | (Deprecated - bude odstaven 19. února 2026) |
| claude-3-opus-20240229 | $15.00 | $75.00 |

### OpenAI
| Model | Input | Output |
|-------|-------|--------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |

### DeepSeek
| Model | Input | Output |
|-------|-------|--------|
| deepseek-chat | $0.14 | $0.28 |

### Groq & Ollama
| Model | Input | Output |
|-------|-------|--------|
| Groq (llama-3.2-vision) | FREE | FREE |
| Ollama (lokální) | FREE | FREE |

## 📈 Příklad reálných nákladů

### Typická faktura (PDF, 1 stránka)
```
Extrakce: 2,847 in + 425 out = $0.0149
Validace:  2,963 in + 215 out = $0.0121
------------------------------------------
CELKEM:                        $0.0270 (~0.65 Kč)
```

### 100 faktur za měsíc
```
100 × $0.027 = $2.70 (~65 Kč)
```

### 1000 faktur za měsíc
```
1000 × $0.027 = $27.00 (~650 Kč)
```

## 🎯 Optimalizace nákladů

### 1. Výběr modelu
```yaml
# config/settings.yaml

# DRAHÉ ale nejpřesnější
ai:
  provider: "anthropic"
  model: "claude-sonnet-4-5-20250929"  # $3/$15 per 1M tokens

# LEVNĚJŠÍ alternativy
ai:
  provider: "deepseek"
  model: "deepseek-chat"  # $0.14/$0.28 per 1M tokens
  
# ZDARMA (s omezeními)
ai:
  provider: "groq"
  model: "llama-3.2-90b-vision-preview"  # FREE

# LOKÁLNÍ (žádné náklady)
ai:
  provider: "ollama"
  model: "llama3.2-vision"  # FREE, lokální
```

### 2. Vypnutí validace
```python
# Ušetří 50% nákladů (ale nižší přesnost!)
invoice_data = ai_extractor.extract_invoice_data(
    invoice_file,
    validate=False  # Jen 1× AI volání místo 2×
)
```

### 3. Batch zpracování
```python
# Zpracujte více faktur najednou
for invoice_file in invoice_files:
    data = ai_extractor.extract_invoice_data(invoice_file)
    # ...

# Na konci zobrazit celkové náklady
ai_extractor.print_usage_summary()
```

## 📝 Logging do souboru

Pro dlouhodobé sledování můžete logovat:

```python
import json
from datetime import datetime

# Po zpracování faktur
stats = ai_extractor.get_usage_stats()

# Uložit do souboru
log_file = f"logs/ai_usage_{datetime.now():%Y%m%d}.json"
with open(log_file, 'a') as f:
    json.dump(stats, f)
    f.write('\n')
```

## 🔔 Upozornění na limity

### Nastavit cost alert
```python
# Příklad: Varovat když náklady překročí $10
MAX_COST = 10.0

stats = ai_extractor.get_usage_stats()
if stats['total_cost_usd'] > MAX_COST:
    print(f"⚠️  WARNING: Cost exceeded ${MAX_COST}!")
    print(f"   Current cost: ${stats['total_cost_usd']:.2f}")
```

## 📊 Analýza nákladů

### Per-invoice cost
```python
requests = ai_extractor.get_usage_stats()['requests']

for req in requests:
    print(f"{req['timestamp']}: ${req['cost_usd']:.4f} - {req['operation']}")
```

### Denní/měsíční reporting
```python
from collections import defaultdict
import datetime

stats = ai_extractor.get_usage_stats()
daily_costs = defaultdict(float)

for req in stats['requests']:
    date = datetime.datetime.fromisoformat(req['timestamp']).date()
    daily_costs[date] += req['cost_usd']

for date, cost in sorted(daily_costs.items()):
    print(f"{date}: ${cost:.4f}")
```

## 🆘 Troubleshooting

### Tracking nefunguje
- **Anthropic**: Vždy funguje (usage je v response)
- **OpenAI**: Zkontrolujte, že máte `usage` v response
- **Ollama**: Může chybět usage data (tracking zobrazí $0.00)

### Nesprávné ceny
Ceny jsou přibližné a aktuální k lednu 2025. Pro nejnovější ceny:
- Anthropic: https://anthropic.com/pricing
- OpenAI: https://openai.com/pricing
- DeepSeek: https://platform.deepseek.com/pricing

### Aktualizace cen
Upravte v `src/ai_extractor.py`:
```python
MODEL_COSTS = {
    'claude-sonnet-4-5-20250929': {'input': 3.0, 'output': 15.0},
    'claude-3-5-sonnet-20241022': {'input': 3.0, 'output': 15.0},  # Deprecated
    # ... upravte podle aktuálních cen
}
```

## 🎓 Best Practices

### 1. Pro produkci
```python
# ✅ Vždy trackujte náklady
# ✅ Pravidelně kontrolujte dashboardy
# ✅ Nastavte billing alerty
# ✅ Ukládejte usage stats do DB/logs
```

### 2. Pro vývoj
```python
# ✅ Používejte levnější modely (deepseek, groq)
# ✅ Vypněte validaci (validate=False)
# ✅ Testujte na menším počtu faktur
```

### 3. Monitorování
```python
# ✅ Denně kontrolujte usage summary
# ✅ Nastavte cost alerts
# ✅ Analyzujte, které faktury jsou dražší
```

## 💡 Tipy

### Model podle typu faktury
```python
# Jednoduché faktury → levnější model
if invoice_is_simple:
    model = "gpt-4o-mini"  # $0.15/$0.60
else:
    model = "claude-sonnet-4-5-20250929"  # $3/$15
```

### Cache často používaných prompt
- Anthropic podporuje prompt caching
- Ušetří tokeny při opakovaném použití stejného promptu

### Batch API (OpenAI)
- Pro velké množství faktur použijte Batch API
- 50% sleva oproti standard API

