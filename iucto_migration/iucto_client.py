"""iÚčto API Client for fetching invoice data."""

import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
import time


class IUctoClient:
    """Client for communicating with iÚčto API.
    
    API Documentation: https://iucto.docs.apiary.io/
    """
    
    def __init__(self, api_key: str, base_url: str = "https://online.iucto.cz/api"):
        """Initialize iÚčto client.
        
        Args:
            api_key: iÚčto API key (from account settings)
            base_url: API base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Fakturoid Migration Tool'
        })
    
    def test_connection(self) -> bool:
        """Test API connection.
        
        Returns:
            True if connection successful
        """
        try:
            # Try a simple endpoint - adjust based on actual iÚčto API
            # Common endpoints: /account, /user, /invoices
            response = self.session.get(f"{self.base_url}/invoices", params={'limit': 1})
            return response.status_code in [200, 401]  # 401 means API is up, auth might be wrong
        except Exception as e:
            print(f"Connection test failed: {e}")
            print(f"\nTrying alternative: checking if API responds...")
            try:
                # Try without SSL verification as fallback (not recommended for production)
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                response = requests.get(f"{self.base_url}/invoices", 
                                       headers={'X-Api-Key': self.api_key},
                                       params={'limit': 1},
                                       verify=False,
                                       timeout=10)
                if response.status_code in [200, 401]:
                    print("⚠️  Connection works but SSL verification disabled")
                    print("   Consider updating SSL certificates or checking API URL")
                    return True
            except Exception as e2:
                print(f"Alternative connection also failed: {e2}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information.
        
        Returns:
            Account info dictionary
        """
        # Try common endpoints for account info
        endpoints = ['/account', '/user', '/company']
        
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    return response.json()
            except:
                continue
        
        # If none work, raise an error
        raise Exception("Could not fetch account info. Please check API documentation for correct endpoint.")
    
    def get_issued_invoices(
        self, 
        year: Optional[int] = None,
        status: str = "all",
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Fetch issued invoices (vystavené faktury).
        
        Args:
            year: Filter by year (e.g., 2013)
            status: Filter by status (all, paid, unpaid)
            limit: Maximum number of invoices to return
            
        Returns:
            List of invoice dictionaries
        """
        url = f"{self.base_url}/invoices"
        params = {}
        
        if year:
            params['year'] = year
        if status != 'all':
            params['status'] = status
        if limit:
            params['limit'] = limit
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        # Handle both list and paginated response
        if isinstance(data, dict) and 'invoices' in data:
            return data['invoices']
        return data if isinstance(data, list) else []
    
    def get_received_invoices(
        self, 
        year: Optional[int] = None,
        status: str = "all",
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Fetch received invoices/expenses (přijaté faktury).
        
        Args:
            year: Filter by year
            status: Filter by status (all, paid, unpaid)
            limit: Maximum number to return
            
        Returns:
            List of expense dictionaries
        """
        url = f"{self.base_url}/expenses"
        params = {}
        
        if year:
            params['year'] = year
        if status != 'all':
            params['status'] = status
        if limit:
            params['limit'] = limit
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        # Handle both list and paginated response
        if isinstance(data, dict) and 'expenses' in data:
            return data['expenses']
        return data if isinstance(data, list) else []
    
    def get_invoice_detail(self, invoice_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific invoice.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Invoice detail dictionary
        """
        url = f"{self.base_url}/invoices/{invoice_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_expense_detail(self, expense_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific expense.
        
        Args:
            expense_id: Expense ID
            
        Returns:
            Expense detail dictionary
        """
        url = f"{self.base_url}/expenses/{expense_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_years_with_invoices(self) -> List[int]:
        """Get list of years that have invoices.
        
        Returns:
            List of years (e.g., [2013, 2014, ..., 2021])
        """
        # This might need to be adjusted based on actual API
        # For now, we'll just return a range
        current_year = datetime.now().year
        return list(range(2013, current_year + 1))

