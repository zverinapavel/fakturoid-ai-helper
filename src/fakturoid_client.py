"""Fakturoid API client for submitting invoices."""

import requests
import base64
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel
from .ai_extractor import InvoiceData
import re


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
    
    def find_subject_by_ico(self, ico: str) -> Optional[Dict[str, Any]]:
        """Find subject by IČO (company registration number).
        
        Args:
            ico: IČO (company ID)
            
        Returns:
            Subject dictionary or None if not found
        """
        if not ico:
            return None
        
        # Clean IČO (remove spaces, dashes)
        ico_clean = re.sub(r'[^\d]', '', str(ico))
        
        subjects = self.list_subjects()
        for subject in subjects:
            subject_ico = subject.get('registration_no')
            if subject_ico:  # Only process if not None
                subject_ico_clean = re.sub(r'[^\d]', '', str(subject_ico))
                if subject_ico_clean == ico_clean:
                    return subject
        return None
    
    def get_company_from_ares(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get company information from ARES (Czech business register).
        
        Args:
            ico: IČO (company registration number)
            
        Returns:
            Dictionary with company data or None if not found
        """
        if not ico:
            return None
        
        # Clean IČO
        ico_clean = re.sub(r'[^\d]', '', str(ico))
        
        try:
            # ARES API endpoint
            url = f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico_clean}"
            
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # Extract company information
            company_name = data.get('obchodniJmeno', '')
            
            # Get address
            sidlo = data.get('sidlo', {})
            address_parts = []
            
            # Street and number
            ulice = sidlo.get('nazevUlice', '')
            cislo_domovni = sidlo.get('cisloDomovni', '')
            cislo_orientacni = sidlo.get('cisloOrientacni', '')
            
            if ulice:
                street = ulice
                if cislo_domovni:
                    street += f" {cislo_domovni}"
                if cislo_orientacni:
                    street += f"/{cislo_orientacni}"
                address_parts.append(street)
            
            # City and ZIP
            obec = sidlo.get('nazevObce', '')
            psc = sidlo.get('psc', '')
            
            # Get DIC (VAT number)
            dic = data.get('dic', '')
            
            return {
                'name': company_name,
                'street': address_parts[0] if address_parts else '',
                'city': obec,
                'zip': str(psc) if psc else '',
                'country': 'CZ',
                'registration_no': ico_clean,
                'vat_no': dic
            }
            
        except Exception as e:
            print(f"Warning: Failed to fetch data from ARES for IČO {ico}: {e}")
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
        
        # Debug: print what we're sending
        print(f"\n🔍 DEBUG - Sending to Fakturoid API:")
        import json
        print(json.dumps(invoice_data, indent=2, ensure_ascii=False))
        
        response = self.session.post(url, json=invoice_data)
        
        # If error, print response details
        if response.status_code != 201:
            print(f"\n❌ API Error Response:")
            print(f"Status: {response.status_code}")
            try:
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            except:
                print(response.text)
        
        response.raise_for_status()
        return response.json()
    
    def get_or_create_subject(
        self,
        supplier_name: str,
        supplier_ico: Optional[str] = None,
        supplier_dic: Optional[str] = None,
        supplier_vat_number: Optional[str] = None,
        supplier_address: Optional[str] = None,
        supplier_street: Optional[str] = None,
        supplier_city: Optional[str] = None,
        supplier_zip: Optional[str] = None,
        supplier_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get existing subject or create new one.
        
        For Czech companies (with IČO), tries to fetch complete data from ARES.
        For foreign companies, uses detailed address fields.
        
        Args:
            supplier_name: Supplier company name
            supplier_ico: IČO (Czech company ID)
            supplier_dic: DIČ (Czech tax ID)
            supplier_vat_number: EU VAT number (for foreign companies)
            supplier_address: Complete address (fallback if structured fields not available)
            supplier_street: Street and number
            supplier_city: City
            supplier_zip: Postal code
            supplier_country: Country code (e.g., CZ, DE, US)
            
        Returns:
            Subject dictionary with 'id'
        """
        # Try to find existing subject by IČO first (more reliable)
        if supplier_ico:
            subject = self.find_subject_by_ico(supplier_ico)
            if subject:
                print(f"✓ Found existing subject by IČO: {subject.get('name')}")
                return subject
        
        # Try to find by name
        subject = self.find_subject_by_name(supplier_name)
        if subject:
            print(f"✓ Found existing subject by name: {subject.get('name')}")
            return subject
        
        # Subject not found - create new one
        print(f"⚙ Creating new subject: {supplier_name}")
        
        # For Czech companies, try to get data from ARES
        subject_data_dict = None
        if supplier_ico:
            print(f"  → Fetching data from ARES for IČO: {supplier_ico}")
            ares_data = self.get_company_from_ares(supplier_ico)
            if ares_data:
                print(f"  ✓ Got data from ARES: {ares_data['name']}")
                subject_data_dict = ares_data
            else:
                print(f"  ⚠ ARES lookup failed, using extracted data")
        
        # If ARES failed or no IČO, use extracted data
        if not subject_data_dict:
            # Determine VAT number (prefer supplier_vat_number for foreign, supplier_dic for Czech)
            vat_no = supplier_vat_number or supplier_dic
            
            # Use structured address if available, otherwise fallback to supplier_address
            street = supplier_street or supplier_address
            
            # Determine country (default to CZ if not specified and has IČO)
            country = supplier_country
            if not country:
                country = "CZ" if supplier_ico else None
            
            subject_data = FakturoidSubject(
                name=supplier_name,
                registration_no=supplier_ico,
                vat_no=vat_no,
                street=street,
                city=supplier_city,
                zip=supplier_zip,
                country=country or "CZ"
            )
            subject_data_dict = subject_data.model_dump(exclude_none=True)
        
        created_subject = self.create_subject(subject_data_dict)
        print(f"  ✓ Subject created with ID: {created_subject.get('id')}")
        return created_subject
    
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
                    supplier_vat_number=invoice_data.supplier_vat_number,
                    supplier_address=invoice_data.supplier_address,
                    supplier_street=invoice_data.supplier_street,
                    supplier_city=invoice_data.supplier_city,
                    supplier_zip=invoice_data.supplier_zip,
                    supplier_country=invoice_data.supplier_country
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
        if invoice_data.line_items and len(invoice_data.line_items) > 0:
            # Check if line items have valid prices
            has_valid_prices = any(
                item.get('unit_price') and float(item.get('unit_price', 0)) > 0 
                for item in invoice_data.line_items
            )
            
            if has_valid_prices:
                # Use extracted line items
                for item in invoice_data.line_items:
                    lines.append({
                        'name': item.get('description', ''),
                        'quantity': str(item.get('quantity', 1)),
                        'unit_price': str(item.get('unit_price', 0)),
                        'vat_rate': item.get('vat_rate', 21)  # Default Czech VAT
                    })
            else:
                # Line items exist but without prices - use total as fallback
                lines = None
        else:
            # No line items extracted
            lines = None
        
        if not lines:
            # Create a single line item with total
            # Calculate price without VAT (assuming 21% VAT included)
            total = float(invoice_data.total_amount)
            price_without_vat = total / 1.21
            
            lines = [{
                'name': invoice_data.notes or f'Invoice {invoice_data.invoice_number}',
                'quantity': '1.0',
                'unit_price': str(round(price_without_vat, 2)),
                'vat_rate': 21
            }]
        
        # Normalize currency (handle common variations)
        currency = invoice_data.currency or "CZK"
        currency_map = {
            'Kc': 'CZK',
            'Kč': 'CZK',
            'KC': 'CZK',
            'kc': 'CZK',
            'kč': 'CZK',
            'czk': 'CZK'
        }
        normalized_currency = currency_map.get(currency, currency.upper() if currency else "CZK")
        
        # Determine taxable_fulfillment_due (DUZP)
        # If not extracted from invoice, default to received_on date (same as issue_date)
        taxable_fulfillment_due = invoice_data.taxable_fulfillment_due
        if not taxable_fulfillment_due:
            taxable_fulfillment_due = invoice_data.issue_date  # Default to issue date (same as received_on)
        
        fakturoid_expense = FakturoidExpense(
            subject_id=subject_id,
            lines=lines,
            original_number=invoice_data.invoice_number,
            variable_symbol=invoice_data.variable_symbol,
            issued_on=invoice_data.issue_date,
            taxable_fulfillment_due=taxable_fulfillment_due,  # Date of chargeable event (DUZP)
            due_on=invoice_data.due_date,
            received_on=invoice_data.issue_date,  # Default to issue date
            currency=normalized_currency,
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

