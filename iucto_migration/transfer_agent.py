"""Transfer agent for orchestrating iÚčto to Fakturoid migration."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time
import json

try:
    from src.fakturoid_client import FakturoidClient
except ImportError:
    from fakturoid_client import FakturoidClient

from iucto_migration.iucto_client import IUctoClient
from iucto_migration.data_mapper import IUctoToFakturoidMapper


class TransferAgent:
    """Orchestrates the transfer of invoices from iÚčto to Fakturoid."""
    
    def __init__(
        self,
        iucto_client: IUctoClient,
        fakturoid_client: FakturoidClient,
        config: Dict[str, Any]
    ):
        """Initialize transfer agent.
        
        Args:
            iucto_client: iÚčto API client
            fakturoid_client: Fakturoid API client
            config: Migration configuration dict
        """
        self.iucto = iucto_client
        self.fakturoid = fakturoid_client
        self.config = config
        self.mapper = IUctoToFakturoidMapper(fakturoid_client)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def transfer_year(
        self,
        year: int,
        dry_run: bool = True,
        transfer_issued: bool = True,
        transfer_received: bool = True,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Transfer all invoices for a specific year.
        
        Args:
            year: Year to transfer (e.g., 2013)
            dry_run: If True, only simulate transfer without creating records
            transfer_issued: Whether to transfer issued invoices
            transfer_received: Whether to transfer received invoices
            limit: Maximum number of invoices to process
            
        Returns:
            Report dictionary with statistics
        """
        report = {
            'year': year,
            'dry_run': dry_run,
            'timestamp': datetime.now().isoformat(),
            'issued': {'total': 0, 'transferred': 0, 'skipped': 0, 'errors': 0},
            'received': {'total': 0, 'transferred': 0, 'skipped': 0, 'errors': 0},
            'details': []
        }
        
        # Transfer issued invoices
        if transfer_issued:
            print(f"\n{'='*60}")
            print(f"Transferring ISSUED invoices for {year}")
            print(f"{'='*60}\n")
            
            try:
                invoices = self.iucto.get_issued_invoices(year=year, limit=limit)
                report['issued']['total'] = len(invoices)
                print(f"Found {len(invoices)} issued invoices")
                
                for i, invoice in enumerate(invoices, 1):
                    print(f"\nProcessing {i}/{len(invoices)}: {invoice.get('number', 'N/A')}")
                    result = self._transfer_issued_invoice(invoice, dry_run)
                    report['details'].append(result)
                    
                    if result['status'] == 'transferred':
                        report['issued']['transferred'] += 1
                    elif result['status'] == 'skipped':
                        report['issued']['skipped'] += 1
                    else:
                        report['issued']['errors'] += 1
                    
                    # Rate limiting
                    if not dry_run and i % self.config.get('batch_size', 50) == 0:
                        delay = self.config.get('delay_between_batches', 2)
                        print(f"Batch complete, waiting {delay}s...")
                        time.sleep(delay)
                        
            except Exception as e:
                print(f"Error fetching issued invoices: {e}")
                report['issued']['errors'] = 1
        
        # Transfer received invoices
        if transfer_received:
            print(f"\n{'='*60}")
            print(f"Transferring RECEIVED invoices for {year}")
            print(f"{'='*60}\n")
            
            try:
                expenses = self.iucto.get_received_invoices(year=year, limit=limit)
                report['received']['total'] = len(expenses)
                print(f"Found {len(expenses)} received invoices")
                
                for i, expense in enumerate(expenses, 1):
                    print(f"\nProcessing {i}/{len(expenses)}: {expense.get('number', 'N/A')}")
                    result = self._transfer_received_invoice(expense, dry_run)
                    report['details'].append(result)
                    
                    if result['status'] == 'transferred':
                        report['received']['transferred'] += 1
                    elif result['status'] == 'skipped':
                        report['received']['skipped'] += 1
                    else:
                        report['received']['errors'] += 1
                    
                    # Rate limiting
                    if not dry_run and i % self.config.get('batch_size', 50) == 0:
                        delay = self.config.get('delay_between_batches', 2)
                        print(f"Batch complete, waiting {delay}s...")
                        time.sleep(delay)
                        
            except Exception as e:
                print(f"Error fetching received invoices: {e}")
                report['received']['errors'] = 1
        
        return report
    
    def _transfer_issued_invoice(self, iucto_invoice: Dict, dry_run: bool) -> Dict[str, Any]:
        """Transfer a single issued invoice.
        
        Args:
            iucto_invoice: Invoice from iÚčto
            dry_run: If True, don't actually create
            
        Returns:
            Result dictionary
        """
        try:
            invoice_number = iucto_invoice.get('number', 'N/A')
            
            # Check for duplicate
            if self.config.get('skip_duplicates', True):
                if self._is_duplicate_issued(iucto_invoice):
                    print(f"  ⏭️  Skipped: duplicate")
                    return {
                        'type': 'issued',
                        'iucto_id': iucto_invoice.get('id'),
                        'number': invoice_number,
                        'status': 'skipped',
                        'reason': 'duplicate'
                    }
            
            # Map data
            fakturoid_data, is_paid, paid_date = self.mapper.map_issued_invoice(iucto_invoice)
            
            if dry_run:
                print(f"  🔍 Dry run: would create invoice {invoice_number}")
                return {
                    'type': 'issued',
                    'iucto_id': iucto_invoice.get('id'),
                    'number': invoice_number,
                    'status': 'dry_run',
                    'data': fakturoid_data,
                    'would_mark_paid': is_paid
                }
            
            # Create in Fakturoid
            created = self.fakturoid.create_invoice(fakturoid_data)
            print(f"  ✓ Created: {created.get('number')} (ID: {created.get('id')})")
            
            # Mark as paid if needed
            if is_paid and self.config.get('auto_mark_paid', True):
                payment_date = self._determine_payment_date(
                    paid_date,
                    iucto_invoice.get('due_date'),
                    iucto_invoice.get('issue_date')
                )
                self._mark_invoice_paid(created['id'], payment_date, fakturoid_data.get('total', 0))
                print(f"  ✓ Marked as paid ({payment_date})")
            
            return {
                'type': 'issued',
                'iucto_id': iucto_invoice.get('id'),
                'number': invoice_number,
                'status': 'transferred',
                'fakturoid_id': created['id'],
                'fakturoid_number': created['number'],
                'paid': is_paid
            }
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return {
                'type': 'issued',
                'iucto_id': iucto_invoice.get('id'),
                'number': iucto_invoice.get('number', 'N/A'),
                'status': 'error',
                'error': str(e)
            }
    
    def _transfer_received_invoice(self, iucto_expense: Dict, dry_run: bool) -> Dict[str, Any]:
        """Transfer a single received invoice/expense.
        
        Args:
            iucto_expense: Expense from iÚčto
            dry_run: If True, don't actually create
            
        Returns:
            Result dictionary
        """
        try:
            expense_number = iucto_expense.get('number', 'N/A')
            
            # Check for duplicate
            if self.config.get('skip_duplicates', True):
                if self._is_duplicate_received(iucto_expense):
                    print(f"  ⏭️  Skipped: duplicate")
                    return {
                        'type': 'received',
                        'iucto_id': iucto_expense.get('id'),
                        'number': expense_number,
                        'status': 'skipped',
                        'reason': 'duplicate'
                    }
            
            # Map data
            fakturoid_data, is_paid, paid_date = self.mapper.map_received_invoice(iucto_expense)
            
            if dry_run:
                print(f"  🔍 Dry run: would create expense {expense_number}")
                return {
                    'type': 'received',
                    'iucto_id': iucto_expense.get('id'),
                    'number': expense_number,
                    'status': 'dry_run',
                    'data': fakturoid_data,
                    'would_mark_paid': is_paid
                }
            
            # Create in Fakturoid
            created = self.fakturoid.create_expense_invoice(fakturoid_data)
            print(f"  ✓ Created: {created.get('number')} (ID: {created.get('id')})")
            
            # Mark as paid if needed
            if is_paid and self.config.get('auto_mark_paid', True):
                payment_date = self._determine_payment_date(
                    paid_date,
                    iucto_expense.get('due_date'),
                    iucto_expense.get('issue_date')
                )
                self._mark_expense_paid(created['id'], payment_date, fakturoid_data.get('total', 0))
                print(f"  ✓ Marked as paid ({payment_date})")
            
            return {
                'type': 'received',
                'iucto_id': iucto_expense.get('id'),
                'number': expense_number,
                'status': 'transferred',
                'fakturoid_id': created['id'],
                'fakturoid_number': created['number'],
                'paid': is_paid
            }
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return {
                'type': 'received',
                'iucto_id': iucto_expense.get('id'),
                'number': iucto_expense.get('number', 'N/A'),
                'status': 'error',
                'error': str(e)
            }
    
    def _is_duplicate_issued(self, iucto_invoice: Dict) -> bool:
        """Check if issued invoice already exists in Fakturoid.
        
        Args:
            iucto_invoice: Invoice from iÚčto
            
        Returns:
            True if duplicate found
        """
        # Simple check: search by invoice number
        # In production, you might want more sophisticated duplicate detection
        try:
            invoices = self.fakturoid.session.get(
                self.fakturoid._get_url("invoices.json"),
                params={'number': iucto_invoice.get('number')}
            ).json()
            
            return len(invoices) > 0 if isinstance(invoices, list) else False
        except:
            return False
    
    def _is_duplicate_received(self, iucto_expense: Dict) -> bool:
        """Check if received invoice already exists in Fakturoid.
        
        Args:
            iucto_expense: Expense from iÚčto
            
        Returns:
            True if duplicate found
        """
        try:
            expenses = self.fakturoid.session.get(
                self.fakturoid._get_url("expenses.json"),
                params={'original_number': iucto_expense.get('number')}
            ).json()
            
            return len(expenses) > 0 if isinstance(expenses, list) else False
        except:
            return False
    
    def _determine_payment_date(
        self,
        paid_date: Optional[str],
        due_date: Optional[str],
        issue_date: str
    ) -> str:
        """Determine the payment date to use.
        
        Args:
            paid_date: Actual payment date from iÚčto
            due_date: Due date
            issue_date: Issue date (fallback)
            
        Returns:
            Date string to use for payment (YYYY-MM-DD)
        """
        strategy = self.config.get('payment_date_strategy', 'due_date')
        
        if strategy == 'paid_date' and paid_date:
            return paid_date
        elif strategy == 'due_date' and due_date:
            return due_date
        elif paid_date:
            return paid_date
        elif due_date:
            return due_date
        else:
            return issue_date
    
    def _mark_invoice_paid(self, invoice_id: int, payment_date: str, amount: float):
        """Mark issued invoice as paid in Fakturoid.
        
        Args:
            invoice_id: Fakturoid invoice ID
            payment_date: Date of payment
            amount: Payment amount
        """
        try:
            url = self.fakturoid._get_url(f"invoices/{invoice_id}/fire.json")
            data = {
                'event': 'pay',
                'paid_on': payment_date,
                'paid_amount': amount
            }
            response = self.fakturoid.session.post(url, json=data)
            response.raise_for_status()
        except Exception as e:
            self.logger.warning(f"Failed to mark invoice {invoice_id} as paid: {e}")
    
    def _mark_expense_paid(self, expense_id: int, payment_date: str, amount: float):
        """Mark expense as paid in Fakturoid.
        
        Args:
            expense_id: Fakturoid expense ID
            payment_date: Date of payment
            amount: Payment amount
        """
        try:
            url = self.fakturoid._get_url(f"expenses/{expense_id}/fire.json")
            data = {
                'event': 'pay',
                'paid_on': payment_date,
                'paid_amount': amount
            }
            response = self.fakturoid.session.post(url, json=data)
            response.raise_for_status()
        except Exception as e:
            self.logger.warning(f"Failed to mark expense {expense_id} as paid: {e}")
    
    def generate_report(self, report: Dict) -> str:
        """Generate human-readable report.
        
        Args:
            report: Report dictionary
            
        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"MIGRATION REPORT - Year {report['year']}")
        lines.append("=" * 60)
        lines.append(f"Date: {report['timestamp']}")
        lines.append(f"Mode: {'DRY RUN' if report['dry_run'] else 'EXECUTION'}")
        lines.append("")
        
        # Issued invoices
        issued = report['issued']
        lines.append(f"Issued Invoices:")
        lines.append(f"  Total: {issued['total']}")
        lines.append(f"  Transferred: {issued['transferred']}")
        lines.append(f"  Skipped: {issued['skipped']}")
        lines.append(f"  Errors: {issued['errors']}")
        lines.append("")
        
        # Received invoices
        received = report['received']
        lines.append(f"Received Invoices:")
        lines.append(f"  Total: {received['total']}")
        lines.append(f"  Transferred: {received['transferred']}")
        lines.append(f"  Skipped: {received['skipped']}")
        lines.append(f"  Errors: {received['errors']}")
        lines.append("")
        
        # Summary
        total_transferred = issued['transferred'] + received['transferred']
        total_skipped = issued['skipped'] + received['skipped']
        total_errors = issued['errors'] + received['errors']
        total = issued['total'] + received['total']
        
        lines.append(f"TOTAL:")
        lines.append(f"  All documents: {total}")
        lines.append(f"  Transferred: {total_transferred}")
        lines.append(f"  Skipped: {total_skipped}")
        lines.append(f"  Errors: {total_errors}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def save_report(self, report: Dict, filename: str):
        """Save report to JSON file.
        
        Args:
            report: Report dictionary
            filename: Output filename
        """
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Report saved to: {filename}")

