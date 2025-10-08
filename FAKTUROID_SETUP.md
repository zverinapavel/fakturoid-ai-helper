# Fakturoid API Setup (OAuth 2.0)

Tento projekt používá **Fakturoid API v3** s **OAuth 2.0 Client Credentials Flow**.

## 📋 Jak získat přístupové údaje

### 1. Přihlaste se do Fakturoidu
Jděte na: https://app.fakturoid.cz

### 2. Vygenerujte Client ID a Client Secret
- Klikněte na **Nastavení** (Settings)
- Vyberte **Uživatelský účet** (User account)
- V sekci **OAuth 2 přístupové údaje** klikněte na **Vygenerovat nové přístupové údaje**
- Zkopírujte **Client ID** a **Client Secret**

⚠️ **DŮLEŽITÉ**: Používáme **Client Credentials Flow**, NE Authorization Code Flow!

### 3. Zjistěte Account Slug
Account slug je první část URL vašeho Fakturoid účtu.

Například:
- Pro `https://mujucet.fakturoid.cz` je slug: `mujucet`
- Pro `https://firma.fakturoid.cz` je slug: `firma`

## 🔧 Konfigurace

### Vytvořte soubor `.env` v kořenu projektu:

```bash
# Anthropic API Key (pro Claude AI)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Fakturoid OAuth 2.0 Credentials
FAKTUROID_CLIENT_ID=your-client-id-here
FAKTUROID_CLIENT_SECRET=your-client-secret-here
FAKTUROID_ACCOUNT_SLUG=your-account-slug

# Příklad:
# FAKTUROID_CLIENT_ID=9ae1...f3d8
# FAKTUROID_CLIENT_SECRET=a7b2...c4e5
# FAKTUROID_ACCOUNT_SLUG=mujucet
```

## 🔐 Jak OAuth 2.0 funguje

1. **Při inicializaci** klient získá access token pomocí Client ID a Secret
2. **Access token** je platný 2 hodiny
3. **Automatické obnovení**: Před expirací se token automaticky obnoví
4. Všechny API requesty používají: `Authorization: Bearer <access_token>`

## 📚 Dokumentace

- [Fakturoid API v3 - Authorization](https://www.fakturoid.cz/api/v3/authorization#client-credentials-flow)
- [Fakturoid API v3 - Expenses](https://www.fakturoid.cz/api/v3/expenses)

## ✅ Test připojení

V notebooku `04_fakturoid_integration.ipynb` spusťte první buňky pro test připojení:

```python
from src.fakturoid_client import FakturoidClient
from src.config import config

fakturoid = FakturoidClient(config)
account_info = fakturoid.get_account_info()
print(account_info)
```

Pokud vše funguje, měli byste vidět informace o vašem účtu!

