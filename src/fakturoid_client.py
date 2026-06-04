"""Fakturoid API client for submitting invoices."""

import requests
import base64
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel
try:
    from src.ai_extractor import InvoiceData
except ImportError:
    from ai_extractor import InvoiceData
import re


class AmountValidationError(ValueError):
    """Raised when extracted invoice total does not match Fakturoid line calculation."""


# At least 1 CZK or 1.5 % — covers rounding and net vs gross label mix-ups.
_AMOUNT_ABS_TOLERANCE_MIN = 1.0
_AMOUNT_REL_TOLERANCE = 0.015

_REF_LABEL_PRIORITY = {
    "total_amount (celkem)": 0,
    "suma položek (total)": 1,
    "suma položek (množství × cena)": 2,
    "základ (total − DPH)": 3,
    "tax_amount": 4,
}

_ROUNDING_LINE_NAME = "Zaokrouhlení"
# Max gross gap auto-fixed by a rounding line (haléřové rozdíly na víceřádkových fakturách).
_MAX_AUTO_ROUNDING_GAP = 2.0


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
    vat_price_mode: Optional[str] = None  # without_vat | from_total_with_vat
    
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
        client_secret: Optional[str] = None,
        account_slug: Optional[str] = None,
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
        self._account_vat_price_mode: Optional[str] = None
        
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
        if (
            not self.access_token
            or self.token_expires_at is None
            or datetime.now() >= self.token_expires_at
        ):
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

    def _paginate_collection(
        self,
        endpoint: str,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all pages (40 items per page) for a collection endpoint."""
        self._ensure_token_valid()
        url = self._get_url(endpoint)
        all_items: List[Dict[str, Any]] = []
        page = 1
        while True:
            params: Dict[str, Any] = dict(extra_params or {})
            params["page"] = page
            response = self.session.get(url, params=params)
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            all_items.extend(batch)
            if len(batch) < 40:
                break
            page += 1
        return all_items

    def list_todos(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all todos (paginated)."""
        extra: Dict[str, Any] = {}
        if since:
            extra["since"] = since
        return self._paginate_collection("todos.json", extra)

    def list_expenses(
        self,
        status: Optional[str] = None,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List expenses with optional status filter (e.g. open, overdue, paid)."""
        extra: Dict[str, Any] = {}
        if status:
            extra["status"] = status
        if since:
            extra["since"] = since
        return self._paginate_collection("expenses.json", extra)

    def list_invoices(
        self,
        status: Optional[str] = None,
        since: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List invoices with optional status filter (e.g. open, overdue, paid)."""
        extra: Dict[str, Any] = {}
        if status:
            extra["status"] = status
        if since:
            extra["since"] = since
        if document_type:
            extra["document_type"] = document_type
        return self._paginate_collection("invoices.json", extra)

    def list_unpaid_expenses(self) -> List[Dict[str, Any]]:
        """Return expenses that are not paid (open + overdue), deduplicated by id."""
        by_id: Dict[int, Dict[str, Any]] = {}
        for st in ("open", "overdue"):
            for e in self.list_expenses(status=st):
                by_id[e["id"]] = e
        return list(by_id.values())

    def list_unpaid_invoices(self) -> List[Dict[str, Any]]:
        """Return invoices that are not paid (open + sent + overdue), deduplicated by id."""
        by_id: Dict[int, Dict[str, Any]] = {}
        for st in ("open", "sent", "overdue"):
            for inv in self.list_invoices(status=st):
                by_id[inv["id"]] = inv
        return list(by_id.values())

    def create_expense_payment(
        self,
        expense_id: int,
        payment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a payment on an expense (marks paid / partial).

        See: https://www.fakturoid.cz/api/v3/expense-payments
        """
        self._ensure_token_valid()
        url = self._get_url(f"expenses/{expense_id}/payments.json")
        response = self.session.post(url, json=payment)
        response.raise_for_status()
        return response.json()

    def create_invoice_payment(
        self,
        invoice_id: int,
        payment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a payment on an invoice (marks paid / partial).

        See: https://www.fakturoid.cz/api/v3/invoice-payments
        """
        self._ensure_token_valid()
        url = self._get_url(f"invoices/{invoice_id}/payments.json")
        response = self.session.post(url, json=payment)
        response.raise_for_status()
        return response.json()

    def toggle_todo_completion(self, todo_id: int) -> Dict[str, Any]:
        """Mark a todo as completed (e.g. after pairing a payment)."""
        self._ensure_token_valid()
        url = self._get_url(f"todos/{todo_id}/toggle_completion.json")
        response = self.session.post(url)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}

    def list_subjects(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all subjects (customers/suppliers).
        
        Note: Fakturoid API may paginate results. This method fetches all pages.
        
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
        
        all_subjects = []
        page = 1
        per_page = 40  # Fakturoid default is 40 records per page according to docs
        
        while True:
            params['page'] = page
            # Note: per_page might not be supported, but we'll try it
            # If it fails, we'll use default 40 per page
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            subjects = response.json()
            if not subjects:  # Empty list means no more pages
                break
            
            all_subjects.extend(subjects)
            
            # If we got fewer than per_page (or default 40), we're on the last page
            if len(subjects) < 40:
                break
            
            page += 1
        
        return all_subjects
    
    def search_subjects(self, query: str) -> List[Dict[str, Any]]:
        """Search subjects using Fakturoid search endpoint.
        
        Searches in: name, full_name, email, email_copy, registration_no, vat_no, private_note
        
        Args:
            query: Search query string
            
        Returns:
            List of matching subjects
        """
        self._ensure_token_valid()
        url = self._get_url("subjects/search.json")
        params: Dict[str, Any] = {'query': query}
        
        all_results = []
        page = 1
        
        while True:
            params['page'] = page  # int is valid for requests query params
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            results = response.json()
            if not results:  # Empty list means no more pages
                break
            
            all_results.extend(results)
            
            # If we got fewer than 40 (default page size), we're on the last page
            if len(results) < 40:
                break
            
            page += 1
        
        return all_results
    
    def find_subject_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find subject by name (case-insensitive, partial match).
        
        Args:
            name: Subject name to search for
            
        Returns:
            Subject dictionary or None if not found
        """
        subjects = self.list_subjects()
        name_lower = name.lower()
        
        # First try exact match
        for subject in subjects:
            if subject.get('name', '').lower() == name_lower:
                return subject
        
        # Then try partial match (for cases like "Google Cloud" vs "Google Cloud EMEA Limited")
        for subject in subjects:
            subject_name = subject.get('name', '').lower()
            if name_lower in subject_name or subject_name in name_lower:
                return subject
        
        return None
    
    def find_subject_by_vat(self, vat_no: str) -> Optional[Dict[str, Any]]:
        """Find subject by VAT number.
        
        Uses Fakturoid search endpoint which searches in vat_no field.
        
        Args:
            vat_no: VAT number
            
        Returns:
            Subject dictionary or None if not found
        """
        if not vat_no:
            return None
        
        # Clean VAT number (remove spaces, dashes)
        vat_clean = re.sub(r'[\s\-]', '', str(vat_no)).upper()
        
        print(f"  🔍 Searching for subject with VAT/DIČ: {vat_clean}")
        
        # Use search endpoint - it searches in vat_no field
        # Try both cleaned and original format
        search_queries = [vat_clean]
        if str(vat_no) != vat_clean:
            search_queries.append(str(vat_no))
        
        for query in search_queries:
            print(f"  🔍 Trying search query: '{query}'")
            results = self.search_subjects(query)
            
            # Check if any result matches our VAT exactly
            for subject in results:
                subject_vat = subject.get('vat_no')
                if subject_vat:
                    subject_vat_clean = re.sub(r'[\s\-]', '', str(subject_vat)).upper()
                    if subject_vat_clean == vat_clean:
                        print(f"  ✓ Match found: {subject.get('name')} (ID: {subject.get('id')}, VAT: {subject_vat})")
                        return subject
        
        print(f"  ✗ No subject found with VAT/DIČ: {vat_clean}")
        return None
    
    def find_subject_by_ico(self, ico: str) -> Optional[Dict[str, Any]]:
        """Find subject by IČO (company registration number).
        
        Uses Fakturoid search endpoint which searches in registration_no field.
        
        Args:
            ico: IČO (company ID)
            
        Returns:
            Subject dictionary or None if not found
        """
        if not ico:
            return None
        
        # Clean IČO (remove spaces, dashes, keep only digits)
        ico_clean = re.sub(r'[^\d]', '', str(ico))
        
        if not ico_clean:
            return None
        
        print(f"  🔍 Searching for subject with IČO: {ico_clean}")
        
        # Use search endpoint - it searches in registration_no field
        # Try both with and without leading zeros
        search_queries = [ico_clean]
        
        # Also try the original IČO (might have prefix or formatting)
        if str(ico) != ico_clean:
            search_queries.append(str(ico))
        
        # Try searching with leading zero removed (in case stored without it)
        if ico_clean.startswith('0'):
            search_queries.append(ico_clean.lstrip('0'))
        
        for query in search_queries:
            print(f"  🔍 Trying search query: '{query}'")
            results = self.search_subjects(query)
            
            # Check if any result matches our IČO exactly
            for subject in results:
                subject_ico = subject.get('registration_no')
                if subject_ico:
                    subject_ico_clean = re.sub(r'[^\d]', '', str(subject_ico))
                    if subject_ico_clean == ico_clean:
                        print(f"  ✓ Match found: {subject.get('name')} (ID: {subject.get('id')}, IČO: {subject_ico})")
                        return subject
            
            # If we found results but none matched exactly, show them for debugging
            if results:
                print(f"  ⚠ Found {len(results)} results for '{query}', but IČO doesn't match exactly:")
                for subject in results[:3]:
                    subject_ico = subject.get('registration_no', 'N/A')
                    print(f"     - {subject.get('name')}: IČO='{subject_ico}'")
        
        print(f"  ✗ No subject found with IČO: {ico_clean}")
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
        
        # Debug: print what we're sending
        print(f"\n🔍 DEBUG - Creating subject:")
        import json
        print(json.dumps(subject_data, indent=2, ensure_ascii=False))
        
        response = self.session.post(url, json=subject_data)
        
        # If error, print response details
        if response.status_code != 201:
            print(f"\n❌ API Error Response:")
            print(f"Status: {response.status_code}")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                print(response.text)
        
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
    
    def _matches_subject_identifiers(
        self,
        subject: Dict[str, Any],
        supplier_ico: Optional[str] = None,
        supplier_dic: Optional[str] = None,
        supplier_vat_number: Optional[str] = None
    ) -> bool:
        """Check if subject matches given IČO or VAT identifiers.
        
        Returns True if:
        - At least one identifier (IČO or VAT) matches
        - OR no identifiers are provided (name-only search)
        
        Returns False if:
        - We have identifiers but none of them match
        
        Args:
            subject: Subject dictionary from Fakturoid
            supplier_ico: IČO to match
            supplier_dic: DIČ to match
            supplier_vat_number: VAT number to match
            
        Returns:
            True if identifiers match, False otherwise
        """
        vat_to_check = supplier_vat_number or supplier_dic
        has_identifiers = bool(supplier_ico or vat_to_check)
        
        # If no identifiers provided, consider it a match (name-only search)
        if not has_identifiers:
            return True
        
        # Check IČO match
        ico_matches = False
        if supplier_ico:
            subject_ico = subject.get('registration_no')
            if subject_ico:
                ico_clean = re.sub(r'[^\d]', '', str(supplier_ico))
                subject_ico_clean = re.sub(r'[^\d]', '', str(subject_ico))
                ico_matches = (ico_clean == subject_ico_clean)
        
        # Check VAT/DIČ match
        vat_matches = False
        if vat_to_check:
            subject_vat = subject.get('vat_no')
            if subject_vat:
                vat_clean = re.sub(r'[\s\-]', '', str(vat_to_check)).upper()
                subject_vat_clean = re.sub(r'[\s\-]', '', str(subject_vat)).upper()
                vat_matches = (vat_clean == subject_vat_clean)
        
        # Return True if at least one identifier matches
        return ico_matches or vat_matches
    
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
        
        Search priority:
        1. By IČO (for Czech companies)
        2. By VAT/DIČ (for foreign companies or Czech companies with DIČ)
        3. By name (with verification that IČO/VAT matches if provided)
        
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
        print(f"\n🔍 Looking for existing subject:")
        print(f"   Name: {supplier_name}")
        if supplier_ico:
            print(f"   IČO: {supplier_ico}")
        if supplier_dic:
            print(f"   DIČ: {supplier_dic}")
        if supplier_vat_number:
            print(f"   VAT: {supplier_vat_number}")
        
        # Try to find existing subject by IČO first (most reliable for Czech companies)
        if supplier_ico:
            subject = self.find_subject_by_ico(supplier_ico)
            if subject:
                print(f"✓ Found existing subject by IČO: {subject.get('name')} (ID: {subject.get('id')})")
                return subject
        
        # Try to find by VAT number (for foreign companies or Czech companies with DIČ)
        vat_to_check = supplier_vat_number or supplier_dic
        if vat_to_check:
            subject = self.find_subject_by_vat(vat_to_check)
            if subject:
                print(f"✓ Found existing subject by VAT/DIČ: {subject.get('name')} (ID: {subject.get('id')})")
                return subject
        
        # Try to find by name, but verify IČO/VAT matches if provided
        subject = self.find_subject_by_name(supplier_name)
        if subject:
            # Debug: show what IČO/VAT the found subject has
            found_ico = subject.get('registration_no')
            found_vat = subject.get('vat_no')
            print(f"  🔍 Found subject by name: {subject.get('name')} (ID: {subject.get('id')})")
            if found_ico:
                print(f"     Has IČO: '{found_ico}' (cleaned: {re.sub(r'[^\d]', '', str(found_ico))})")
            if found_vat:
                print(f"     Has VAT/DIČ: '{found_vat}' (cleaned: {re.sub(r'[\s\-]', '', str(found_vat)).upper()})")
            
            # Verify that identifiers match (if we have them)
            if self._matches_subject_identifiers(subject, supplier_ico, supplier_dic, supplier_vat_number):
                print(f"✓ Found existing subject by name: {subject.get('name')} (ID: {subject.get('id')})")
                return subject
            else:
                # Found by name but IČO/VAT doesn't match - this is a different company
                print(f"⚠ Found subject with same name but different IČO/VAT, will create new subject")
        
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
                # Mark as supplier
                subject_data_dict['supplier'] = True
            else:
                print(f"  ⚠ ARES lookup failed, using extracted data")
        
        # If ARES failed or no IČO, use extracted data
        if not subject_data_dict:
            # Determine VAT number (prefer supplier_vat_number for foreign, supplier_dic for Czech)
            vat_no = supplier_vat_number or supplier_dic
            
            # Use structured address if available, otherwise fallback to supplier_address
            street = supplier_street or supplier_address
            
            # Determine country - normalize to ISO 2-letter code
            country = None
            if supplier_country:
                # Map common country names to ISO codes
                country_mapping = {
                    'ireland': 'IE',
                    'germany': 'DE',
                    'united kingdom': 'GB',
                    'uk': 'GB',
                    'france': 'FR',
                    'austria': 'AT',
                    'slovakia': 'SK',
                    'poland': 'PL',
                    'netherlands': 'NL',
                    'italy': 'IT',
                    'spain': 'ES',
                    'belgium': 'BE',
                    'denmark': 'DK',
                    'sweden': 'SE',
                    'finland': 'FI',
                    'czech republic': 'CZ',
                    'czechia': 'CZ',
                    'česko': 'CZ',
                    'česká republika': 'CZ',
                }
                
                country_lower = supplier_country.lower().strip()
                country = country_mapping.get(country_lower, supplier_country.upper())
                
                # Validate it's 2-letter code
                if len(country) > 2:
                    # Try to extract 2-letter code
                    country = None
            
            # If no country from extraction, try to detect from VAT number
            if not country and vat_no and len(vat_no) >= 2:
                vat_prefix = vat_no[:2].upper()
                # Common EU country codes
                if vat_prefix in ['DE', 'GB', 'FR', 'AT', 'SK', 'PL', 'NL', 'IT', 'ES', 'BE', 'IE', 'DK', 'SE', 'FI', 'CZ']:
                    country = vat_prefix
            
            # If has IČO, it's Czech
            if not country and supplier_ico:
                country = "CZ"
            
            # For foreign companies without clear country, don't default to CZ
            # Leave as None and it won't be sent to API
            
            # Build subject data - only include non-empty fields
            subject_data_dict = {
                'name': supplier_name,
                'supplier': True  # Mark as supplier (not customer)
            }
            
            # Add optional fields only if they have values
            if supplier_ico:
                subject_data_dict['registration_no'] = supplier_ico
            if vat_no:
                subject_data_dict['vat_no'] = vat_no
            if street:
                subject_data_dict['street'] = street
            if supplier_city:
                subject_data_dict['city'] = supplier_city
            if supplier_zip:
                subject_data_dict['zip'] = supplier_zip
            if country:
                subject_data_dict['country'] = country
        
        # Ensure supplier flag is set for ARES data too
        if subject_data_dict and 'supplier' not in subject_data_dict:
            subject_data_dict['supplier'] = True
        
        created_subject = self.create_subject(subject_data_dict)
        print(f"  ✓ Subject created with ID: {created_subject.get('id')} (marked as supplier)")
        return created_subject

    @staticmethod
    def _parse_percent_to_vat_rate(raw: Any) -> Optional[int]:
        """Parse a VAT percentage from extracted string or number."""
        if raw is None or raw == "":
            return None
        try:
            s = str(raw).strip().replace(",", ".").replace("%", "")
            if s == "":
                return None
            v = float(s)
            return int(round(v))
        except (TypeError, ValueError):
            return None

    def _line_item_declared_vat_rate(self, item: Dict[str, Any]) -> Optional[int]:
        """Read per-line VAT %% from common AI field names."""
        for key in (
            "vat_rate",
            "tax_rate",
            "tax_rate_percent",
            "vat_percent",
            "vat_percentage",
            "tax_percentage",
        ):
            if key not in item:
                continue
            parsed = self._parse_percent_to_vat_rate(item.get(key))
            if parsed is not None:
                return max(0, min(100, parsed))
        return None

    def _invoice_implies_zero_vat(self, invoice_data: InvoiceData) -> bool:
        """Heuristic: reverse charge, notes, or zero tax on the document."""
        if getattr(invoice_data, "reverse_charge", None) is True:
            return True
        notes = f"{invoice_data.notes or ''} "
        low = notes.lower()
        needles = (
            "reverse charge",
            "přenesená daňová",
            "prenesena danova",
            "tax to be paid on reverse",
            "reverse-charge",
            "autoliquidation",
        )
        if any(n in low for n in needles):
            return True
        if invoice_data.tax_amount is not None and abs(float(invoice_data.tax_amount)) < 0.005:
            return True
        return False

    def _default_vat_rate_when_line_unspecified(self, invoice_data: InvoiceData) -> int:
        """
        When AI omits vat_rate on a line, infer default for Fakturoid.
        Do not assume 21%% for foreign / reverse-charge invoices.
        """
        if self._invoice_implies_zero_vat(invoice_data):
            return 0
        cur = (invoice_data.currency or "CZK").upper()
        cz_domestic = cur == "CZK" and (
            (invoice_data.supplier_ico and str(invoice_data.supplier_ico).strip())
            or (
                invoice_data.supplier_dic
                and "cz" in str(invoice_data.supplier_dic).lower()
            )
        )
        if cz_domestic:
            return 21
        return 0

    def get_account_vat_price_mode(self) -> str:
        """Map account VAT setting to expense API vat_price_mode."""
        if self._account_vat_price_mode is not None:
            return self._account_vat_price_mode
        info = self.get_account_info()
        raw = (info.get("vat_price_mode") or "without_vat").lower()
        if raw in ("with_vat", "from_total_with_vat", "numerical_with_vat"):
            self._account_vat_price_mode = "from_total_with_vat"
        else:
            self._account_vat_price_mode = "without_vat"
        return self._account_vat_price_mode

    @staticmethod
    def _parse_line_quantity(raw: Any, default: float = 1.0) -> float:
        if raw is None or raw == "":
            return default
        try:
            return float(str(raw).replace(",", ".").strip())
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _line_qty_unit_vat(line: Dict[str, Any]) -> Tuple[float, float, int]:
        qty = FakturoidClient._parse_line_quantity(line.get("quantity"), 1.0)
        unit = float(str(line.get("unit_price", 0)).replace(",", "."))
        vat_rate = int(line.get("vat_rate") or 0)
        return qty, unit, vat_rate

    @staticmethod
    def _compute_line_total_with_vat(
        qty: float,
        unit_price: float,
        vat_rate: int,
        vat_price_mode: str,
        *,
        zero_vat: bool,
    ) -> float:
        """Mirror Fakturoid expense line total (price including VAT)."""
        if zero_vat or vat_rate <= 0:
            return round(qty * unit_price, 2)
        if vat_price_mode == "from_total_with_vat":
            return round(qty * unit_price, 2)
        net = qty * unit_price
        return round(net * (1 + vat_rate / 100.0), 2)

    @staticmethod
    def _compute_line_vat_amount(
        qty: float,
        unit_price: float,
        vat_rate: int,
        vat_price_mode: str,
        *,
        zero_vat: bool,
    ) -> float:
        if zero_vat or vat_rate <= 0:
            return 0.0
        gross = qty * unit_price
        if vat_price_mode == "from_total_with_vat":
            net = gross / (1 + vat_rate / 100.0)
            return round(gross - net, 2)
        net = gross
        return round(net * vat_rate / 100.0, 2)

    def _compute_document_total(
        self,
        lines: List[Dict[str, Any]],
        vat_price_mode: str,
        *,
        zero_vat: bool,
    ) -> float:
        total = 0.0
        for line in lines:
            qty, unit, vat_rate = self._line_qty_unit_vat(line)
            total += self._compute_line_total_with_vat(
                qty, unit, vat_rate, vat_price_mode, zero_vat=zero_vat
            )
        return round(total, 2)

    def _compute_document_vat(
        self,
        lines: List[Dict[str, Any]],
        vat_price_mode: str,
        *,
        zero_vat: bool,
    ) -> float:
        total_vat = 0.0
        for line in lines:
            qty, unit, vat_rate = self._line_qty_unit_vat(line)
            total_vat += self._compute_line_vat_amount(
                qty, unit, vat_rate, vat_price_mode, zero_vat=zero_vat
            )
        return round(total_vat, 2)

    @staticmethod
    def _compute_line_net(
        qty: float,
        unit_price: float,
        vat_rate: int,
        vat_price_mode: str,
        *,
        zero_vat: bool,
    ) -> float:
        if zero_vat or vat_rate <= 0:
            return round(qty * unit_price, 2)
        if vat_price_mode == "from_total_with_vat":
            gross = qty * unit_price
            return round(gross / (1 + vat_rate / 100.0), 2)
        return round(qty * unit_price, 2)

    def _compute_document_subtotal(
        self,
        lines: List[Dict[str, Any]],
        vat_price_mode: str,
        *,
        zero_vat: bool,
    ) -> float:
        total = 0.0
        for line in lines:
            qty, unit, vat_rate = self._line_qty_unit_vat(line)
            total += self._compute_line_net(
                qty, unit, vat_rate, vat_price_mode, zero_vat=zero_vat
            )
        return round(total, 2)

    def _compute_document_breakdown(
        self,
        lines: List[Dict[str, Any]],
        vat_price_mode: str,
        *,
        zero_vat: bool,
    ) -> Tuple[float, float, float]:
        """Return (tax_base/subtotal, vat, gross) from expense lines."""
        subtotal = self._compute_document_subtotal(
            lines, vat_price_mode, zero_vat=zero_vat
        )
        vat = self._compute_document_vat(lines, vat_price_mode, zero_vat=zero_vat)
        gross = round(subtotal + vat, 2)
        return subtotal, vat, gross

    @staticmethod
    def _line_is_rounding(name: str) -> bool:
        low = (name or "").lower()
        return "zaokrouhl" in low or low.strip() == "rounding"

    def _apply_rounding_line_if_needed(
        self,
        lines: List[Dict[str, Any]],
        invoice_data: InvoiceData,
        vat_price_mode: str,
        *,
        zero_vat: bool,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Ensure tax_base + VAT from lines matches invoice total_amount.

        If a small gap remains (typical per-line VAT rounding), append a 0% VAT line.
        """
        info: Dict[str, Any] = {
            "rounding_line_added": False,
            "rounding_gap": None,
            "subtotal": None,
            "vat_computed": None,
            "gross_computed": None,
            "invoice_total": None,
            "invoice_tax": None,
            "sum_base_plus_invoice_tax": None,
        }

        target_total = float(invoice_data.total_amount or 0)
        if target_total <= 0.01:
            return lines, info

        subtotal, vat, gross = self._compute_document_breakdown(
            lines, vat_price_mode, zero_vat=zero_vat
        )
        info.update(
            {
                "subtotal": subtotal,
                "vat_computed": vat,
                "gross_computed": gross,
                "invoice_total": round(target_total, 2),
            }
        )

        invoice_tax: Optional[float] = None
        if invoice_data.tax_amount is not None and float(invoice_data.tax_amount) > 0.01:
            invoice_tax = round(float(invoice_data.tax_amount), 2)
            info["invoice_tax"] = invoice_tax
            info["sum_base_plus_invoice_tax"] = round(subtotal + invoice_tax, 2)

        gap = round(target_total - gross, 2)
        info["rounding_gap"] = gap

        if abs(gap) <= 0.005:
            return lines, info

        if any(self._line_is_rounding(str(l.get("name") or "")) for l in lines):
            return lines, info

        if abs(gap) > _MAX_AUTO_ROUNDING_GAP:
            return lines, info

        rounding_line = {
            "name": _ROUNDING_LINE_NAME,
            "quantity": "1",
            "unit_price": str(gap),
            "vat_rate": 0,
        }
        new_lines = list(lines) + [rounding_line]
        info["rounding_line_added"] = True

        sub2, vat2, gross2 = self._compute_document_breakdown(
            new_lines, vat_price_mode, zero_vat=zero_vat
        )
        info["subtotal_after"] = sub2
        info["vat_computed_after"] = vat2
        info["gross_computed_after"] = round(sub2 + vat2, 2)

        return new_lines, info

    def _prepare_expense_lines(
        self, invoice_data: InvoiceData
    ) -> Tuple[List[Dict[str, Any]], bool, Dict[str, Any]]:
        """Build lines, pick VAT mode, apply rounding line if needed, validate."""
        lines, from_detailed = self._build_expense_lines(invoice_data)
        validation = self._validate_amounts_from_lines(
            invoice_data, lines, from_detailed
        )
        lines, rounding_info = self._apply_rounding_line_if_needed(
            lines,
            invoice_data,
            validation["vat_price_mode"],
            zero_vat=validation["zero_vat"],
        )
        validation["rounding"] = rounding_info
        if rounding_info.get("rounding_line_added"):
            print(
                f"  ℹ️  Přidán řádek {_ROUNDING_LINE_NAME}: "
                f"{rounding_info['rounding_gap']:+.2f} "
                f"(základ {rounding_info['subtotal']} + DPH {rounding_info['vat_computed']} "
                f"→ {rounding_info['gross_computed']}, faktura {rounding_info['invoice_total']})"
            )
            validation = self._validate_amounts_from_lines(
                invoice_data, lines, from_detailed
            )
            validation["rounding"] = rounding_info
        validation["lines"] = lines
        return lines, from_detailed, validation

    @staticmethod
    def _amount_tolerance(reference: float) -> float:
        ref = max(abs(reference), 1.0)
        return max(_AMOUNT_ABS_TOLERANCE_MIN, ref * _AMOUNT_REL_TOLERANCE)

    @classmethod
    def _amounts_match(cls, a: float, b: float) -> bool:
        return abs(a - b) <= cls._amount_tolerance(max(a, b))

    def _collect_reference_amounts(
        self, invoice_data: InvoiceData
    ) -> List[Tuple[str, float]]:
        """Candidate invoice totals (gross, net, line sums) — not only total_amount."""
        refs: List[Tuple[str, float]] = []
        total = float(invoice_data.total_amount or 0)
        tax = (
            float(invoice_data.tax_amount)
            if invoice_data.tax_amount is not None
            else 0.0
        )

        if total > 0.01:
            refs.append(("total_amount (celkem)", round(total, 2)))
        if tax > 0.01:
            refs.append(("tax_amount", round(tax, 2)))
            if total > tax + 0.01:
                refs.append(("základ (total − DPH)", round(total - tax, 2)))

        if invoice_data.line_items:
            sum_line_total = 0.0
            sum_qty_price = 0.0
            has_line_total = False
            for item in invoice_data.line_items:
                lt = item.get("total")
                if lt is not None:
                    try:
                        v = float(lt)
                        if v > 0:
                            sum_line_total += v
                            has_line_total = True
                    except (TypeError, ValueError):
                        pass
                up = item.get("unit_price")
                qty = item.get("quantity", 1)
                if up is not None:
                    try:
                        sum_qty_price += float(qty) * float(up)
                    except (TypeError, ValueError):
                        pass
            if has_line_total and sum_line_total > 0.01:
                refs.append(("suma položek (total)", round(sum_line_total, 2)))
            if sum_qty_price > 0.01:
                refs.append(
                    ("suma položek (množství × cena)", round(sum_qty_price, 2))
                )

        seen: set = set()
        unique: List[Tuple[str, float]] = []
        for label, val in refs:
            key = round(val, 2)
            if key in seen:
                continue
            seen.add(key)
            unique.append((label, key))
        return unique

    def _pick_vat_price_mode(
        self,
        totals_by_mode: Dict[str, float],
        references: List[Tuple[str, float]],
        *,
        extracted_total: float,
        account_mode: str,
        from_detailed: bool,
        zero_vat: bool,
    ) -> Tuple[str, Optional[str], float, bool]:
        """
        Choose vat_price_mode and whether amounts are consistent.

        Returns:
            (mode, matched_reference_label, diff_vs_matched_ref, ok)
        """
        if not from_detailed or zero_vat:
            mode = "without_vat"
            computed = totals_by_mode[mode]
            if references:
                label, ref = min(
                    references,
                    key=lambda r: abs(computed - r[1]),
                )
                diff = round(computed - ref, 2)
                ok = self._amounts_match(computed, ref)
                return mode, label, diff, ok
            return mode, None, 0.0, True

        best: Optional[Tuple[int, float, str, str]] = None
        for mode, computed in totals_by_mode.items():
            for label, ref in references:
                if not self._amounts_match(computed, ref):
                    continue
                priority = _REF_LABEL_PRIORITY.get(label, 50)
                diff = abs(computed - ref)
                score = (priority, diff)
                if best is None or score < (best[0], best[1]):
                    best = (priority, diff, mode, label)

        if best is not None:
            _, diff, mode, label = best
            ref_val = next(v for l, v in references if l == label)
            return mode, label, round(totals_by_mode[mode] - ref_val, 2), True

        # No reference matched — trust line items if total_amount missing / zero
        if extracted_total <= 0.01 and from_detailed:
            return account_mode, None, 0.0, True

        if not references:
            return account_mode, None, 0.0, from_detailed

        # Have total_amount but it matches neither mode (wrong field / DPH režim)
        mode = min(
            totals_by_mode,
            key=lambda m: min(
                abs(totals_by_mode[m] - ref) for _, ref in references
            ),
        )
        label, ref = min(
            references,
            key=lambda pair: abs(totals_by_mode[mode] - pair[1]),
        )
        diff = round(totals_by_mode[mode] - ref, 2)
        ok = self._amounts_match(totals_by_mode[mode], ref)
        return mode, label, diff, ok

    def _build_expense_lines(
        self, invoice_data: InvoiceData
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Build Fakturoid expense lines from extracted data.

        Returns:
            (lines, from_detailed_line_items) — False when using total/tax fallback.
        """
        lines: Optional[List[Dict[str, Any]]] = None
        from_detailed = False

        if invoice_data.line_items and len(invoice_data.line_items) > 0:
            billable_items = [
                item
                for item in invoice_data.line_items
                if self._parse_line_quantity(item.get("quantity"), 0) > 0
            ]
            skipped_zero_qty = len(invoice_data.line_items) - len(billable_items)
            if skipped_zero_qty:
                print(
                    f"  ℹ️  Přeskočeno {skipped_zero_qty} položek s množstvím 0 "
                    f"(Fakturoid vyžaduje quantity > 0)"
                )

            has_valid_prices = any(
                item.get("unit_price") and float(item.get("unit_price", 0)) > 0
                for item in billable_items
            )
            if has_valid_prices:
                from_detailed = True
                lines = []
                for item in billable_items:
                    qty = self._parse_line_quantity(item.get("quantity"), 1.0)
                    declared = self._line_item_declared_vat_rate(item)
                    vat_rate = (
                        declared
                        if declared is not None
                        else self._default_vat_rate_when_line_unspecified(invoice_data)
                    )
                    desc = item.get("description") or item.get("name") or ""
                    lines.append(
                        {
                            "name": desc,
                            "quantity": str(qty),
                            "unit_price": str(item.get("unit_price", 0)),
                            "vat_rate": vat_rate,
                        }
                    )

        if not lines:
            total = float(invoice_data.total_amount)
            if invoice_data.tax_amount and invoice_data.tax_amount > 0:
                tax = float(invoice_data.tax_amount)
                price_without_vat = total - tax
                if price_without_vat > 0:
                    vat_rate = max(0, min(100, round((tax / price_without_vat) * 100)))
                elif self._invoice_implies_zero_vat(invoice_data):
                    vat_rate = 0
                    price_without_vat = total
                else:
                    vat_rate = self._default_vat_rate_when_line_unspecified(invoice_data)
                    price_without_vat = total
            else:
                price_without_vat = total
                vat_rate = 0

            lines = [
                {
                    "name": invoice_data.notes or f"Invoice {invoice_data.invoice_number}",
                    "quantity": "1.0",
                    "unit_price": str(round(price_without_vat, 2)),
                    "vat_rate": vat_rate,
                }
            ]

        return lines, from_detailed

    def _validate_amounts_from_lines(
        self,
        invoice_data: InvoiceData,
        lines: List[Dict[str, Any]],
        from_detailed: bool,
    ) -> Dict[str, Any]:
        """
        Check line items vs. reference amounts (celkem, základ, sumy položek).

        Accepts match in either VAT price mode; does not require total_amount alone.
        """
        zero_vat = self._invoice_implies_zero_vat(invoice_data)
        account_mode = self.get_account_vat_price_mode()
        references = self._collect_reference_amounts(invoice_data)
        extracted_total = round(float(invoice_data.total_amount or 0), 2)

        totals_by_mode = {
            "without_vat": self._compute_document_total(
                lines, "without_vat", zero_vat=zero_vat
            ),
            "from_total_with_vat": self._compute_document_total(
                lines, "from_total_with_vat", zero_vat=zero_vat
            ),
        }

        chosen_mode, matched_ref, diff, ok = self._pick_vat_price_mode(
            totals_by_mode,
            references,
            extracted_total=extracted_total,
            account_mode=account_mode,
            from_detailed=from_detailed,
            zero_vat=zero_vat,
        )
        computed_total = totals_by_mode[chosen_mode]

        # When celkem was extracted, it must match at least one VAT mode total
        if extracted_total > 0.01 and from_detailed and not zero_vat:
            matches_extracted = any(
                self._amounts_match(totals_by_mode[m], extracted_total)
                for m in totals_by_mode
            )
            if not matches_extracted:
                ok = False

        warnings: List[str] = []
        if extracted_total <= 0.01 and from_detailed:
            warnings.append(
                "total_amount chybí nebo je 0 — kontrola podle položek faktury"
            )
        elif (
            matched_ref == "základ (total − DPH)"
            and chosen_mode == "from_total_with_vat"
        ):
            warnings.append(
                "total_amount vypadá jako základ bez DPH; použit režim z cílové částky"
            )

        tax_warning: Optional[str] = None
        computed_tax: Optional[float] = None
        if (
            invoice_data.tax_amount is not None
            and float(invoice_data.tax_amount) > 0.01
            and not zero_vat
        ):
            computed_tax = self._compute_document_vat(
                lines, chosen_mode, zero_vat=zero_vat
            )
            expected_tax = round(float(invoice_data.tax_amount), 2)
            if not self._amounts_match(computed_tax, expected_tax):
                tax_warning = (
                    f"DPH z položek ({computed_tax}) vs. tax_amount ({expected_tax})"
                )

        mode_labels = {
            "without_vat": "ze základu (bez DPH)",
            "from_total_with_vat": "z cílové částky (s DPH)",
        }

        ref_display = (
            f"{matched_ref}"
            if matched_ref
            else (
                "položky (bez spolehlivého total_amount)"
                if extracted_total <= 0.01
                else "—"
            )
        )

        return {
            "ok": ok,
            "expected_total": extracted_total,
            "reference_label": matched_ref,
            "reference_display": ref_display,
            "references": references,
            "computed_total": computed_total,
            "diff": diff,
            "vat_price_mode": chosen_mode,
            "vat_price_mode_label": mode_labels.get(chosen_mode, chosen_mode),
            "account_vat_price_mode": account_mode,
            "totals_by_mode": totals_by_mode,
            "from_detailed_line_items": from_detailed,
            "zero_vat": zero_vat,
            "warnings": warnings,
            "tax_warning": tax_warning,
            "computed_tax": computed_tax,
            "tolerance_note": f"min {_AMOUNT_ABS_TOLERANCE_MIN} Kč nebo {_AMOUNT_REL_TOLERANCE * 100:.1f} %",
        }

    def validate_expense_amounts(
        self,
        invoice_data: InvoiceData,
    ) -> Dict[str, Any]:
        """Check Fakturoid line totals; add rounding line when base+VAT ≠ invoice total."""
        _lines, _from_detailed, validation = self._prepare_expense_lines(invoice_data)
        return validation

    @staticmethod
    def format_amount_validation_message(validation: Dict[str, Any]) -> str:
        """Human-readable Czech summary for CLI / logs."""
        out = [
            "Kontrola částek (položky vs. částky na faktuře):",
            f"  total_amount (extrahováno): {validation['expected_total']}",
        ]
        refs = validation.get("references") or []
        if refs:
            ref_parts = [f"{label}={val}" for label, val in refs[:5]]
            out.append(f"  Referenční částky: {', '.join(ref_parts)}")
        out.append(
            f"  Výpočet Fakturoid ({validation['vat_price_mode_label']}): "
            f"{validation['computed_total']}"
        )
        if validation.get("reference_display"):
            out.append(f"  Porovnáno s: {validation['reference_display']}")
        if validation.get("computed_tax") is not None:
            out.append(f"  DPH ve výpočtu: {validation['computed_tax']}")
        by_mode = validation.get("totals_by_mode") or {}
        if validation.get("from_detailed_line_items") and len(by_mode) > 1:
            out.append(f"  Celkem ze základu: {by_mode.get('without_vat')}")
            out.append(f"  Celkem z cílové částky: {by_mode.get('from_total_with_vat')}")
        for w in validation.get("warnings") or []:
            out.append(f"  ⚠ {w}")
        diff = validation.get("diff", 0)
        if validation.get("ok"):
            if abs(diff) > 0.001:
                out.append(
                    f"  ✓ Souhlasí (rozdíl {diff:+.2f}, {validation.get('tolerance_note')})"
                )
            else:
                out.append("  ✓ Souhlasí")
        else:
            out.append(
                f"  ✗ Nesoulad {diff:+.2f} ({validation.get('tolerance_note')})"
            )
        if validation.get("tax_warning"):
            out.append(f"  ⚠ {validation['tax_warning']}")
        rounding = validation.get("rounding") or {}
        if rounding.get("subtotal") is not None:
            out.append(
                f"  Základ + DPH (položky): {rounding['subtotal']} + "
                f"{rounding['vat_computed']} = {rounding['gross_computed']}"
            )
            if rounding.get("invoice_tax") is not None:
                out.append(
                    f"  Základ + DPH (z faktury): {rounding['subtotal']} + "
                    f"{rounding['invoice_tax']} = {rounding['sum_base_plus_invoice_tax']}"
                )
            if rounding.get("invoice_total") is not None:
                out.append(f"  Celkem na faktuře: {rounding['invoice_total']}")
            if rounding.get("rounding_line_added"):
                out.append(
                    f"  ✓ Zaokrouhlení: {rounding['rounding_gap']:+.2f} → "
                    f"součet {rounding.get('gross_computed_after')}"
                )
            elif (
                rounding.get("rounding_gap") is not None
                and abs(rounding["rounding_gap"]) > 0.005
            ):
                out.append(
                    f"  ⚠ Rozdíl základ+DPH vs. celkem: {rounding['rounding_gap']:+.2f} "
                    f"(mimo auto zaokrouhlení ±{_MAX_AUTO_ROUNDING_GAP})"
                )
        return "\n".join(out)

    def convert_extracted_to_expense(
        self,
        invoice_data: InvoiceData,
        auto_create_subject: bool = True,
        amount_validation: Optional[Dict[str, Any]] = None,
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

        if amount_validation and amount_validation.get("lines"):
            lines = amount_validation["lines"]
            _from_detailed = amount_validation.get(
                "from_detailed_line_items", True
            )
            validation = amount_validation
        else:
            lines, _from_detailed, validation = self._prepare_expense_lines(
                invoice_data
            )
        if not validation["ok"]:
            raise AmountValidationError(
                self.format_amount_validation_message(validation)
            )
        vat_price_mode = validation["vat_price_mode"]
        if (
            _from_detailed
            and vat_price_mode != validation["account_vat_price_mode"]
        ):
            print(
                f"\nℹ️  DPH režim: použit {validation['vat_price_mode_label']} "
                f"(výchozí účet: {validation['account_vat_price_mode']})"
            )
        
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
            vat_price_mode=vat_price_mode,
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
        validation = self.validate_expense_amounts(invoice_data)
        print(f"\n{self.format_amount_validation_message(validation)}")
        if not validation["ok"]:
            raise AmountValidationError(
                self.format_amount_validation_message(validation)
            )

        subject_id, fakturoid_expense = self.convert_extracted_to_expense(
            invoice_data,
            auto_create_subject=auto_create_subject,
            amount_validation=validation,
        )
        
        return self.create_expense_invoice(fakturoid_expense.model_dump(exclude_none=True))

