# Changelog

All notable changes to the Fakturoid Invoice Processor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-07

### Added
- Initial project setup with UV package manager
- Git repository initialization
- Core modules:
  - `config.py` - Configuration management with YAML and environment variables
  - `document_processor.py` - PDF and image invoice loading
  - `ai_extractor.py` - AI-powered data extraction using Claude Sonnet 4.5
  - `fakturoid_client.py` - Fakturoid API client integration
  - `agent.py` - Main orchestration agent
- Jupyter notebooks for incremental development:
  - 01_document_loader.ipynb - Document loading tests
  - 02_data_extraction.ipynb - AI extraction tests
  - 03_validation.ipynb - Validation workflow
  - 04_fakturoid_integration.ipynb - Fakturoid API tests
  - 05_orchestration.ipynb - Complete pipeline
- Command-line interface (`process_invoices.py`)
- Example usage script (`example_usage.py`)
- Comprehensive documentation:
  - README.md (English)
  - docs/setup_guide.md (detailed English guide)
  - docs/czechREADME.md (Czech guide)
  - CHANGELOG.md
- Configuration files:
  - pyproject.toml for UV package management
  - config/settings.yaml for application settings
  - .env.example for environment variables template
  - .gitignore for version control
- Directory structure:
  - src/ for production code
  - notebooks/ for development notebooks
  - data/invoices/ for input invoices
  - data/processed/ for processed invoices archive
  - config/ for configuration files
  - docs/ for documentation
  - logs/ for application logs

### Features
- Multi-format invoice support (PDF, JPG, PNG, GIF, WEBP)
- AI-powered data extraction with Claude Sonnet 4.5
- Configurable validation of required and optional fields
- Manual review and automatic submission modes
- Batch processing capabilities
- Integration with Fakturoid API
- Automatic subject (supplier) creation
- Invoice archiving after processing
- Comprehensive logging
- Error handling and reporting

### Configuration
- Support for both YAML configuration files and environment variables
- Customizable required/optional invoice fields
- AI model selection and parameters
- Processing modes (auto/manual/both)
- Directory paths configuration
- Logging level and format configuration

### Dependencies
- anthropic >= 0.39.0 - AI vision models
- mcp >= 0.9.0 - Model Context Protocol
- pypdf >= 4.0.0 - PDF processing
- pillow >= 10.0.0 - Image processing
- pydantic >= 2.0.0 - Data validation
- python-dotenv >= 1.0.0 - Environment configuration
- jupyter >= 1.0.0 - Interactive development
- pyyaml >= 6.0.0 - YAML configuration
- requests >= 2.31.0 - HTTP client

### Documentation
- Complete setup guide with installation instructions
- Usage examples and workflow documentation
- Troubleshooting section
- API integration guide
- Notebook-based tutorials
- Czech language documentation

## [Unreleased]

### Planned
- Web interface for manual review
- Support for more invoice formats (XML, EDI)
- Multi-language invoice support
- Advanced validation rules
- Email integration for automated invoice receipt
- Duplicate invoice detection
- Export to other accounting systems
- Performance optimizations
- Unit tests and integration tests
- CI/CD pipeline
- Docker containerization
- API documentation
- Video tutorials

---

[0.1.0]: https://github.com/yourusername/fakturoid/releases/tag/v0.1.0

