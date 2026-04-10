# AI Providers Guide

Průvodce pro používání různých AI modelů pro extrakci dat z faktur.

## 🤖 Podporované providery

| Provider | PDF podpora | Image podpora | Cena | Rychlost | Kvalita |
|----------|------------|---------------|------|----------|---------|
| **Anthropic Claude** | ✅ Ano | ✅ Ano | $$ | 🟡 Střední | ⭐⭐⭐⭐⭐ |
| **OpenAI GPT-4** | ❌ Ne* | ✅ Ano | $$$ | 🟡 Střední | ⭐⭐⭐⭐ |
| **DeepSeek** | ❌ Ne* | ✅ Ano | $ | 🟢 Rychlá | ⭐⭐⭐⭐ |
| **Groq** | ❌ Ne* | ✅ Ano | 🆓 Free** | 🟢 Velmi rychlá | ⭐⭐⭐ |
| **Ollama** | ❌ Ne* | ✅ Ano | 🆓 Free | 🔴 Pomalá | ⭐⭐ |

\* Nepodporují PDF přímo - potřeba převod na obrázky  
\*\* Groq má free tier s rate limity

---

## 🔧 Nastavení

### 1. Config YAML (`config/settings.yaml`)

```yaml
ai:
  provider: "anthropic"  # Změňte na: anthropic, openai, deepseek, groq, ollama
  model: "claude-sonnet-4-5-20250929"
  temperature: 0.0
  max_tokens: 4096
  
  # Pro Ollama (local)
  ollama_base_url: "http://localhost:11434"
```

### 2. Environment Variables (`.env`)

```bash
# Vyberte provider
AI_PROVIDER=anthropic  # nebo openai, deepseek, groq, ollama

# API klíče (přidejte ty které budete používat)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk_...

# Ollama (local) - pokud používáte
OLLAMA_BASE_URL=http://localhost:11434
```

---

## 📋 Provider Details

### 1️⃣ Anthropic Claude (Doporučeno)

**Modely:**
- `claude-sonnet-4-5-20250929` - Nejlepší poměr cena/výkon (doporučeno)
- `claude-3-5-sonnet-20241022` - Deprecated (bude odstaven 19. února 2026)
- `claude-3-opus-20240229` - Nejvyšší kvalita
- `claude-3-haiku-20240307` - Nejrychlejší, nejlevnější

**Výhody:**
- ✅ Nativní podpora PDF
- ✅ Výborná kvalita extrakce
- ✅ Dobré s českým textem
- ✅ Spolehlivé pro OCR

**Setup:**
```bash
# .env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key
```

**Získat API klíč:**
https://console.anthropic.com/settings/keys

---

### 2️⃣ OpenAI GPT

**Modely:**
- `gpt-4o` - Nejlepší kvalita
- `gpt-4o-mini` - Levnější varianta
- `gpt-4-turbo` - Starší model

**Výhody:**
- ✅ Velmi dobrá kvalita
- ✅ Rychlé API
- ✅ Široká podpora

**Nevýhody:**
- ❌ Nepodporuje PDF přímo (jen obrázky)

**Setup:**
```bash
# .env
AI_PROVIDER=openai
AI_MODEL=gpt-4o
OPENAI_API_KEY=sk-proj-your-key
```

**Získat API klíč:**
https://platform.openai.com/api-keys

---

### 3️⃣ DeepSeek (Budget Option)

**Modely:**
- `deepseek-chat` - Hlavní model

**Výhody:**
- ✅ Velmi nízká cena (~100x levnější než GPT-4)
- ✅ Dobrá kvalita
- ✅ Rychlé API

**Nevýhody:**
- ❌ Nepodporuje PDF
- ⚠️ Může mít problémy s nestandardními faktury

**Setup:**
```bash
# .env
AI_PROVIDER=deepseek
AI_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-your-key
```

**Získat API klíč:**
https://platform.deepseek.com/

---

### 4️⃣ Groq (Fast & Free)

**Modely:**
- `llama-3.2-90b-vision-preview` - Největší model
- `llama-3.2-11b-vision-preview` - Rychlejší

**Výhody:**
- ✅ Velmi rychlá inference
- ✅ Free tier
- ✅ Dobrá kvalita

**Nevýhody:**
- ❌ Nepodporuje PDF
- ⚠️ Rate limity na free tier

**Setup:**
```bash
# .env
AI_PROVIDER=groq
AI_MODEL=llama-3.2-90b-vision-preview
GROQ_API_KEY=gsk_your-key
```

**Získat API klíč:**
https://console.groq.com/keys

---

### 5️⃣ Ollama (Local)

**Modely:**
- `llama3.2-vision` - Llama 3.2 Vision
- `llava` - LLaVA model

**Výhody:**
- ✅ Zcela zdarma
- ✅ 100% soukromé (běží lokálně)
- ✅ Žádné API limity

**Nevýhody:**
- ❌ Nepodporuje PDF
- ❌ Nižší kvalita než cloud modely
- ❌ Pomalejší
- ❌ Vyžaduje dobrý hardware

**Setup:**

1. Instalujte Ollama:
```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com/download
```

2. Stáhněte model:
```bash
ollama pull llama3.2-vision
```

3. Ověřte že běží:
```bash
ollama list
# Měli byste vidět llama3.2-vision
```

4. Nastavte v `.env`:
```bash
AI_PROVIDER=ollama
AI_MODEL=llama3.2-vision
OLLAMA_BASE_URL=http://localhost:11434
```

---

## 🧪 Testování modelů

Použijte notebook `06_model_comparison.ipynb`:

```python
jupyter notebook notebooks/06_model_comparison.ipynb
```

Nebo v kódu:

```python
from src.ai_extractor import AIInvoiceExtractor
from src.config import Config

# Test různých providerů
providers = [
    ('anthropic', 'claude-sonnet-4-5-20250929'),
    ('openai', 'gpt-4o'),
    ('deepseek', 'deepseek-chat'),
]

for provider, model in providers:
    test_config = Config.load_from_yaml()
    test_config.ai.provider = provider
    test_config.ai.model = model
    
    extractor = AIInvoiceExtractor(test_config)
    result = extractor.extract_from_image(image_base64, media_type)
    
    print(f"{provider}: {result.invoice_number}")
```

---

## 💡 Doporučení pro výběr

### Začínáte? 
→ **Anthropic Claude** (claude-sonnet-4-5-20250929)
- Nejlepší kvalita
- Podporuje PDF
- Dobrý poměr cena/výkon

### Máte mnoho faktur?
→ **DeepSeek** (deepseek-chat)
- Velmi levné
- Dobrá kvalita
- Jen pro obrázky (ne PDF)

### Chcete rychlost?
→ **Groq** (llama-3.2-90b-vision)
- Velmi rychlé
- Free tier
- Jen pro obrázky

### Potřebujete soukromí?
→ **Ollama** (local)
- Běží na vašem počítači
- Žádná data neopouští PC
- Vyžaduje dobrý hardware

---

## 📊 Porovnání cen (orientační)

Pro typickou fakturu (~200kB obrázek nebo 5-page PDF):

| Provider | Cena za fakturu | Cena za 1000 faktur |
|----------|----------------|---------------------|
| Anthropic Claude Sonnet 4.5 | $3.00 | $15.00 |
| OpenAI GPT-4o | $0.025 | $25 |
| OpenAI GPT-4o-mini | $0.002 | $2 |
| DeepSeek | $0.0002 | $0.20 |
| Groq | $0 (free tier) | $0* |
| Ollama | $0 | $0 |

\* Groq má rate limity na free tier

---

## ⚙️ Switching Providers

### Metoda 1: Environment Variable (Nejflexibilnější)

```bash
# V .env
AI_PROVIDER=deepseek
AI_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-...
```

Restart aplikace a je hotovo!

### Metoda 2: YAML Config

```yaml
# config/settings.yaml
ai:
  provider: "openai"
  model: "gpt-4o-mini"
```

Restart aplikace.

### Metoda 3: Programmaticky

```python
from src.config import config

config.ai.provider = "groq"
config.ai.model = "llama-3.2-90b-vision-preview"

# Use with new settings
agent = InvoiceProcessingAgent(config)
```

---

## 🆘 Troubleshooting

### "Provider X not installed"

**OpenAI/DeepSeek/Groq/Ollama:**
```bash
uv sync  # Mělo by nainstalovat openai package
# nebo ručně:
pip install openai
```

**Anthropic:**
```bash
pip install anthropic
```

### "API key not found"

Zkontrolujte `.env`:
```bash
cat .env | grep API_KEY
```

### "Ollama connection refused"

Ujistěte se, že Ollama běží:
```bash
ollama serve
# V jiném terminálu:
ollama list
```

### PDF extraction fails with non-Anthropic providers

**Řešení:** Použijte Anthropic pro PDF, nebo převeďte PDF na obrázky:

```python
# Budoucí feature: automatický převod PDF→image
# Prozatím použijte Anthropic nebo naskenujte jako JPG
```

---

## 📈 Performance Tips

### Pro nejvyšší kvalitu:
```yaml
ai:
  provider: "anthropic"
  model: "claude-3-opus-20240229"  # Nejlepší model
```

### Pro nejnižší cenu:
```yaml
ai:
  provider: "deepseek"
  model: "deepseek-chat"
```

### Pro nejvyšší rychlost:
```yaml
ai:
  provider: "groq"
  model: "llama-3.2-90b-vision-preview"
```

### Pro lokální zpracování (privacy):
```yaml
ai:
  provider: "ollama"
  model: "llama3.2-vision"
```

---

**Last Updated:** 2025-10-08  
**Version:** 0.1.0

