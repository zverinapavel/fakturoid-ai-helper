# Kde co konfigurovat?

Jednoduchý přehled, kde nastavit různé věci v projektu.

## 📁 Adresáře (invoices, processed)

**Kde:** `config/settings.yaml`

```yaml
directories:
  invoices: "data/invoices"
  processed: "data/processed"
```

**Proč YAML, ne .env?**
- Adresáře jsou součást struktury projektu
- Nejsou to "tajemství" jako API klíče
- Lépe se verzují v gitu

---

## 🔐 API klíče a credentials

**Kde:** `.env` soubor

```bash
ANTHROPIC_API_KEY=sk-ant-...
FAKTUROID_CLIENT_ID=...
FAKTUROID_CLIENT_SECRET=...
FAKTUROID_ACCOUNT_SLUG=...
```

**Proč .env, ne YAML?**
- API klíče jsou tajné
- .env se NECOMMITUJE do gitu
- Různé klíče pro dev/prod

---

## 🤖 AI Model

**Kde:** Oba! (ale .env má přednost)

**YAML** - pro výchozí nastavení:
```yaml
ai:
  provider: "anthropic"
  model: "claude-sonnet-4-5-20250929"
```

**.env** - pro přepsání:
```bash
AI_PROVIDER=deepseek
AI_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-...
```

---

## ⚙️ Processing režim

**Kde:** Oba! (ale .env má přednost)

**YAML** - pro výchozí:
```yaml
processing:
  mode: "manual"
  auto_submit: false
  batch_size: 10
```

**.env** - pro přepsání:
```bash
PROCESSING_MODE=auto
AUTO_SUBMIT=true
```

---

## 📝 Logging

**Kde:** Oba! (ale .env má přednost)

**YAML** - pro výchozí:
```yaml
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/processor.log"
```

**.env** - pro přepsání:
```bash
LOG_LEVEL=DEBUG
```

---

## 🎯 Quick Reference

| Co chci nastavit | Kam to dát | Proč |
|------------------|------------|------|
| API klíče | `.env` | Tajné, necommitovat |
| Adresáře | `settings.yaml` | Struktura projektu |
| AI model | `.env` nebo `settings.yaml` | .env pro experimenty |
| Processing mode | `.env` nebo `settings.yaml` | .env pro změny |
| Log level | `.env` nebo `settings.yaml` | .env pro debug |

---

## 💡 Doporučený workflow

### Pro vývoj:

1. **V `settings.yaml`:** Nastavte výchozí hodnoty
   ```yaml
   directories:
     invoices: "data/invoices"
   ai:
     provider: "anthropic"
   processing:
     mode: "manual"
   ```

2. **V `.env`:** Tajné klíče a experimenty
   ```bash
   ANTHROPIC_API_KEY=sk-ant-dev...
   
   # Pro testování jiného modelu:
   # AI_PROVIDER=deepseek
   # DEEPSEEK_API_KEY=sk-...
   ```

### Pro produkci:

1. **V `settings.yaml`:** Základní struktura (commituje se)
   ```yaml
   directories:
     invoices: "data/invoices"
   processing:
     batch_size: 50  # Větší pro produkci
   ```

2. **V `.env`:** Vše ostatní (NECOMMITUJE se)
   ```bash
   ANTHROPIC_API_KEY=sk-ant-prod...
   FAKTUROID_CLIENT_ID=prod_id
   FAKTUROID_CLIENT_SECRET=prod_secret
   
   PROCESSING_MODE=auto
   AUTO_SUBMIT=true
   LOG_LEVEL=INFO
   ```

---

## ✅ Pravidla

1. **API klíče** → Vždy jen `.env`
2. **Adresáře** → Vždy jen `settings.yaml`
3. **AI provider/model** → `.env` OR `settings.yaml` (.env má přednost)
4. **Processing mode** → `.env` OR `settings.yaml` (.env má přednost)
5. **Log level** → `.env` OR `settings.yaml` (.env má přednost)

---

## 🔄 Změna konfigurace

### Změnit adresáře:

```bash
nano config/settings.yaml
# Upravte directories.invoices a directories.processed
```

### Změnit AI model:

```bash
nano .env
# Přidejte:
# AI_PROVIDER=deepseek
# AI_MODEL=deepseek-chat
# DEEPSEEK_API_KEY=sk-...
```

### Změnit režim:

```bash
nano .env
# Přidejte:
# PROCESSING_MODE=auto
# AUTO_SUBMIT=true
```

---

**Tip:** `.env` je pro **runtime změny**, `settings.yaml` je pro **projektovou strukturu**.

---

**Last Updated:** 2025-10-08  
**Version:** 0.1.0

