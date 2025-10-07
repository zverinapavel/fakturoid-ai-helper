"""Fakturoid API client for submitting invoices."""

import requests
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from .ai_extractor import InvoiceData


class FakturoidInvoice(BaseModel):
    """Fakturoid invoice format."""
    
    subject_id: Optional[int] = None  # Customer ID in Fakturoid
    number: Optional[str] = None  # Invoice number
    issued_on: str  # Issue date (YYYY-MM-DD)
    due_on: Optional[str] = None  # Due date (YYYY-MM-DD)
    currency: str = "CZK"
    
    # Lines
    lines: List[Dict[str, Any]] = []
    
    # Optional fields
    variable_symbol: Optional[str] = None
    note: Optional[str] = None
    
    # Subject (supplier) information for new subjects
    subject_name: Optional[str] = None
    subject_street: Optional[str] = None
    subject_city: Optional[str] = None
    subject_zip: Optional[str] = None
    subject_registration_no: Optional[str] = None  # IČO
    subject_vat_no: Optional[str] = None  # DIČ


class FakturoidClient:
    """Client for interacting with Fakturoid API."""
    
    def __init__(
        self,
        email: str,
        api_key: str,
        account_slug: str,
        base_url: str = "https://app.fakturoid.cz/api/v3"
    ):
        """Initialize Fakturoid client.
        
        Args:
            email: Fakturoid account email
            api_key: Fakturoid API key
            account_slug: Account slug (subdomain)
            base_url: API base URL
        """
        self.email = email
        self.api_key = api_key
        self.account_slug = account_slug
        self.base_url = base_url
        self.session = requests.Session()
        self.session.auth = (email, api_key)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Fakturoid Invoice Processor (pavel@example.com)'
        })
    
    def _get_url(self, endpoint: str) -> str:
        """Construct full API URL.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Full URL
        """
        return f"{self.base_url}/accounts/{self.account_slug}/{endpoint}"
    
    def test_connection(self) -> bool:
        """Test API connection.
        
        Returns:
            True if connection successful
        """
        try:
            url = self._get_url("account.json")
            response = self.session.get(url)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information.
        
        Returns:
            Account info dictionary
        """
        url = self._get_url("account.json")
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def list_subjects(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all subjects (customers/suppliers).
        
        Args:
            since: ISO 8601 date to filter subjects modified since
            
        Returns:
            List of subjects
        """
        url = self._get_url("subjects.json")
        params = {}
        if since:
            params['since'] = since
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def find_subject_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find subject by name.
        
        Args:
            name: Subject name to search for
            
        Returns:
            Subject dictionary or None if not found
        """
        subjects = self.list_subjects()
        for subject in subjects:
            if subject.get('name', '').lower() == name.lower():
                return subject
        return None
    
    def create_subject(self, subject_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new subject.
        
        Args:
            subject_data: Subject data
            
        Returns:
            Created subject
        """
        url = self._get_url("subjects.json")
        response = self.session.post(url, json=subject_data)
        response.raise_for_status()
        return response.json()
    
    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an invoice.
        
        Args:
            invoice_data: Invoice data
            
        Returns:
            Created invoice
        """
        url = self._get_url("invoices.json")
        response = self.session.post(url, json=invoice_data)
        response.raise_for_status()
        return response.json()
    
    def convert_extracted_to_fakturoid(
        self,
        invoice_data: InvoiceData,
        auto_create_subject: bool = True
    ) -> FakturoidInvoice:
        """Convert extracted invoice data to Fakturoid format.
        
        Args:
            invoice_data: Extracted invoice data
            auto_create_subject: Whether to auto-create subject if not found
            
        Returns:
            Fakturoid invoice format
        """
        # Try to find existing subject
        subject_id = None
        if invoice_data.supplier_name:
            subject = self.find_subject_by_name(invoice_data.supplier_name)
            if subject:
                subject_id = subject['id']
        
        # Prepare line items
        lines = []
        if invoice_data.line_items:
            for item in invoice_data.line_items:
                lines.append({
                    'name': item.get('description', ''),
                    'quantity': item.get('quantity', 1),
                    'unit_price': item.get('unit_price', 0),
                    'vat_rate': item.get('vat_rate', 21)  # Default Czech VAT
                })
        else:
            # Create a single line item with total
            lines.append({
                'name': invoice_data.notes or 'Invoice',
                'quantity': 1,
                'unit_price': invoice_data.total_amount,
                'vat_rate': 0  # Included in total
            })
        
        fakturoid_invoice = FakturoidInvoice(
            subject_id=subject_id,
            number=invoice_data.invoice_number,
            issued_on=invoice_data.issue_date,
            due_on=invoice_data.due_date,
            currency=invoice_data.currency or "CZK",
            lines=lines,
            variable_symbol=invoice_data.variable_symbol,
            note=invoice_data.notes
        )
        
        # If subject not found and auto-create enabled, add subject info
        if not subject_id and auto_create_subject:
            fakturoid_invoice.subject_name = invoice_data.supplier_name
            fakturoid_invoice.subject_registration_no = invoice_data.supplier_ico
            fakturoid_invoice.subject_vat_no = invoice_data.supplier_dic
            
            # Parse address if available
            if invoice_data.supplier_address:
                # Basic address parsing - you may want to improve this
                fakturoid_invoice.subject_street = invoice_data.supplier_address
        
        return fakturoid_invoice
    
    def submit_invoice(
        self,
        invoice_data: InvoiceData,
        auto_create_subject: bool = True
    ) -> Dict[str, Any]:
        """Submit extracted invoice to Fakturoid.
        
        Args:
            invoice_data: Extracted invoice data
            auto_create_subject: Whether to auto-create subject if not found
            
        Returns:
            Created invoice from Fakturoid
        """
        fakturoid_invoice = self.convert_extracted_to_fakturoid(
            invoice_data,
            auto_create_subject=auto_create_subject
        )
        
        return self.create_invoice(fakturoid_invoice.model_dump(exclude_none=True))

