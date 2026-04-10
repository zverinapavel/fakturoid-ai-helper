# Fakturoid Invoice Processor

AI-powered invoice processing agent that automatically extracts data from PDF and image invoices and submits them to Fakturoid using Model Context Protocol (MCP).

## Features

- 📄 **Multi-format Support**: Process PDFs and images (JPG, PNG, GIF, WEBP)
- 🤖 **AI-Powered Extraction**: Uses Claude Sonnet 4.5 for accurate data extraction
- ✅ **Smart Validation**: Validates extracted data before submission
- 🔄 **Flexible Workflows**: Manual review, automatic submission, or hybrid modes
- 📊 **Batch Processing**: Process multiple invoices efficiently
- 🔌 **MCP Integration**: Built with Model Context Protocol for Fakturoid API
- 📓 **Jupyter Notebooks**: Incremental development and testing environment

## Quick Start

### 1. Prerequisites

- Python 3.11+
- [UV package manager](https://github.com/astral-sh/uv)
- Anthropic API key
- Fakturoid account with API credentials

### 2. Installation

```bash
# Clone or navigate to project
cd /Users/pavelzverina/AiProjects/fakturoid

# Install dependencies with UV
uv sync

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
```

### 3. Configuration

Create a `.env` file:

```bash
ANTHROPIC_API_KEY=your_key_here
FAKTUROID_EMAIL=your_email@example.com
FAKTUROID_API_KEY=your_fakturoid_api_key
FAKTUROID_ACCOUNT_SLUG=your_account_slug
```

### 4. Process Invoices

```bash
# Place invoices in data/invoices/
# Then run:
python process_invoices.py
```

Or use Python:

```python
from src.agent import InvoiceProcessingAgent

agent = InvoiceProcessingAgent()
agent.test_connections()
results = agent.process_batch(review=True)
```

## Project Structure

```
fakturoid/
├── src/                    # Production code
│   ├── config.py          # Configuration management
│   ├── document_processor.py  # Document loading
│   ├── ai_extractor.py    # AI-powered extraction
│   ├── fakturoid_client.py    # Fakturoid API client
│   └── agent.py           # Main orchestration
├── notebooks/             # Development notebooks
│   ├── 01_document_loader.ipynb
│   ├── 02_data_extraction.ipynb
│   ├── 03_validation.ipynb
│   ├── 04_fakturoid_integration.ipynb
│   └── 05_orchestration.ipynb
├── data/
│   ├── invoices/          # Input invoices
│   └── processed/         # Processed invoices archive
├── config/
│   └── settings.yaml      # Application settings
└── docs/
    └── setup_guide.md     # Detailed setup guide
```

## Documentation

See [`docs/setup_guide.md`](docs/setup_guide.md) for comprehensive documentation including:

- Detailed installation instructions
- Configuration options
- MCP server setup
- Usage examples
- Troubleshooting guide

## Development

### Using Jupyter Notebooks

```bash
# Start Jupyter
jupyter notebook

# Open notebooks in sequence:
# 1. Document Loader
# 2. Data Extraction
# 3. Validation
# 4. Fakturoid Integration
# 5. Orchestration
```

Each notebook demonstrates a specific component of the pipeline.

### Running Tests

```bash
# Run specific notebook
jupyter execute notebooks/01_document_loader.ipynb

# Or test components directly
python -c "from src.config import config; print(config.ai.model)"
```

## Workflow Modes

### Manual Review (Recommended for initial use)

```python
agent = InvoiceProcessingAgent(auto_submit=False)
results = agent.process_batch(review=True)
```

Each invoice is displayed for review before submission.

### Automatic Mode

```python
agent = InvoiceProcessingAgent(auto_submit=True)
results = agent.process_batch(review=False)
```

⚠️ Automatically submits all valid invoices without review.

### Hybrid Mode

Process with validation, approve only valid invoices automatically.

## Extracted Data Fields

### Required Fields
- Invoice number
- Issue date
- Supplier name
- Total amount

### Optional Fields
- Due date
- Variable symbol
- Supplier address, IČO, DIČ
- Line items with quantities and prices
- Tax amount
- Currency

## Technologies

- **Python 3.11+**: Core language
- **UV**: Fast Python package manager
- **Anthropic Claude**: AI vision model for invoice parsing
- **Fakturoid API**: Invoice management system
- **MCP**: Model Context Protocol for API communication
- **Pydantic**: Data validation
- **Jupyter**: Interactive development

## Configuration

Edit `config/settings.yaml` to customize:

- Processing mode (auto/manual)
- AI model selection
- Required/optional fields
- Batch size
- Logging level

## Troubleshooting

**Connection issues:**
```python
from src.fakturoid_client import FakturoidClient
from src.config import config

client = FakturoidClient(
    email=config.fakturoid.email,
    api_key=config.fakturoid.api_key,
    account_slug=config.fakturoid.account_slug
)
print(client.test_connection())
```

**Extraction issues:**
- Ensure images are high resolution
- Check API key is valid
- Review logs in `logs/processor.log`

See [`docs/setup_guide.md`](docs/setup_guide.md) for detailed troubleshooting.

## License

MIT

## Contributing

Contributions welcome! Please ensure:
- Code follows project structure
- Tests pass
- Documentation is updated

## Roadmap

- [ ] Web interface for manual review
- [ ] Support for more invoice formats
- [ ] Multi-language invoice support
- [ ] Advanced validation rules
- [ ] Email integration for automated invoice receipt
- [ ] Duplicate detection
- [ ] Export to other accounting systems

## Support

For issues and questions:
1. Check `docs/setup_guide.md`
2. Review example notebooks
3. Check logs in `logs/processor.log`

---

**Version**: 0.1.0  
**Author**: Pavel Zverina  
**Last Updated**: October 2025

