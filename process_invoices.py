#!/usr/bin/env python
"""
Process invoices from command line.

This script provides a simple command-line interface for processing invoices
from the data/invoices directory and submitting them to Fakturoid.

Usage:
    python process_invoices.py [options]

Options:
    --auto          Enable automatic submission (no review)
    --max N         Process at most N invoices
    --help          Show this help message
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from agent import InvoiceProcessingAgent
from config import config


def main():
    """Main entry point for CLI invoice processing."""
    parser = argparse.ArgumentParser(
        description='Process invoices and submit to Fakturoid',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Enable automatic submission without review'
    )
    
    parser.add_argument(
        '--max',
        type=int,
        default=None,
        metavar='N',
        help='Process at most N invoices'
    )
    
    parser.add_argument(
        '--invoices-dir',
        type=str,
        default=None,
        help=f'Directory containing invoices (default: {config.directories.invoices})'
    )
    
    args = parser.parse_args()
    
    # Display configuration
    print("="*60)
    print("FAKTUROID INVOICE PROCESSOR")
    print("="*60)
    print(f"Invoices directory: {args.invoices_dir or config.directories.invoices}")
    print(f"Auto-submit: {args.auto}")
    print(f"Max files: {args.max or 'unlimited'}")
    print(f"AI Model: {config.ai.model}")
    print("="*60 + "\n")
    
    # Initialize agent
    agent = InvoiceProcessingAgent(
        invoices_dir=Path(args.invoices_dir) if args.invoices_dir else None,
        auto_submit=args.auto
    )
    
    # Test connections
    print("Testing connections...")
    if not agent.test_connections():
        print("\n❌ Failed to connect to Fakturoid. Please check your credentials in .env file.")
        return 1
    
    print("✅ Connection successful!\n")
    
    # List available invoices
    files = agent.doc_processor.list_invoice_files()
    
    if not files:
        print("No invoice files found in the invoices directory.")
        print(f"Please add PDF or image files to: {agent.invoices_dir}")
        return 0
    
    print(f"Found {len(files)} invoice file(s):\n")
    for i, f in enumerate(files[:10], 1):  # Show first 10
        print(f"  {i}. {f.name}")
    
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more")
    
    print()
    
    # Confirm processing
    if not args.auto:
        response = input(f"Process invoices with manual review? (y/n): ")
        if response.lower() != 'y':
            print("Processing cancelled.")
            return 0
    else:
        print("⚠️  AUTO-SUBMIT MODE ENABLED - Invoices will be submitted without review!")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Processing cancelled.")
            return 0
    
    print("\nProcessing invoices...\n")
    
    # Process invoices
    results = agent.process_batch(
        review=not args.auto,
        max_files=args.max
    )
    
    # Display results
    print("\n" + "="*60)
    print("PROCESSING RESULTS")
    print("="*60 + "\n")
    
    for i, result in enumerate(results, 1):
        status_icon = {
            'submitted': '✅',
            'extracted': '📋',
            'error': '❌',
            'pending': '⏳'
        }.get(result['status'], '❓')
        
        print(f"{i}. {status_icon} {result['file']}")
        print(f"   Status: {result['status']}")
        
        if result.get('extracted_data'):
            data = result['extracted_data']
            print(f"   Invoice: {data.get('invoice_number')}")
            print(f"   Supplier: {data.get('supplier_name')}")
            print(f"   Amount: {data.get('total_amount')} {data.get('currency', 'CZK')}")
        
        if result.get('error'):
            print(f"   Error: {result['error']}")
        
        print()
    
    # Summary
    submitted = sum(1 for r in results if r['status'] == 'submitted')
    extracted = sum(1 for r in results if r['status'] == 'extracted')
    errors = sum(1 for r in results if r['status'] == 'error')
    
    print("="*60)
    print(f"SUMMARY: {len(results)} total | {submitted} submitted | {extracted} extracted | {errors} errors")
    print("="*60)
    
    if extracted > 0 and not args.auto:
        print(f"\n📋 {extracted} invoice(s) extracted but not submitted (manual review mode)")
        print("   To submit these invoices, review the data and run with --auto flag")
    
    if errors > 0:
        print(f"\n❌ {errors} invoice(s) failed to process")
        print("   Check logs/processor.log for details")
    
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

