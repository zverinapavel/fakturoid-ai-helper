"""AI-powered invoice data extraction."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from anthropic import Anthropic
from pydantic import BaseModel, Field
from datetime import date


class InvoiceData(BaseModel):
    """Structured invoice data model."""
    
    # Required fields
    invoice_number: str = Field(description="Invoice number or ID")
    issue_date: str = Field(description="Invoice issue date (YYYY-MM-DD)")
    supplier_name: str = Field(description="Supplier/vendor company name")
    total_amount: float = Field(description="Total amount including tax")
    
    # Optional fields
    due_date: Optional[str] = Field(None, description="Payment due date (YYYY-MM-DD)")
    variable_symbol: Optional[str] = Field(None, description="Variable symbol for payment")
    supplier_address: Optional[str] = Field(None, description="Supplier address")
    supplier_ico: Optional[str] = Field(None, description="Supplier IČO (company ID)")
    supplier_dic: Optional[str] = Field(None, description="Supplier DIČ (tax ID)")
    currency: Optional[str] = Field("CZK", description="Currency code")
    tax_amount: Optional[float] = Field(None, description="VAT/tax amount")
    line_items: Optional[list] = Field(None, description="List of invoice line items")
    notes: Optional[str] = Field(None, description="Additional notes or description")
    
    # Metadata
    confidence: Optional[float] = Field(None, description="Extraction confidence (0-1)")
    source_file: Optional[str] = Field(None, description="Source file name")


class AIInvoiceExtractor:
    """Extract invoice data using AI vision models."""
    
    EXTRACTION_PROMPT = """Analyze this invoice document and extract the following information in JSON format:

Required fields:
- invoice_number: The invoice number or ID
- issue_date: Invoice issue date in YYYY-MM-DD format
- supplier_name: Name of the company/supplier
- total_amount: Total amount including tax (as a number)

Optional fields (if available):
- due_date: Payment due date in YYYY-MM-DD format
- variable_symbol: Variable symbol for payment
- supplier_address: Complete supplier address
- supplier_ico: IČO (company identification number)
- supplier_dic: DIČ (tax identification number)
- currency: Currency code (e.g., CZK, EUR, USD)
- tax_amount: VAT/tax amount (as a number)
- line_items: Array of items with description, quantity, unit_price, total
- notes: Any additional notes or payment instructions

Return ONLY valid JSON in this exact format:
{
  "invoice_number": "...",
  "issue_date": "YYYY-MM-DD",
  "supplier_name": "...",
  "total_amount": 0.0,
  "due_date": "YYYY-MM-DD",
  "currency": "CZK",
  ...
}

If a field is not visible or unclear, omit it from the JSON. Be precise and only extract data that you can clearly see in the document."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """Initialize AI extractor.
        
        Args:
            api_key: Anthropic API key
            model: Model to use for extraction
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def extract_from_image(
        self, 
        image_base64: str, 
        media_type: str = "image/png",
        source_file: Optional[str] = None
    ) -> InvoiceData:
        """Extract invoice data from image.
        
        Args:
            image_base64: Base64 encoded image
            media_type: Image media type
            source_file: Source file name for metadata
            
        Returns:
            Extracted invoice data
        """
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": self.EXTRACTION_PROMPT
                        }
                    ],
                }
            ],
        )
        
        # Extract JSON from response
        response_text = message.content[0].text
        json_data = self._extract_json_from_text(response_text)
        
        # Add metadata
        json_data['source_file'] = source_file
        
        # Parse and validate with Pydantic
        return InvoiceData(**json_data)
    
    def extract_from_pdf(
        self,
        pdf_base64: str,
        source_file: Optional[str] = None
    ) -> InvoiceData:
        """Extract invoice data from PDF.
        
        Args:
            pdf_base64: Base64 encoded PDF
            source_file: Source file name for metadata
            
        Returns:
            Extracted invoice data
        """
        # Claude supports PDF documents directly
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": self.EXTRACTION_PROMPT
                        }
                    ],
                }
            ],
        )
        
        # Extract JSON from response
        response_text = message.content[0].text
        json_data = self._extract_json_from_text(response_text)
        
        # Add metadata
        json_data['source_file'] = source_file
        
        # Parse and validate with Pydantic
        return InvoiceData(**json_data)
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """Extract JSON object from text response.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Parsed JSON dictionary
        """
        # Try to find JSON in the text
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No JSON found in response")
        
        json_str = text[start_idx:end_idx + 1]
        return json.loads(json_str)

