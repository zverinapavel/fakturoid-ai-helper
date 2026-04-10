# Provoz a chování aplikace

## Spuštění

```bash
# z kořene projektu, aktivní venv
python process_invoices.py
```

Nejčastější volby:

| Argument | Význam |
|----------|--------|
| *(žádný)* nebo `--auto` | Odeslání všech faktur bez dotazování na každou zvlášť (výchozí) |
| `--review` / `-r` nebo `--manual` | U každé faktury náhled a potvrzení (y/n/q) před odesláním |
| `--extract-only` | Jen extrakce dat, bez Fakturoidu |
| `--max N` | Zpracovat nejvýše N souborů |
| `--invoices-dir CESTA` | Jiný vstupní adresář než v `settings.yaml` |

Nápověda: `python process_invoices.py --help`.

## Po úspěšném odeslání — pojmenování souborů

Soubor se přesune do `processed/` s názvem ve tvaru:

`[číslo nákladu] - [dodavatel] - [krátký popis] - [původní název].pdf`

Příklad: `FP20240189 - Alza.cz a.s. - Software - faktura.pdf`

## AI validace

Po první extrakci model data ještě jednou zkontroluje (částky, měny, položky). Když něco nesedí, pole se opraví nebo vyprázdní — v logu uvidíš stručný diff.

## Dodavatelé — ČR a zahraničí

- **České IČO:** při vytváření subjektu v Fakturoidu se může doplnit adresa z **ARES** (veřejný registr).
- **Zahraniční:** AI extrahuje VAT a adresu z faktury; ARES se nepoužívá.

## AI providery (stručně)

Výchozí je Anthropic (včetně PDF). Ostatní providery často vyžadují převod PDF na obrázky — nastavení v `settings.yaml` / `.env` a klíče podle [`CONFIGURATION.md`](CONFIGURATION.md).

## Náklady na API

Sleduj usage u svého providera (Anthropic / OpenAI / …). V konzoli se při běhu mohou vypisovat odhady tokenů podle implementace v `ai_extractor`.

## Logy

Výchozí soubor: `logs/processor.log` (cesta z konfigurace).
