# Configuration Priority

Jak funguje priorita konfigurace v projektu Fakturoid Invoice Processor.

## 🎯 Pravidlo priority

Systém načítá konfiguraci v tomto pořadí (od nejvyšší k nejnižší prioritě):

```
1. Environment Variables (.env)    ← Nejvyšší priorita
2. YAML Configuration (settings.yaml)
3. Hard-coded Defaults              ← Nejnižší priorita
```

**Pravidlo:** První nalezená hodnota se použije.

---

## 📁 Directories (invoices, processed)

### Priorita:

1. **YAML config** (`directories.invoices`, `directories.processed`)
2. **Default** (`data/invoices`, `data/processed`)

**Note:** Directories are NOT configurable via .env (only via YAML) to avoid confusion.

### Příklad:

**Scenario 1: Použít defaults**
```yaml
# config/settings.yaml - prázdné nebo výchozí hodnoty
directories:
  invoices: "data/invoices"
  processed: "data/processed"
```
→ Použije se: `/path/to/project/data/invoices`

**Scenario 2: Custom YAML cesty**
```yaml
# config/settings.yaml
directories:
  invoices: "monthly_invoices"
  processed: "archive/processed"
```
→ Použije se: `/path/to/project/monthly_invoices`

**Scenario 3: Absolutní cesty v YAML**
```yaml
# config/settings.yaml
directories:
  invoices: "/absolute/path/to/invoices"
  processed: "/absolute/path/to/processed"
```
→ Použije se: `/absolute/path/to/invoices`

---

## 🤖 AI Configuration

### Provider a Model:

1. **Environment variables** (`AI_PROVIDER`, `AI_MODEL`)
2. **YAML config** (`ai.provider`, `ai.model`)
3. **Defaults** (`anthropic`, `claude-sonnet-4-5-20250929`)

### API Keys:

**Vždy z environment variables:**
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `GROQ_API_KEY`

API klíče **se nikdy neukládají** do YAML (bezpečnost!).

### Příklad:

```yaml
# settings.yaml
ai:
  provider: "anthropic"
  model: "claude-sonnet-4-5-20250929"
```

```bash
# .env
AI_PROVIDER=deepseek        # ← Přepíše YAML
AI_MODEL=deepseek-chat      # ← Přepíše YAML
DEEPSEEK_API_KEY=sk-...
```

→ Použije se: DeepSeek (z .env, ignoruje YAML)

---

## ⚙️ Processing Configuration

### Mode a Auto-submit:

1. **Environment variables** (`PROCESSING_MODE`, `AUTO_SUBMIT`)
2. **YAML config** (`processing.mode`, `processing.auto_submit`)
3. **Defaults** (`manual`, `false`)

### Příklad:

```yaml
# settings.yaml
processing:
  mode: "manual"
  auto_submit: false
```

```bash
# .env
PROCESSING_MODE=auto     # ← Přepíše YAML
AUTO_SUBMIT=true         # ← Přepíše YAML
```

→ Použije se: auto mode s auto-submit (z .env)

---

## 📝 Logging

### Log Level:

1. **Environment variable** (`LOG_LEVEL`)
2. **YAML config** (`logging.level`)
3. **Default** (`INFO`)

### Příklad:

```yaml
# settings.yaml
logging:
  level: "INFO"
```

```bash
# .env
LOG_LEVEL=DEBUG    # ← Přepíše YAML
```

→ Použije se: DEBUG level

---

## 🔐 Fakturoid Credentials

### API Credentials:

**Vždy z environment variables:**
- `FAKTUROID_CLIENT_ID` (nebo `FAKTUROID_EMAIL`)
- `FAKTUROID_CLIENT_SECRET` (nebo `FAKTUROID_API_KEY`)
- `FAKTUROID_ACCOUNT_SLUG`

Credentials **se nikdy neukládají** do YAML!

### API endpoint:

```yaml
# settings.yaml
fakturoid:
  base_url: "https://app.fakturoid.cz/api/v3"
  timeout: 30
```

URL a timeout lze nastavit v YAML.

---

## 📊 Complete Priority Table

| Konfigurace | .env | YAML | Default | Notes |
|-------------|------|------|---------|-------|
| **Directories** | | | | |
| invoices | - | `directories.invoices` | `data/invoices` | Pouze YAML, převede se na absolutní |
| processed | - | `directories.processed` | `data/processed` | Pouze YAML, převede se na absolutní |
| **AI** | | | | |
| provider | `AI_PROVIDER` | `ai.provider` | `anthropic` | |
| model | `AI_MODEL` | `ai.model` | `claude-sonnet-4-5-20250929` | |
| **API Keys** | | | | |
| Anthropic | `ANTHROPIC_API_KEY` | - | - | Required for Anthropic |
| OpenAI | `OPENAI_API_KEY` | - | - | Required for OpenAI |
| DeepSeek | `DEEPSEEK_API_KEY` | - | - | Required for DeepSeek |
| Groq | `GROQ_API_KEY` | - | - | Required for Groq |
| Ollama URL | `OLLAMA_BASE_URL` | `ai.ollama_base_url` | `http://localhost:11434` | |
| **Processing** | | | | |
| mode | `PROCESSING_MODE` | `processing.mode` | `manual` | |
| auto_submit | `AUTO_SUBMIT` | `processing.auto_submit` | `false` | |
| **Fakturoid** | | | | |
| client_id | `FAKTUROID_CLIENT_ID` | - | - | Required |
| client_secret | `FAKTUROID_CLIENT_SECRET` | - | - | Required |
| account_slug | `FAKTUROID_ACCOUNT_SLUG` | - | - | Required |
| **Logging** | | | | |
| level | `LOG_LEVEL` | `logging.level` | `INFO` | |

---

## 💡 Best Practices

### Development Setup

**Use `.env` for secrets:**
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-dev...
FAKTUROID_CLIENT_ID=dev_id
FAKTUROID_CLIENT_SECRET=dev_secret
FAKTUROID_ACCOUNT_SLUG=dev-account
```

**Use YAML for preferences:**
```yaml
# settings.yaml
ai:
  provider: "anthropic"
  model: "claude-3-haiku-20240307"  # Cheaper for dev

processing:
  mode: "manual"
  
logging:
  level: "DEBUG"  # Verbose logging for dev
```

### Production Setup

**Use `.env` for all critical settings:**
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-prod...
FAKTUROID_CLIENT_ID=prod_id
FAKTUROID_CLIENT_SECRET=prod_secret
FAKTUROID_ACCOUNT_SLUG=prod-account

# Override YAML settings
AI_PROVIDER=anthropic
AI_MODEL=claude-sonnet-4-5-20250929
PROCESSING_MODE=auto
AUTO_SUBMIT=true
INVOICES_DIR=/production/invoices
PROCESSED_DIR=/production/processed
LOG_LEVEL=INFO
```

**Keep YAML minimal:**
```yaml
# settings.yaml - just structure, no sensitive data
processing:
  batch_size: 10

extraction:
  required_fields:
    - invoice_number
    - issue_date
    - supplier_name
    - total_amount
```

---

## 🧪 Testing Configuration

```python
from src.config import config
import json

# Display all configuration
print(json.dumps(config.model_dump(), indent=2, default=str))

# Check specific values
print(f"\nInvoices: {config.directories.invoices}")
print(f"Provider: {config.ai.provider}")
print(f"Model: {config.ai.model}")
print(f"Mode: {config.processing.mode}")
```

---

## 🔄 Changing Configuration

### Temporary Override (Runtime)

```python
from src.config import config

# Override for this session
config.ai.provider = "openai"
config.ai.model = "gpt-4o-mini"

# Use modified config
agent = InvoiceProcessingAgent(config)
```

### Permanent Change

**Option 1: Edit .env** (doporučeno)
```bash
nano .env
# Změňte AI_PROVIDER=deepseek
```

**Option 2: Edit YAML**
```bash
nano config/settings.yaml
# Změňte ai.provider: "deepseek"
```

**Option 3: Environment variable** (dočasné)
```bash
AI_PROVIDER=groq python process_invoices.py --extract-only
```

---

## 🆘 Troubleshooting

### "Config value not used"

**Příčina:** .env má přednost před YAML

**Řešení:** Zkontrolujte .env:
```bash
cat .env | grep INVOICES_DIR
# Pokud je nastaveno, přepíše YAML
```

### "Path not found"

**Příčina:** Relativní cesta v YAML je relativní k PROJECT_ROOT

**Řešení:**
```yaml
# Špatně (od cwd):
directories:
  invoices: "../other_project/invoices"

# Správně (od project root):
directories:
  invoices: "data/invoices"

# Nebo absolutně:
directories:
  invoices: "/absolute/path/invoices"
```

### "API key not found"

**Příčina:** API klíče nejdou z YAML, jen z .env

**Řešení:** Přidejte do .env:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

---

**Last Updated:** 2025-10-08  
**Version:** 0.1.0

