# Quick Start Guide

Get started with Fakturoid Invoice Processor in 5 minutes!

## Step 1: Prerequisites Check

Make sure you have:
- ✅ Python 3.11 or higher: `python --version`
- ✅ UV installed: `uv --version`
- ✅ Git initialized (already done in this project)

If UV is not installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Step 2: Install Dependencies

```bash
# From project root
cd /Users/pavelzverina/AiProjects/fakturoid

# Install all dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

## Step 3: Configure Credentials

Create a `.env` file in the project root:

```bash
# Create from template
cat > .env << 'EOF'
# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Fakturoid Credentials
FAKTUROID_EMAIL=your@email.com
FAKTUROID_API_KEY=xxxxx
FAKTUROID_ACCOUNT_SLUG=your-account

# Processing Settings
PROCESSING_MODE=manual
AUTO_SUBMIT=false
LOG_LEVEL=INFO
EOF
```

### Where to get credentials:

**Anthropic API Key:**
1. Go to https://console.anthropic.com
2. Sign up / Log in
3. Navigate to API Keys
4. Create new key
5. Copy to `.env`

**Fakturoid Credentials:**
1. Log into https://app.fakturoid.cz
2. Go to Settings → API
3. Generate API key
4. Copy email, API key, and account slug to `.env`

## Step 4: Test Configuration

```bash
# Test that everything is configured correctly
python example_usage.py

# Select option 4 or 5 to check configuration
```

Or test directly:

```python
python -c "
from src.config import config
print('✓ Configuration loaded')
print(f'AI Model: {config.ai.model}')
print(f'Fakturoid Account: {config.fakturoid.account_slug}')
"
```

## Step 5: Add Sample Invoices

Place your invoice files in the `data/invoices/` directory:

```bash
# Example: copy invoices
cp /path/to/your/invoice.pdf data/invoices/
cp /path/to/your/scanned_invoice.jpg data/invoices/
```

Supported formats: PDF, JPG, PNG, GIF, WEBP

## Step 6: Process Invoices

### Option A: Interactive CLI

```bash
python process_invoices.py
```

This will:
1. List all invoices found
2. Ask for confirmation
3. Process each invoice
4. Display extracted data for review
5. Ask if you want to submit to Fakturoid

### Option B: Python Script

```python
from src.agent import InvoiceProcessingAgent

# Initialize
agent = InvoiceProcessingAgent()

# Test connection
if agent.test_connections():
    print("✓ Connected to Fakturoid!")
    
    # Process with manual review
    results = agent.process_batch(review=True, max_files=5)
    
    # Check results
    for result in results:
        print(f"{result['file']}: {result['status']}")
```

### Option C: Jupyter Notebooks

```bash
jupyter notebook
```

Open and run:
1. `notebooks/01_document_loader.ipynb` - Test loading
2. `notebooks/02_data_extraction.ipynb` - Test AI extraction
3. `notebooks/05_orchestration.ipynb` - Full pipeline

## Step 7: Review Results

After processing:

1. **Check extracted data** displayed in console
2. **Verify in Fakturoid** if auto-submitted
3. **Processed invoices** are moved to `data/processed/`
4. **Check logs** in `logs/processor.log`

## Common First-Time Issues

### "ANTHROPIC_API_KEY not set"
→ Make sure `.env` file exists and contains your API key

### "Fakturoid connection failed"
→ Verify credentials in `.env` are correct

### "No invoice files found"
→ Add PDF or image files to `data/invoices/` directory

### Import errors
→ Make sure virtual environment is activated: `source .venv/bin/activate`

## Next Steps

Once everything works:

1. **Process more invoices** - Add more files to `data/invoices/`
2. **Customize settings** - Edit `config/settings.yaml`
3. **Enable auto-submit** - Set `AUTO_SUBMIT=true` in `.env` (use with caution!)
4. **Explore notebooks** - Learn how each component works
5. **Read full docs** - See `docs/setup_guide.md`

## Daily Usage

```bash
# 1. Add new invoices to data/invoices/
# 2. Run processor
python process_invoices.py

# 3. Review and approve
# 4. Check results in Fakturoid
```

## Quick Reference

```bash
# Process with review (recommended)
python process_invoices.py

# Process automatically (no review)
python process_invoices.py --auto

# Process max 10 files
python process_invoices.py --max 10

# Run examples
python example_usage.py

# Start Jupyter
jupyter notebook

# View logs
tail -f logs/processor.log

# Check configuration
python -c "from src.config import config; print(config.model_dump())"
```

## Help & Support

- 📖 **Full Documentation**: `docs/setup_guide.md`
- 🇨🇿 **Czech Guide**: `docs/czechREADME.md`
- 📓 **Examples**: `example_usage.py`
- 📔 **Notebooks**: `notebooks/` directory
- 📝 **Logs**: `logs/processor.log`

---

**Ready to go!** 🚀

Your first invoice should take about 10-20 seconds to process depending on the file size and complexity.

