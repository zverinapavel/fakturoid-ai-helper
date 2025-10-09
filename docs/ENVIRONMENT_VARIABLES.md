# Environment Variables Reference

Complete guide to all environment variables used in the Fakturoid Invoice Processor.

## Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | ✅ Yes | - | Anthropic API key for AI extraction |
| `FAKTUROID_CLIENT_ID` | ✅ Yes | - | OAuth 2.0 Client ID |
| `FAKTUROID_CLIENT_SECRET` | ✅ Yes | - | OAuth 2.0 Client Secret |
| `FAKTUROID_ACCOUNT_SLUG` | ✅ Yes | - | Fakturoid account slug |
| `PROCESSING_MODE` | ❌ No | `manual` | Processing mode |
| `AUTO_SUBMIT` | ❌ No | `false` | Auto-submit without review |
| `INVOICES_DIR` | ❌ No | `data/invoices` | Input invoices directory |
| `PROCESSED_DIR` | ❌ No | `data/processed` | Processed invoices archive |
| `LOG_LEVEL` | ❌ No | `INFO` | Logging level |

---

## Required Variables

### 1. ANTHROPIC_API_KEY

**Purpose:** Authentication for Anthropic's Claude AI model used for invoice data extraction.

**Where to get it:** 
- https://console.anthropic.com/settings/keys

**Example:**
```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx...
```

**Used in:**
- `src/config.py` → `Config.anthropic_api_key`
- `src/ai_extractor.py` → `AIInvoiceExtractor.__init__()`

---

### 2. FAKTUROID_CLIENT_ID

**Purpose:** OAuth 2.0 Client ID for Fakturoid API v3 authentication.

**Where to get it:**
- https://app.fakturoid.cz/settings/api

**Example:**
```bash
FAKTUROID_CLIENT_ID=your_client_id_here
```

**Used in:**
- `src/config.py` → `FakturoidConfig.email` (mapped for compatibility)
- `src/fakturoid_client.py` → OAuth token request

**Note:** For backward compatibility, also reads `FAKTUROID_EMAIL`

---

### 3. FAKTUROID_CLIENT_SECRET

**Purpose:** OAuth 2.0 Client Secret for Fakturoid API v3 authentication.

**Where to get it:**
- https://app.fakturoid.cz/settings/api

**Example:**
```bash
FAKTUROID_CLIENT_SECRET=your_secret_here
```

**Used in:**
- `src/config.py` → `FakturoidConfig.api_key` (mapped for compatibility)
- `src/fakturoid_client.py` → OAuth token request

**Note:** For backward compatibility, also reads `FAKTUROID_API_KEY`

---

### 4. FAKTUROID_ACCOUNT_SLUG

**Purpose:** Your Fakturoid account identifier (subdomain).

**Where to get it:**
- From your Fakturoid URL: `https://app.fakturoid.cz/{account_slug}/...`

**Example:**
```bash
FAKTUROID_ACCOUNT_SLUG=mycompany
```

**Used in:**
- `src/config.py` → `FakturoidConfig.account_slug`
- `src/fakturoid_client.py` → API endpoint construction

---

## Optional Variables

### 5. PROCESSING_MODE

**Purpose:** Determines how invoices are processed.

**Options:**
- `manual` (default) - Review each invoice before submission
- `auto` - Automatically process and submit
- `both` - Mixed mode (not fully implemented)

**Example:**
```bash
PROCESSING_MODE=manual
```

**Used in:**
- `src/config.py` → `ProcessingConfig.mode`
- `src/agent.py` → Workflow decisions

---

### 6. AUTO_SUBMIT

**Purpose:** Whether to automatically submit invoices to Fakturoid without manual review.

**Options:**
- `false` (default) - Require manual approval
- `true` - Auto-submit all valid invoices

**Example:**
```bash
AUTO_SUBMIT=false
```

**Used in:**
- `src/config.py` → `ProcessingConfig.auto_submit`
- `src/agent.py` → `InvoiceProcessingAgent.auto_submit`

**⚠️ Warning:** Setting to `true` will automatically submit ALL invoices without review!

---

### 7. LOG_LEVEL

**Purpose:** Controls verbosity of logging output.

**Options:**
- `DEBUG` - Detailed information for debugging
- `INFO` (default) - General informational messages
- `WARNING` - Warning messages only
- `ERROR` - Error messages only

**Example:**
```bash
LOG_LEVEL=INFO
```

**Used in:**
- `src/config.py` → `LoggingConfig.level`
- `src/agent.py` → `logging.basicConfig(level=...)`

---

## Configuration Priority

The system reads configuration in this order (highest to lowest priority):

1. **Environment variables** (`.env` file or system environment)
2. **YAML configuration** (`config/settings.yaml`)
3. **Hard-coded defaults** (in Pydantic models)

### Example:

If you have:
- `.env`: `INVOICES_DIR=/custom/path`
- `config/settings.yaml`: `directories.invoices: data/invoices`
- Default: `data/invoices`

**Result:** `/custom/path` is used (env var wins)

---

## Usage Examples

### Development Setup

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-dev123...
FAKTUROID_CLIENT_ID=dev_client_id
FAKTUROID_CLIENT_SECRET=dev_secret
FAKTUROID_ACCOUNT_SLUG=mycompany-dev
PROCESSING_MODE=manual
AUTO_SUBMIT=false
LOG_LEVEL=DEBUG
```

### Production Setup

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-prod456...
FAKTUROID_CLIENT_ID=prod_client_id
FAKTUROID_CLIENT_SECRET=prod_secret
FAKTUROID_ACCOUNT_SLUG=mycompany
PROCESSING_MODE=auto
AUTO_SUBMIT=true
INVOICES_DIR=/var/invoices
PROCESSED_DIR=/var/processed
LOG_LEVEL=INFO
```

### Minimal Setup (Testing)

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-test...
FAKTUROID_CLIENT_ID=test_id
FAKTUROID_CLIENT_SECRET=test_secret
FAKTUROID_ACCOUNT_SLUG=testaccount
# All other values use defaults
```

---

## Backward Compatibility

For users upgrading from older versions:

| Old Variable | New Variable | Status |
|--------------|--------------|--------|
| `FAKTUROID_EMAIL` | `FAKTUROID_CLIENT_ID` | ✅ Still supported |
| `FAKTUROID_API_KEY` | `FAKTUROID_CLIENT_SECRET` | ✅ Still supported |

Both old and new variable names work. The system checks for the new name first, then falls back to the old name.

---

## Validation

The system validates environment variables on startup:

```python
from src.config import config

# This will raise ValueError if ANTHROPIC_API_KEY is not set
try:
    key = config.anthropic_api_key
except ValueError as e:
    print(f"Error: {e}")
```

**Required variables:**
- If missing, raises `ValueError` immediately

**Optional variables:**
- If missing, uses default values
- No error is raised

---

## Testing Configuration

To test your configuration:

```python
from src.config import config
import json

# Print all configuration
print(json.dumps(config.model_dump(), indent=2, default=str))

# Check specific values
print(f"Invoices dir: {config.directories.invoices}")
print(f"Processed dir: {config.directories.processed}")
print(f"Auto-submit: {config.processing.auto_submit}")
print(f"Log level: {config.logging.level}")
```

Or use the example script:

```bash
python example_usage.py
# Select option 4: Check Configuration
```

---

## Security Best Practices

1. **Never commit `.env` file to git**
   - It's in `.gitignore` by default
   - Use `env.example` as a template

2. **Rotate API keys regularly**
   - Especially for production environments

3. **Use different credentials for dev/prod**
   - Separate Fakturoid accounts or client IDs
   - Different Anthropic API keys

4. **Restrict file permissions**
   ```bash
   chmod 600 .env  # Only owner can read/write
   ```

5. **Use environment-specific .env files**
   ```bash
   .env.development
   .env.production
   .env.test
   ```

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

**Cause:** `.env` file missing or variable not set

**Fix:**
```bash
# Create .env from template
cp env.example .env
# Edit .env and add your API key
```

### Variables not being read

**Cause:** `.env` file in wrong location

**Fix:** Ensure `.env` is in project root:
```
/Users/pavelzverina/AiProjects/fakturoid/
├── .env              ← Here!
├── src/
├── config/
└── ...
```

### Changes to .env not taking effect

**Cause:** Need to restart Python/Jupyter

**Fix:** Restart your Python script or Jupyter kernel

---

**Last Updated:** 2025-10-08  
**Version:** 0.1.0

