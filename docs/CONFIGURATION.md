# Konfigurace

## Priorita

1. **Proměnné prostředí** (`.env` nebo systém) — nejvyšší priorita  
2. **`config/settings.yaml`**  
3. **Výchozí hodnoty** v kódu

API klíče a Fakturoid údaje jdou **výhradně z `.env`**, nikdy je nedávej do YAML.

## Kde co upravit

| Co | Kde |
|----|-----|
| Tajné klíče (Anthropic, Fakturoid OAuth, …) | `.env` |
| Adresáře `invoices` / `processed` | `config/settings.yaml` → `directories` |
| Výchozí AI provider a model | `settings.yaml` nebo `.env` (`AI_PROVIDER`, `AI_MODEL`) |
| Režim zpracování (`manual` / `auto`), `auto_submit` | `settings.yaml` nebo `.env` (`PROCESSING_MODE`, `AUTO_SUBMIT`) |
| Úroveň logů | `LOG_LEVEL` v `.env` nebo `logging.level` v YAML |

Šablona proměnných: [`env.example`](../env.example).

## Povinné proměnné (typický provoz)

| Proměnná | Účel |
|----------|------|
| `ANTHROPIC_API_KEY` | AI extrakce (pokud `AI_PROVIDER=anthropic`) |
| `FAKTUROID_CLIENT_ID` | OAuth klient (lze starý název `FAKTUROID_EMAIL`) |
| `FAKTUROID_CLIENT_SECRET` | OAuth secret (lze `FAKTUROID_API_KEY`) |
| `FAKTUROID_ACCOUNT_SLUG` | Slug účtu z URL Fakturoidu |

Podle zvoleného `AI_PROVIDER` musí být v `.env` nastavený odpovídající klíč (`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`); Ollama klíč nepotřebuje.

## Volitelné

| Proměnná | Výchozí | Poznámka |
|----------|---------|----------|
| `AI_PROVIDER` | `anthropic` | např. `openai`, `deepseek`, `groq`, `ollama` |
| `AI_MODEL` | dle výchozího modelu v kódu | |
| `PROCESSING_MODE` | `manual` | |
| `AUTO_SUBMIT` | `false` | |
| `LOG_LEVEL` | `INFO` | |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | jen pro Ollama |

Adresáře vstupních faktur **nejsou** v `.env` — pouze v `config/settings.yaml`. Jednorázově lze při spuštění použít `python process_invoices.py --invoices-dir /cesta` (viz [`USAGE.md`](USAGE.md)).

## Ověření načtení konfigurace

```python
from src.config import config
print(config.ai.provider, config.ai.model)
print(config.directories.invoices)
```
