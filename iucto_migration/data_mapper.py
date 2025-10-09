"""Data mapping from iÚčto format to Fakturoid format."""

from typing import Dict, List, Tuple, Optional, Any


class IUctoToFakturoidMapper:
    """Maps data from iÚčto format to Fakturoid format."""
    
    def __init__(self, fakturoid_client):
        """Initialize mapper.
        
        Args:
            fakturoid_client: Instance of FakturoidClient
        """
        self.fakturoid = fakturoid_client
    
    def map_issued_invoice(self, iucto_invoice: Dict) -> Tuple[Dict, bool, Optional[str]]:
        """Convert issued invoice from iÚčto to Fakturoid format.
        
        Args:
            iucto_invoice: Invoice data from iÚčto
            
        Returns:
            Tuple of (fakturoid_invoice_dict, is_paid, payment_date)
        """
        # Get or create customer (subject)
        customer = iucto_invoice.get('customer', {})
        subject_id = self._get_or_create_subject(
            name=customer.get('name', 'Unknown Customer'),
            ico=customer.get('ico'),
            dic=customer.get('dic'),
            address=customer.get('address'),
            is_supplier=False
        )
        
        # Map line items
        lines = self._map_line_items(iucto_invoice.get('items', []))
        
        # Build Fakturoid invoice
        fakturoid_invoice = {
            'subject_id': subject_id,
            'number': iucto_invoice.get('number'),
            'variable_symbol': iucto_invoice.get('variable_symbol'),
            'issued_on': iucto_invoice.get('issue_date'),
            'due_on': iucto_invoice.get('due_date'),
            'lines': lines
        }
        
        # Add optional fields if present
        if iucto_invoice.get('note'):
            fakturoid_invoice['note'] = iucto_invoice['note']
        
        # Payment info
        is_paid = iucto_invoice.get('paid', False)
        paid_date = iucto_invoice.get('paid_date')
        
        return fakturoid_invoice, is_paid, paid_date
    
    def map_received_invoice(self, iucto_expense: Dict) -> Tuple[Dict, bool, Optional[str]]:
        """Convert received invoice/expense from iÚčto to Fakturoid format.
        
        Args:
            iucto_expense: Expense data from iÚčto
            
        Returns:
            Tuple of (fakturoid_expense_dict, is_paid, payment_date)
        """
        # Get or create supplier (subject)
        supplier = iucto_expense.get('supplier', {})
        subject_id = self._get_or_create_subject(
            name=supplier.get('name', 'Unknown Supplier'),
            ico=supplier.get('ico'),
            dic=supplier.get('dic'),
            vat_number=supplier.get('vat_no'),
            address=supplier.get('address'),
            street=supplier.get('street'),
            city=supplier.get('city'),
            zip_code=supplier.get('zip'),
            country=supplier.get('country'),
            is_supplier=True
        )
        
        # Map line items
        lines = self._map_line_items(iucto_expense.get('items', []))
        
        # Build Fakturoid expense
        fakturoid_expense = {
            'subject_id': subject_id,
            'original_number': iucto_expense.get('number'),
            'variable_symbol': iucto_expense.get('variable_symbol'),
            'issued_on': iucto_expense.get('issue_date'),
            'due_on': iucto_expense.get('due_date'),
            'received_on': iucto_expense.get('received_date') or iucto_expense.get('issue_date'),
            'taxable_fulfillment_due': iucto_expense.get('taxable_fulfillment_due') or iucto_expense.get('issue_date'),
            'lines': lines,
            'document_type': 'invoice'
        }
        
        # Add optional fields
        if iucto_expense.get('description'):
            fakturoid_expense['description'] = iucto_expense['description']
        
        # Payment info
        is_paid = iucto_expense.get('paid', False)
        paid_date = iucto_expense.get('paid_date')
        
        return fakturoid_expense, is_paid, paid_date
    
    def _map_line_items(self, iucto_items: List[Dict]) -> List[Dict]:
        """Map line items from iÚčto to Fakturoid format.
        
        Args:
            iucto_items: List of line items from iÚčto
            
        Returns:
            List of line items in Fakturoid format
        """
        lines = []
        
        for item in iucto_items:
            line = {
                'name': item.get('name', item.get('description', 'Item')),
                'quantity': str(item.get('quantity', 1)),
                'unit_price': str(item.get('unit_price', 0)),
                'vat_rate': item.get('vat_rate', 21)
            }
            lines.append(line)
        
        return lines
    
    def _get_or_create_subject(
        self,
        name: str,
        ico: Optional[str] = None,
        dic: Optional[str] = None,
        vat_number: Optional[str] = None,
        address: Optional[str] = None,
        street: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        country: Optional[str] = None,
        is_supplier: bool = True
    ) -> int:
        """Get or create subject (customer/supplier) in Fakturoid.
        
        Uses existing FakturoidClient.get_or_create_subject() method.
        
        Args:
            name: Company/person name
            ico: IČO (Czech company ID)
            dic: DIČ (Czech tax ID)
            vat_number: EU VAT number
            address: Complete address (fallback)
            street: Street and number
            city: City
            zip_code: Postal code
            country: Country code
            is_supplier: Whether this is a supplier (True) or customer (False)
            
        Returns:
            Subject ID in Fakturoid
        """
        subject = self.fakturoid.get_or_create_subject(
            supplier_name=name,
            supplier_ico=ico,
            supplier_dic=dic,
            supplier_vat_number=vat_number,
            supplier_address=address,
            supplier_street=street,
            supplier_city=city,
            supplier_zip=zip_code,
            supplier_country=country
        )
        
        return subject['id']

