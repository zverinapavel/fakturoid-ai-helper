#!/usr/bin/env python
"""
Example usage of the Fakturoid Invoice Processor.

This file demonstrates various ways to use the invoice processing agent.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from agent import InvoiceProcessingAgent
from config import config


def example_1_basic_usage():
    """Example 1: Basic usage with manual review."""
    print("="*60)
    print("EXAMPLE 1: Basic Usage")
    print("="*60 + "\n")
    
    # Initialize the agent
    agent = InvoiceProcessingAgent()
    
    # Test connections
    if not agent.test_connections():
        print("Connection failed! Check your credentials.")
        return
    
    # Process invoices with manual review
    results = agent.process_batch(review=True, max_files=5)
    
    # Print summary
    print(f"\nProcessed {len(results)} invoices")
    for result in results:
        print(f"  - {result['file']}: {result['status']}")


def example_2_single_file():
    """Example 2: Process a single file."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Single File Processing")
    print("="*60 + "\n")
    
    agent = InvoiceProcessingAgent()
    
    # Get list of files
    files = agent.doc_processor.list_invoice_files()
    
    if not files:
        print("No invoice files found in data/invoices/")
        return
    
    # Process first file
    result = agent.process_file(files[0], review=True)
    
    print(f"\nResult: {result['status']}")
    if result['extracted_data']:
        data = result['extracted_data']
        print(f"Invoice: {data.get('invoice_number')}")
        print(f"Supplier: {data.get('supplier_name')}")
        print(f"Amount: {data.get('total_amount')} {data.get('currency', 'CZK')}")


def example_3_custom_directories():
    """Example 3: Use custom directories."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Custom Directories")
    print("="*60 + "\n")
    
    # Use custom directories
    agent = InvoiceProcessingAgent(
        invoices_dir=Path("data/invoices"),
        processed_dir=Path("data/processed"),
        auto_submit=False
    )
    
    print(f"Invoices directory: {agent.invoices_dir}")
    print(f"Processed directory: {agent.processed_dir}")
    print(f"Auto-submit: {agent.auto_submit}")


def example_4_check_configuration():
    """Example 4: Check current configuration."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Current Configuration")
    print("="*60 + "\n")
    
    print("Processing Settings:")
    print(f"  Mode: {config.processing.mode}")
    print(f"  Auto-submit: {config.processing.auto_submit}")
    print(f"  Batch size: {config.processing.batch_size}")
    
    print("\nAI Configuration:")
    print(f"  Provider: {config.ai.provider}")
    print(f"  Model: {config.ai.model}")
    print(f"  Temperature: {config.ai.temperature}")
    
    print("\nRequired Fields:")
    for field in config.extraction.required_fields:
        print(f"  - {field}")
    
    print("\nFakturoid:")
    print(f"  Email: {config.fakturoid.email}")
    print(f"  Account: {config.fakturoid.account_slug}")


def example_5_component_testing():
    """Example 5: Test individual components."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Component Testing")
    print("="*60 + "\n")
    
    from document_processor import DocumentProcessor
    from ai_extractor import AIInvoiceExtractor
    from fakturoid_client import FakturoidClient
    
    # Test document processor
    print("1. Testing Document Processor...")
    doc_processor = DocumentProcessor(config.directories.invoices)
    files = doc_processor.list_invoice_files()
    print(f"   Found {len(files)} invoice files")
    
    # Test AI extractor initialization
    print("\n2. Testing AI Extractor...")
    try:
        ai_extractor = AIInvoiceExtractor(
            api_key=config.anthropic_api_key,
            model=config.ai.model
        )
        print(f"   ✓ AI Extractor initialized with model: {config.ai.model}")
    except Exception as e:
        print(f"   ✗ AI Extractor failed: {e}")
    
    # Test Fakturoid client
    print("\n3. Testing Fakturoid Client...")
    try:
        client = FakturoidClient(
            email=config.fakturoid.email,
            api_key=config.fakturoid.api_key,
            account_slug=config.fakturoid.account_slug
        )
        if client.test_connection():
            print("   ✓ Fakturoid connection successful")
            account_info = client.get_account_info()
            print(f"   Account: {account_info.get('name')}")
        else:
            print("   ✗ Fakturoid connection failed")
    except Exception as e:
        print(f"   ✗ Fakturoid client error: {e}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("FAKTUROID INVOICE PROCESSOR - EXAMPLES")
    print("="*60 + "\n")
    
    print("Select an example to run:")
    print("1. Basic Usage (process with review)")
    print("2. Single File Processing")
    print("3. Custom Directories")
    print("4. Check Configuration")
    print("5. Component Testing")
    print("0. Run All Examples (non-interactive)")
    
    choice = input("\nEnter choice (0-5): ").strip()
    
    examples = {
        '1': example_1_basic_usage,
        '2': example_2_single_file,
        '3': example_3_custom_directories,
        '4': example_4_check_configuration,
        '5': example_5_component_testing,
    }
    
    if choice == '0':
        # Run all examples (except those that need interaction)
        example_3_custom_directories()
        example_4_check_configuration()
        example_5_component_testing()
    elif choice in examples:
        examples[choice]()
    else:
        print("Invalid choice!")
        return 1
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

