#!/usr/bin/env python
"""
Process invoices from command line.

This script provides a simple command-line interface for processing invoices
from the data/invoices directory and submitting them to Fakturoid.

Usage:
    python process_invoices.py [options]

Modes:
    (default)       Submit all invoices without per-invoice confirmation
    --review, -r    Confirm each invoice interactively before submission
    --manual        Same as --review
    --auto          Explicit automatic mode (same as default)
    --extract-only  Extract data only, don't submit to Fakturoid

Options:
    --max N         Process at most N invoices
    --help          Show this help message
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Ensure project root is importable (for `from src...` when run as a script)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.agent import InvoiceProcessingAgent
from src.config import config
from src.ai_extractor import InvoiceData
from src.fakturoid_client import FakturoidClient


def display_invoice_details(data: dict):
    """Display detailed invoice information including line items."""
    print("\n" + "="*60)
    print("📄 EXTRAHOVANÁ DATA")
    print("="*60)
    print(f"Číslo faktury: {data.get('invoice_number')}")
    print(f"Datum vystavení: {data.get('issue_date')}")
    print(f"Datum splatnosti: {data.get('due_date') or 'N/A'}")
    print(f"Variabilní symbol: {data.get('variable_symbol') or 'N/A'}")
    
    print(f"\n🏢 Dodavatel: {data.get('supplier_name')}")
    if data.get('supplier_ico'):
        print(f"   IČO: {data.get('supplier_ico')}")
    if data.get('supplier_dic'):
        print(f"   DIČ: {data.get('supplier_dic')}")
    if data.get('supplier_vat_number'):
        print(f"   VAT: {data.get('supplier_vat_number')}")
    if data.get('supplier_street'):
        print(f"   Adresa: {data.get('supplier_street')}")
    if data.get('supplier_city'):
        print(f"          {data.get('supplier_city')}, {data.get('supplier_zip') or ''}")
    if data.get('supplier_country'):
        print(f"          {data.get('supplier_country')}")
    
    print(f"\n💰 Celková částka: {data.get('total_amount')} {data.get('currency', 'CZK')}")
    if data.get('tax_amount'):
        print(f"   DPH: {data.get('tax_amount')} {data.get('currency', 'CZK')}")
    
    # Display line items
    if data.get('line_items') and len(data['line_items']) > 0:
        print(f"\n📋 Položky faktury ({len(data['line_items'])}):")
        for i, item in enumerate(data['line_items'], 1):
            desc = item.get('description', item.get('name', 'N/A'))
            qty = item.get('quantity', 1)
            price = item.get('unit_price', 0)
            total = item.get('total', qty * price if price else 0)
            print(f"   {i}. {desc}")
            print(f"      {qty} x {price} = {total}")
    
    if data.get('notes'):
        print(f"\n📝 Poznámky: {data.get('notes')}")
    
    print("="*60)


def display_amount_validation(client: FakturoidClient, invoice_data: InvoiceData) -> bool:
    """Run and print Fakturoid amount check. Returns True if amounts match."""
    validation = client.validate_expense_amounts(invoice_data)
    print(f"\n{client.format_amount_validation_message(validation)}")
    return bool(validation.get("ok"))


def process_review_mode(agent: InvoiceProcessingAgent, max_files: Optional[int] = None) -> list:
    """Process invoices with interactive confirmation for each file.
    
    Args:
        agent: Invoice processing agent
        max_files: Maximum number of files to process
        
    Returns:
        List of processing results
    """
    files = agent.doc_processor.list_invoice_files()
    if max_files:
        files = files[:max_files]
    
    results = []
    
    for i, file_path in enumerate(files, 1):
        print(f"\n{'='*60}")
        print(f"📄 Faktura {i}/{len(files)}: {file_path.name}")
        print(f"{'='*60}")
        
        try:
            # Extract data using extract_invoice_data (includes validation and tracking)
            print("\n⏳ Extrahuji data...")
            invoice_data_dict = agent.ai_extractor.extract_invoice_data(file_path)
            invoice_data = InvoiceData(**invoice_data_dict)
            
            # Display extracted data
            display_invoice_details(invoice_data_dict)
            amounts_ok = display_amount_validation(agent.fakturoid_client, invoice_data)
            if not amounts_ok:
                print(
                    "\n⚠️  Částky nesedí — doporučeno zkontrolovat položky / DPH před odesláním."
                )
            
            # Ask for confirmation
            print(f"\n❓ Odeslat tuto fakturu do Fakturoidu?")
            response = input("   (y)es / (n)o / (q)uit: ").lower().strip()
            
            if response == 'q':
                print("\n⏹️  Zpracování přerušeno uživatelem.")
                break
            elif response == 'y':
                print("\n⏳ Odesílám do Fakturoidu...")
                try:
                    fakturoid_response = agent.fakturoid_client.submit_expense(invoice_data)
                    print(f"\n✅ Úspěšně odesláno!")
                    print(f"   Číslo nákladu: {fakturoid_response.get('number')}")
                    print(f"   ID: {fakturoid_response.get('id')}")
                    if fakturoid_response.get('html_url'):
                        print(f"   🔗 Odkaz: {fakturoid_response.get('html_url')}")
                    
                    # Move to processed
                    agent._move_to_processed(file_path, invoice_data, fakturoid_response)
                    
                    results.append({
                        'file': file_path.name,
                        'status': 'submitted',
                        'extracted_data': invoice_data.model_dump(),
                        'fakturoid_response': fakturoid_response,
                        'error': None
                    })
                except Exception as e:
                    print(f"❌ Chyba při odesílání: {e}")
                    results.append({
                        'file': file_path.name,
                        'status': 'error',
                        'extracted_data': invoice_data.model_dump(),
                        'fakturoid_response': None,
                        'error': str(e)
                    })
            else:
                print("⏭️  Přeskočeno - pokračuji na další fakturu")
                results.append({
                    'file': file_path.name,
                    'status': 'skipped',
                    'extracted_data': invoice_data.model_dump(),
                    'fakturoid_response': None,
                    'error': None
                })
        
        except Exception as e:
            print(f"❌ Chyba při zpracování: {e}")
            results.append({
                'file': file_path.name,
                'status': 'error',
                'extracted_data': None,
                'fakturoid_response': None,
                'error': str(e)
            })
    
    if hasattr(agent, "ai_extractor") and hasattr(agent.ai_extractor, "print_usage_summary"):
        agent.ai_extractor.print_usage_summary()

    return results


def main():
    """Main entry point for CLI invoice processing."""
    parser = argparse.ArgumentParser(
        description='Process invoices and submit to Fakturoid',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Processing modes (mutually exclusive; default is automatic batch submit)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--review',
        '-r',
        action='store_true',
        help='Ask for confirmation on each invoice before submitting to Fakturoid',
    )
    mode_group.add_argument(
        '--manual',
        action='store_true',
        help='Same as --review (interactive confirmation per invoice)',
    )
    mode_group.add_argument(
        '--auto',
        action='store_true',
        help='Submit all invoices without review (default if no mode flag is given)',
    )
    mode_group.add_argument(
        '--extract-only',
        action='store_true',
        help='Extract data only, do not submit to Fakturoid',
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
    
    # Determine mode (default: automatic batch processing)
    if args.extract_only:
        mode = 'extract-only'
    elif args.review or args.manual:
        mode = 'review'
    else:
        mode = 'auto'  # Default when no mode flag (also when --auto)
    
    # Display configuration (flush so banner appears before logging from libraries)
    print("=" * 60, flush=True)
    print("FAKTUROID INVOICE PROCESSOR", flush=True)
    print("=" * 60, flush=True)
    mode_label = {'auto': 'AUTO (batch submit)', 'review': 'REVIEW (interactive)', 'extract-only': 'EXTRACT-ONLY'}.get(mode, mode.upper())
    print(f"Mode: {mode_label}", flush=True)
    print(f"Invoices directory: {args.invoices_dir or config.directories.invoices}", flush=True)
    print(f"Max files: {args.max or 'unlimited'}", flush=True)
    print(f"AI Model: {config.ai.model}", flush=True)
    print("=" * 60 + "\n", flush=True)
    
    # Initialize agent
    agent = InvoiceProcessingAgent(
        config_obj=config,
        invoices_dir=Path(args.invoices_dir) if args.invoices_dir else None,
        auto_submit=False  # We'll handle submission manually based on mode
    )
    
    # Test connections (skip for extract-only mode)
    if mode != 'extract-only':
        print("Testing connections...")
        if not agent.test_connections():
            print("\n❌ Failed to connect to Fakturoid. Please check your credentials in .env file.")
            return 1
        print("✅ Connection successful!\n")
    else:
        print("Extract-only mode: skipping connection test\n")
    
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
    
    # Run selected mode
    if mode == 'auto':
        print("⚙️  Submitting all invoices without per-invoice confirmation.\n")
        results = agent.process_batch(review=False, max_files=args.max)

    elif mode == 'extract-only':
        print("📋 EXTRACT-ONLY — data will be extracted but not submitted")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Processing cancelled.")
            return 0
        print("\nExtracting invoice data...\n")
        results = agent.process_batch(review=True, max_files=args.max)

    else:  # review (interactive)
        print("🔍 REVIEW MODE — confirm each invoice before it is sent to Fakturoid\n")
        results = process_review_mode(agent, args.max)
    
    # Display results
    print("\n" + "="*60)
    print("PROCESSING RESULTS")
    print("="*60 + "\n")
    
    for i, result in enumerate(results, 1):
        status_icon = {
            'submitted': '✅',
            'extracted': '📋',
            'skipped': '⏭️',
            'error': '❌',
            'pending': '⏳'
        }.get(result['status'], '❓')
        
        print(f"{i}. {status_icon} {result['file']}")
        print(f"   Status: {result['status']}")
        
        if result.get('extracted_data'):
            data = result['extracted_data']
            print(f"   Faktura: {data.get('invoice_number')}")
            print(f"   Dodavatel: {data.get('supplier_name')}")
            print(f"   Částka: {data.get('total_amount')} {data.get('currency', 'CZK')}")
            
            # Show line items if available
            if data.get('line_items') and len(data['line_items']) > 0:
                print(f"   Položky:")
                for item in data['line_items'][:3]:  # Show first 3
                    desc = item.get('description', item.get('name', 'N/A'))
                    print(f"      • {desc[:40]}...")
                if len(data['line_items']) > 3:
                    print(f"      ... a {len(data['line_items']) - 3} dalších")
        
        if result.get('fakturoid_response'):
            resp = result['fakturoid_response']
            print(f"   Fakturoid ID: {resp.get('id')}")
            print(f"   Číslo nákladu: {resp.get('number')}")
            if resp.get('html_url'):
                print(f"   🔗 {resp.get('html_url')}")
        
        if result.get('error'):
            print(f"   Chyba: {result['error']}")
        
        print()
    
    # Summary
    submitted = sum(1 for r in results if r['status'] == 'submitted')
    extracted = sum(1 for r in results if r['status'] == 'extracted')
    skipped = sum(1 for r in results if r['status'] == 'skipped')
    errors = sum(1 for r in results if r['status'] == 'error')
    
    print("="*60)
    print(f"SUMMARY: {len(results)} total | {submitted} submitted | {skipped} skipped | {extracted} extracted | {errors} errors")
    print("="*60)
    # AI usage summary: process_batch / extract-only already printed it; review mode prints inside process_review_mode

    if mode == 'extract-only':
        print(f"\n📋 {len(results)} invoice(s) extracted")
        print("   No invoices were submitted (extract-only mode)")
    elif extracted > 0:
        print(f"\n📋 {extracted} invoice(s) extracted but not submitted")
    
    if skipped > 0:
        print(f"\n⏭️  {skipped} invoice(s) skipped by user")
    
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

