"""Fakturoid API client for submitting invoices."""

import requests
import base64
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel
from .ai_extractor import InvoiceData


class FakturoidExpense(BaseModel):
    """Fakturoid expense format (received invoice)."""
    
    # Required fields
    subject_id: int  # Supplier ID in Fakturoid (REQUIRED!)
    lines: List[Dict[str, Any]]  # Line items (REQUIRED!)
    
    # Optional fields
    custom_id: Optional[str] = None
    number: Optional[str] = None  # Expense number
    original_number: Optional[str] = None  # Original invoice number
    variable_symbol: Optional[str] = None
    document_type: str = "invoice"  # invoice, bill, other
    issued_on: Optional[str] = None  # Issue date (YYYY-MM-DD)
    taxable_fulfillment_due: Optional[str] = None  # Chargeable event date
    received_on: Optional[str] = None  # When you received the expense
    due_on: Optional[str] = None  # Due date (YYYY-MM-DD)
    description: Optional[str] = None
    private_note: Optional[str] = None
    currency: str = "CZK"
    tags: Optional[List[str]] = None
    
    # Payment info
    bank_account: Optional[str] = None
    iban: Optional[str] = None
    swift_bic: Optional[str] = None


class FakturoidSubject(BaseModel):
    """Fakturoid subject (supplier/customer) format."""
    
    name: str  # Company name (REQUIRED!)
    
    # Optional fields
    street: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    country: str = "CZ"
    registration_no: Optional[str] = None  # IČO
    vat_no: Optional[str] = None  # DIČ
    email: Optional[str] = None
    phone: Optional[str] = None


class FakturoidClient:
    """Client for interacting with Fakturoid API."""
    
    def __init__(
        self,
        config_or_client_id,
        client_secret: str = None,
        account_slug: str = None,
        base_url: str = "https://app.fakturoid.cz/api/v3",
        user_agent: str = "Fakturoid Invoice Processor (info@example.com)"
    ):
        """Initialize Fakturoid client with OAuth 2.0 Client Credentials Flow.
        
        Args:
            config_or_client_id: Either a Config object or Client ID string
            client_secret: Client Secret (if Client ID provided directly)
            account_slug: Account slug (if Client ID provided directly)
            base_url: API base URL
            user_agent: User agent string
        """
        # Support both config object and direct parameters
        if hasattr(config_or_client_id, 'fakturoid'):
            # It's a config object
            self.client_id = config_or_client_id.fakturoid.email  # Will change to client_id in config
            self.client_secret = config_or_client_id.fakturoid.api_key  # Will change to client_secret
            self.account_slug = config_or_client_id.fakturoid.account_slug
            self.base_url = config_or_client_id.fakturoid.base_url
        else:
            # Direct parameters
            self.client_id = config_or_client_id
            self.client_secret = client_secret
            self.account_slug = account_slug
            self.base_url = base_url
        
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': self.user_agent
        })
        
        # OAuth 2.0 token management
        self.access_token = None
        self.token_expires_at = None
        
        # Get initial access token
        self._refresh_access_token()
    
    def _refresh_access_token(self):
        """Obtain new access token using OAuth 2.0 Client Credentials Flow.
        
        See: https://www.fakturoid.cz/api/v3/authorization#client-credentials-flow
        """
        # Create Basic Auth header with client_id:client_secret
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': self.user_agent
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(
            f"{self.base_url}/oauth/token",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        # Token expires in 7200 seconds (2 hours), refresh 5 minutes before expiry
        expires_in = token_data.get('expires_in', 7200)
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
        
        # Update session with new token
        self.session.headers.update({
            'Authorization': f"Bearer {self.access_token}"
        })
    
    def _ensure_token_valid(self):
        """Check if token is still valid and refresh if needed."""
        if not self.access_token or datetime.now() >= self.token_expires_at:
            self._refresh_access_token()
    
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
            self._ensure_token_valid()
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
        self._ensure_token_valid()
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
        self._ensure_token_valid()
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
        self._ensure_token_valid()
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
        self._ensure_token_valid()
        url = self._get_url("invoices.json")
        response = self.session.post(url, json=invoice_data)
        response.raise_for_status()
        return response.json()
    
    def list_expense_invoices(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List expense invoices (received invoices).
        
        Args:
            limit: Maximum number of invoices to return
            
        Returns:
            List of expense invoices
        """
        self._ensure_token_valid()
        url = self._get_url("expenses.json")
        params = {'per_page': min(limit, 100)}
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def create_expense_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an expense invoice (received invoice).
        
        Args:
            invoice_data: Invoice data
            
        Returns:
            Created expense invoice
        """
        self._ensure_token_valid()
        url = self._get_url("expenses.json")
        response = self.session.post(url, json=invoice_data)
        response.raise_for_status()
        return response.json()
    
    def get_or_create_subject(
        self,
        supplier_name: str,
        supplier_ico: Optional[str] = None,
        supplier_dic: Optional[str] = None,
        supplier_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get existing subject or create new one.
        
        Args:
            supplier_name: Supplier company name
            supplier_ico: IČO (company ID)
            supplier_dic: DIČ (tax ID)
            supplier_address: Address
            
        Returns:
            Subject dictionary with 'id'
        """
        # Try to find existing subject by name
        subject = self.find_subject_by_name(supplier_name)
        if subject:
            return subject
        
        # Create new subject
        subject_data = FakturoidSubject(
            name=supplier_name,
            registration_no=supplier_ico,
            vat_no=supplier_dic,
            street=supplier_address
        )
        
        return self.create_subject(subject_data.model_dump(exclude_none=True))
    
    def convert_extracted_to_expense(
        self,
        invoice_data: InvoiceData,
        auto_create_subject: bool = True
    ) -> Tuple[int, FakturoidExpense]:
        """Convert extracted invoice data to Fakturoid expense format.
        
        Args:
            invoice_data: Extracted invoice data
            auto_create_subject: Whether to auto-create subject if not found
            
        Returns:
            Tuple of (subject_id, FakturoidExpense)
        """
        # Get or create subject
        subject_id = None
        if invoice_data.supplier_name:
            if auto_create_subject:
                subject = self.get_or_create_subject(
                    supplier_name=invoice_data.supplier_name,
                    supplier_ico=invoice_data.supplier_ico,
                    supplier_dic=invoice_data.supplier_dic,
                    supplier_address=invoice_data.supplier_address
                )
                subject_id = subject['id']
            else:
                subject = self.find_subject_by_name(invoice_data.supplier_name)
                if subject:
                    subject_id = subject['id']
        
        if not subject_id:
            raise ValueError(f"Subject not found for supplier: {invoice_data.supplier_name}")
        
        # Prepare line items
        lines = []
        if invoice_data.line_items:
            for item in invoice_data.line_items:
                lines.append({
                    'name': item.get('description', ''),
                    'quantity': str(item.get('quantity', 1)),
                    'unit_price': str(item.get('unit_price', 0)),
                    'vat_rate': item.get('vat_rate', 21)  # Default Czech VAT
                })
        else:
            # Create a single line item with total
            # Calculate price without VAT (assuming 21% VAT included)
            total = float(invoice_data.total_amount)
            price_without_vat = total / 1.21
            
            lines.append({
                'name': invoice_data.notes or f'Invoice {invoice_data.invoice_number}',
                'quantity': '1.0',
                'unit_price': str(round(price_without_vat, 2)),
                'vat_rate': 21
            })
        
        fakturoid_expense = FakturoidExpense(
            subject_id=subject_id,
            lines=lines,
            original_number=invoice_data.invoice_number,
            variable_symbol=invoice_data.variable_symbol,
            issued_on=invoice_data.issue_date,
            due_on=invoice_data.due_date,
            received_on=invoice_data.issue_date,  # Default to issue date
            currency=invoice_data.currency or "CZK",
            description=invoice_data.notes,
            document_type="invoice"
        )
        
        return subject_id, fakturoid_expense
    
    def submit_expense(
        self,
        invoice_data: InvoiceData,
        auto_create_subject: bool = True
    ) -> Dict[str, Any]:
        """Submit extracted invoice as expense to Fakturoid.
        
        Args:
            invoice_data: Extracted invoice data
            auto_create_subject: Whether to auto-create subject if not found
            
        Returns:
            Created expense from Fakturoid
        """
        subject_id, fakturoid_expense = self.convert_extracted_to_expense(
            invoice_data,
            auto_create_subject=auto_create_subject
        )
        
        return self.create_expense_invoice(fakturoid_expense.model_dump(exclude_none=True))

