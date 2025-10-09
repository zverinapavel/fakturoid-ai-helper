"""iÚčto API Client for fetching invoice data."""

import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
import time


class IUctoClient:
    """Client for communicating with iÚčto API.
    
    API Documentation: https://iucto.docs.apiary.io/
    """
    
    def __init__(self, api_key: str, base_url: str = "https://online.iucto.cz/api", api_version: str = "1.3"):
        """Initialize iÚčto client.
        
        Args:
            api_key: iÚčto API key (from account settings)
            base_url: API base URL
            api_version: API version (default: 1.3)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.api_version = api_version
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
            # Test with versioned endpoint and pagination
            url = f"{self.base_url}/{self.api_version}/invoice_issued"
            response = self.session.get(url, params={'page': 1, 'pageSize': 1})
            return response.status_code == 200
        except Exception as e:
            print(f"Connection test failed: {e}")
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
        """Fetch issued invoices (vystavené faktury) with pagination.
        
        Args:
            year: Filter by year (e.g., 2013)
            status: Filter by status (all, paid, unpaid)
            limit: Maximum number of invoices to return (None = all)
            
        Returns:
            List of invoice dictionaries
        """
        url = f"{self.base_url}/{self.api_version}/invoice_issued"
        
        all_invoices = []
        page = 1
        page_size = 200  # Maximum allowed
        
        while True:
            params = {
                'page': page,
                'pageSize': page_size
            }
            
            if year:
                params['year'] = year
            if status != 'all':
                params['status'] = status
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract invoices from response
            if isinstance(data, dict):
                invoices = data.get('invoices', data.get('items', []))
                total_pages = data.get('totalPages', 1)
                current_page = data.get('page', page)
            else:
                invoices = data if isinstance(data, list) else []
                total_pages = 1
            
            all_invoices.extend(invoices)
            
            # Check if we should stop
            if limit and len(all_invoices) >= limit:
                return all_invoices[:limit]
            
            if page >= total_pages or len(invoices) == 0:
                break
            
            page += 1
            time.sleep(0.1)  # Small delay between pages
        
        return all_invoices
    
    def get_received_invoices(
        self, 
        year: Optional[int] = None,
        status: str = "all",
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Fetch received invoices/expenses (přijaté faktury) with pagination.
        
        Args:
            year: Filter by year
            status: Filter by status (all, paid, unpaid)
            limit: Maximum number to return (None = all)
            
        Returns:
            List of expense dictionaries
        """
        url = f"{self.base_url}/{self.api_version}/invoice_received"
        
        all_expenses = []
        page = 1
        page_size = 200  # Maximum allowed
        
        while True:
            params = {
                'page': page,
                'pageSize': page_size
            }
            
            if year:
                params['year'] = year
            if status != 'all':
                params['status'] = status
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract expenses from response
            if isinstance(data, dict):
                expenses = data.get('expenses', data.get('invoices', data.get('items', [])))
                total_pages = data.get('totalPages', 1)
                current_page = data.get('page', page)
            else:
                expenses = data if isinstance(data, list) else []
                total_pages = 1
            
            all_expenses.extend(expenses)
            
            # Check if we should stop
            if limit and len(all_expenses) >= limit:
                return all_expenses[:limit]
            
            if page >= total_pages or len(expenses) == 0:
                break
            
            page += 1
            time.sleep(0.1)  # Small delay between pages
        
        return all_expenses
    
    def get_invoice_detail(self, invoice_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific invoice.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Invoice detail dictionary
        """
        url = f"{self.base_url}/{self.api_version}/invoice_issued/{invoice_id}"
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
        url = f"{self.base_url}/{self.api_version}/invoice_received/{expense_id}"
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

