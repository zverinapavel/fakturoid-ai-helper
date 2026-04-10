# Fakturoid Invoice Processor - Setup Guide

Comprehensive guide for setting up and using the AI-powered invoice processing system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [MCP Server Setup](#mcp-server-setup)
5. [Usage](#usage)
6. [Development with Notebooks](#development-with-notebooks)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.11+** installed on your system
- **uv** package manager ([installation guide](https://github.com/astral-sh/uv))
- **Anthropic API key** for AI vision models
- **Fakturoid account** with API credentials
- **Git** for version control

## Installation

### 1. Install UV Package Manager

If you don't have UV installed:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone/Navigate to Project Directory

```bash
cd /Users/pavelzverina/AiProjects/fakturoid
```

### 3. Initialize UV Environment

```bash
# Create virtual environment and install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows
```

### 4. Verify Installation

```bash
python --version  # Should show Python 3.11+
python -c "import anthropic; print('Anthropic SDK installed')"
```

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# Anthropic API Key for AI vision models
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Fakturoid Configuration
FAKTUROID_EMAIL=your_email@example.com
FAKTUROID_API_KEY=your_fakturoid_api_key
FAKTUROID_ACCOUNT_SLUG=your_account_slug

# Processing Configuration
PROCESSING_MODE=manual  # Options: auto, manual, both
AUTO_SUBMIT=false

# Directories
INVOICES_DIR=data/invoices
PROCESSED_DIR=data/processed

# Logging
LOG_LEVEL=INFO
```

### 2. Get Your Credentials

#### Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and paste into `.env` file

#### Fakturoid API Key

1. Log into your Fakturoid account
2. Go to Settings → API
3. Generate an API key
4. Copy your:
   - Email address
   - API key
   - Account slug (subdomain of your Fakturoid URL)

### 3. Adjust Settings (Optional)

Edit `config/settings.yaml` to customize:

```yaml
# Processing mode
processing:
  mode: "manual"  # auto | manual | both
  auto_submit: false
  batch_size: 10

# AI model selection
ai:
  provider: "anthropic"
  model: "claude-sonnet-4-5-20250929"
  temperature: 0.0

# Required invoice fields
extraction:
  required_fields:
    - invoice_number
    - issue_date
    - supplier_name
    - total_amount
```

## MCP Server Setup

This project uses the Model Context Protocol (MCP) for communication with Fakturoid.

### Option 1: Using Existing MCP Server

If a Fakturoid MCP server is available:

```bash
# Install the MCP server package
uv add fakturoid-mcp-server  # Example - actual package name may vary
```

### Option 2: Direct API Integration

The project includes a direct Fakturoid API client (`src/fakturoid_client.py`) that works without MCP for simpler setup.

## Usage

### Quick Start

1. **Place invoice files** in the `data/invoices/` directory
   - Supported formats: PDF, JPG, PNG, GIF, WEBP

2. **Run the processing agent:**

```python
from src.agent import InvoiceProcessingAgent

# Initialize
agent = InvoiceProcessingAgent()

# Test connections
agent.test_connections()

# Process invoices with manual review
results = agent.process_batch(review=True)
```

### Command-Line Usage

Create a simple CLI script (`process_invoices.py`):

```python
#!/usr/bin/env python
"""Process invoices from command line."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from agent import InvoiceProcessingAgent

def main():
    agent = InvoiceProcessingAgent()
    
    # Test connections
    if not agent.test_connections():
        print("Failed to connect to Fakturoid. Check your credentials.")
        return 1
    
    # Process invoices
    results = agent.process_batch(review=True)
    
    # Summary
    successful = sum(1 for r in results if r['status'] == 'submitted')
    print(f"\nProcessed {len(results)} invoices, {successful} submitted successfully.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Run with:

```bash
python process_invoices.py
```

### Processing Modes

#### 1. Manual Review Mode (Recommended for first use)

```python
agent = InvoiceProcessingAgent(auto_submit=False)
results = agent.process_batch(review=True)
```

Each invoice will be displayed for review before submission.

#### 2. Automatic Mode (Fully automated)

```python
agent = InvoiceProcessingAgent(auto_submit=True)
results = agent.process_batch(review=False)
```

⚠️ **Caution:** This will automatically submit all invoices to Fakturoid without review!

#### 3. Mixed Mode (Review but auto-approve valid invoices)

```python
agent = InvoiceProcessingAgent(auto_submit=False)
results = agent.process_batch(review=True)
# Review each invoice, decide to submit or skip
```

## Development with Notebooks

The project includes Jupyter notebooks for incremental development and testing.

### 1. Start Jupyter

```bash
jupyter notebook
```

### 2. Available Notebooks

- **01_document_loader.ipynb** - Test document loading (PDF/images)
- **02_data_extraction.ipynb** - Test AI extraction
- **03_validation.ipynb** - Test validation and review workflow
- **04_fakturoid_integration.ipynb** - Test Fakturoid API integration
- **05_orchestration.ipynb** - Complete pipeline demonstration

### 3. Notebook Development Workflow

1. Open `notebooks/01_document_loader.ipynb`
2. Run cells to test document loading
3. Add sample invoices to `data/invoices/`
4. Progress through notebooks sequentially
5. Test each component before moving to the next

### 4. Testing with Sample Data

Add sample invoice files to `data/invoices/`:

```
data/invoices/
  ├── sample_invoice_001.pdf
  ├── sample_invoice_002.jpg
  └── scanned_invoice_003.png
```

## Troubleshooting

### Common Issues

#### 1. "ANTHROPIC_API_KEY not set"

**Solution:**
- Ensure `.env` file exists in project root
- Check that `ANTHROPIC_API_KEY` is set correctly
- Try running: `python -c "from src.config import config; print(config.anthropic_api_key)"`

#### 2. "Fakturoid connection failed"

**Solution:**
- Verify credentials in `.env` file
- Check that your Fakturoid account is active
- Test API manually: `curl -u "email:api_key" https://app.fakturoid.cz/api/v3/accounts/{slug}/account.json`

#### 3. "No invoice files found"

**Solution:**
- Check that files are in `data/invoices/` directory
- Verify file formats are supported (PDF, JPG, PNG, GIF, WEBP)
- Check file permissions

#### 4. "Extraction errors or poor quality"

**Solution:**
- Ensure invoice images are clear and high-resolution
- For scanned documents, try improving scan quality
- Adjust AI model temperature in `config/settings.yaml`
- Try different AI models (e.g., `claude-3-opus-20240229` for complex invoices)

#### 5. "Import errors when running notebooks"

**Solution:**
- Ensure you're using the correct Python environment
- Check that all dependencies are installed: `uv sync`
- Verify the `sys.path.insert()` line points to the correct `src` directory

### Logs and Debugging

**Check logs:**

```bash
tail -f logs/processor.log
```

**Enable debug logging:**

Edit `config/settings.yaml`:

```yaml
logging:
  level: "DEBUG"
```

**Test individual components:**

```python
# Test document loading
from src.document_processor import DocumentProcessor
doc_processor = DocumentProcessor("data/invoices")
files = doc_processor.list_invoice_files()

# Test AI extraction
from src.ai_extractor import AIInvoiceExtractor
from src.config import config
extractor = AIInvoiceExtractor(api_key=config.anthropic_api_key)

# Test Fakturoid connection
from src.fakturoid_client import FakturoidClient
client = FakturoidClient(
    email=config.fakturoid.email,
    api_key=config.fakturoid.api_key,
    account_slug=config.fakturoid.account_slug
)
print(client.test_connection())
```

## Advanced Usage

### Custom Extraction Fields

Edit `config/settings.yaml` to add custom fields:

```yaml
extraction:
  required_fields:
    - invoice_number
    - issue_date
    - supplier_name
    - total_amount
    - custom_field  # Your custom field
  optional_fields:
    - another_custom_field
```

Then update the extraction prompt in `src/ai_extractor.py`.

### Batch Processing with Scheduling

Use cron (Linux/macOS) or Task Scheduler (Windows) to run automatically:

```bash
# Add to crontab (every hour)
0 * * * * cd /Users/pavelzverina/AiProjects/fakturoid && /path/to/venv/bin/python process_invoices.py
```

### Multiple Invoice Directories

```python
from src.agent import InvoiceProcessingAgent

# Process different invoice types
suppliers_agent = InvoiceProcessingAgent(invoices_dir="data/suppliers")
utilities_agent = InvoiceProcessingAgent(invoices_dir="data/utilities")

suppliers_agent.process_batch()
utilities_agent.process_batch()
```

## Support and Contribution

### Getting Help

- Check the logs in `logs/processor.log`
- Review notebook examples
- Test individual components in isolation

### Best Practices

1. **Always test with sample data first**
2. **Use manual review mode initially**
3. **Backup your invoices before processing**
4. **Monitor the first few submissions carefully**
5. **Keep your API keys secure and never commit them to Git**

## Next Steps

1. ✅ Complete setup and configuration
2. ✅ Test with sample invoices
3. ✅ Run through notebooks to understand each component
4. ✅ Process a few invoices in manual mode
5. ✅ Review results in Fakturoid
6. ✅ Adjust configuration as needed
7. ✅ Consider automating for production use

---

**Version:** 0.1.0  
**Last Updated:** October 2025  
**License:** MIT

