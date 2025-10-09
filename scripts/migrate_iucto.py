#!/usr/bin/env python
"""
Migrate invoices from iÚčto to Fakturoid.

This script handles the one-time migration of historical invoice data
from iÚčto.cz to Fakturoid for years 2013-2021.

Usage:
    python scripts/migrate_iucto.py --year 2013 --dry-run
    python scripts/migrate_iucto.py --year 2013 --execute
    python scripts/migrate_iucto.py --year-range 2013-2021 --execute
"""

import sys
import argparse
from pathlib import Path
import yaml
import os
import json
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from iucto_migration.iucto_client import IUctoClient
from iucto_migration.transfer_agent import TransferAgent
from src.fakturoid_client import FakturoidClient
from src.config import config as main_config


def load_migration_config() -> dict:
    """Load migration configuration from YAML."""
    config_path = Path(__file__).parent.parent / 'config' / 'migration_settings.yaml'
    
    if not config_path.exists():
        return {'migration': {}}
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate invoices from iÚčto to Fakturoid',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Year selection
    year_group = parser.add_mutually_exclusive_group(required=True)
    year_group.add_argument(
        '--year',
        type=int,
        help='Migrate specific year (e.g., 2013)'
    )
    year_group.add_argument(
        '--year-range',
        type=str,
        help='Migrate year range (e.g., 2013-2021)'
    )
    year_group.add_argument(
        '--test-connection',
        action='store_true',
        help='Only test API connections'
    )
    
    # Execution mode
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate migration without creating records (default)'
    )
    mode_group.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute the migration'
    )
    
    # Type filters
    parser.add_argument(
        '--issued-only',
        action='store_true',
        help='Transfer only issued invoices'
    )
    parser.add_argument(
        '--received-only',
        action='store_true',
        help='Transfer only received invoices'
    )
    parser.add_argument(
        '--no-mark-paid',
        action='store_true',
        help='Do not mark invoices as paid'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of invoices to process (for testing)'
    )
    
    args = parser.parse_args()
    
    # Determine mode
    dry_run = not args.execute  # Default to dry-run
    
    print("=" * 60)
    print("iÚčto → FAKTUROID MIGRATION")
    print("=" * 60)
    print(f"Mode: {'EXECUTION' if not dry_run else 'DRY RUN'}")
    print("=" * 60 + "\n")
    
    # Load configuration
    migration_config = load_migration_config()
    
    # Get API keys
    iucto_api_key = os.getenv('IUCTO_API_KEY')
    if not iucto_api_key:
        print("❌ IUCTO_API_KEY not found in environment")
        print("Please add to your .env file:")
        print("IUCTO_API_KEY=your_iucto_api_key")
        return 1
    
    # Initialize clients
    print("Initializing API clients...")
    iucto_client = IUctoClient(iucto_api_key)
    fakturoid_client = FakturoidClient(main_config)
    
    # Test connections
    if args.test_connection:
        print("\nTesting iÚčto connection...")
        if iucto_client.test_connection():
            print("✓ iÚčto connection successful")
            account = iucto_client.get_account_info()
            print(f"  Account: {account.get('name', 'N/A')}")
        else:
            print("✗ iÚčto connection failed")
            return 1
        
        print("\nTesting Fakturoid connection...")
        if fakturoid_client.test_connection():
            print("✓ Fakturoid connection successful")
            account = fakturoid_client.get_account_info()
            print(f"  Account: {account.get('name', 'N/A')}")
        else:
            print("✗ Fakturoid connection failed")
            return 1
        
        print("\n✓ All connections successful!")
        return 0
    
    # Test connections
    if not iucto_client.test_connection():
        print("❌ Failed to connect to iÚčto")
        return 1
    
    if not fakturoid_client.test_connection():
        print("❌ Failed to connect to Fakturoid")
        return 1
    
    print("✓ Connections successful\n")
    
    # Initialize transfer agent
    transfer_config = migration_config.get('migration', {})
    if args.no_mark_paid:
        transfer_config['auto_mark_paid'] = False
    
    agent = TransferAgent(iucto_client, fakturoid_client, transfer_config)
    
    # Determine what to transfer
    transfer_issued = not args.received_only
    transfer_received = not args.issued_only
    
    # Process years
    if args.year:
        years = [args.year]
    elif args.year_range:
        start, end = map(int, args.year_range.split('-'))
        years = list(range(start, end + 1))
    else:
        years = []
    
    # Confirm execution
    if not dry_run:
        print(f"⚠️  EXECUTION MODE - Will transfer invoices to Fakturoid!")
        print(f"Years: {years}")
        print(f"Issued: {transfer_issued}")
        print(f"Received: {transfer_received}")
        response = input("\nContinue? (y/n): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return 0
    
    print(f"\n{'='*60}")
    print("Starting migration...")
    print(f"{'='*60}\n")
    
    # Process each year
    all_reports = []
    
    for year in years:
        print(f"\n{'#'*60}")
        print(f"# Processing year {year}")
        print(f"{'#'*60}\n")
        
        report = agent.transfer_year(
            year=year,
            dry_run=dry_run,
            transfer_issued=transfer_issued,
            transfer_received=transfer_received,
            limit=args.limit
        )
        
        all_reports.append(report)
        
        # Display report
        print("\n" + agent.generate_report(report))
        
        # Save report
        if not dry_run:
            report_file = f"logs/migration_report_{year}.json"
            agent.save_report(report, report_file)
    
    # Combined summary
    if len(all_reports) > 1:
        print(f"\n{'='*60}")
        print("COMBINED SUMMARY")
        print(f"{'='*60}")
        
        total_issued = sum(r['issued']['transferred'] for r in all_reports)
        total_received = sum(r['received']['transferred'] for r in all_reports)
        total_skipped = sum(r['issued']['skipped'] + r['received']['skipped'] for r in all_reports)
        total_errors = sum(r['issued']['errors'] + r['received']['errors'] for r in all_reports)
        
        print(f"Years processed: {len(years)}")
        print(f"Issued invoices transferred: {total_issued}")
        print(f"Received invoices transferred: {total_received}")
        print(f"Skipped (duplicates): {total_skipped}")
        print(f"Errors: {total_errors}")
        print(f"{'='*60}")
        
        # Save combined report
        if not dry_run:
            combined_report = {
                'migration_date': datetime.now().isoformat(),
                'years': years,
                'total_issued': total_issued,
                'total_received': total_received,
                'total_skipped': total_skipped,
                'total_errors': total_errors,
                'yearly_reports': all_reports
            }
            
            combined_file = "logs/migration_report_complete.json"
            with open(combined_file, 'w') as f:
                json.dump(combined_report, f, indent=2, ensure_ascii=False)
            print(f"\n📄 Combined report saved to: {combined_file}")
    
    return 0 if sum(r['issued']['errors'] + r['received']['errors'] for r in all_reports) == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

