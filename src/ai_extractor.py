"""AI-powered invoice data extraction."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import date

# Import AI libraries with fallbacks
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import requests  # For DeepSeek, Groq, and Ollama
except ImportError:
    requests = None


class InvoiceData(BaseModel):
    """Structured invoice data model."""
    
    # Required fields
    invoice_number: str = Field(description="Invoice number or ID")
    issue_date: str = Field(description="Invoice issue date (YYYY-MM-DD)")
    supplier_name: str = Field(description="Supplier/vendor company name")
    total_amount: float = Field(description="Total amount including tax")
    
    # Optional fields
    due_date: Optional[str] = Field(None, description="Payment due date (YYYY-MM-DD)")
    taxable_fulfillment_due: Optional[str] = Field(None, description="Taxable fulfillment date / Date of chargeable event (YYYY-MM-DD)")
    variable_symbol: Optional[str] = Field(None, description="Variable symbol for payment")
    
    # Supplier address fields (detailed for foreign companies)
    supplier_address: Optional[str] = Field(None, description="Complete supplier address (fallback)")
    supplier_street: Optional[str] = Field(None, description="Supplier street and number")
    supplier_city: Optional[str] = Field(None, description="Supplier city")
    supplier_zip: Optional[str] = Field(None, description="Supplier postal code")
    supplier_country: Optional[str] = Field(None, description="Supplier country (ISO code or name)")
    
    # Supplier IDs
    supplier_ico: Optional[str] = Field(None, description="Supplier IČO (Czech company ID)")
    supplier_dic: Optional[str] = Field(None, description="Supplier DIČ/VAT (tax ID)")
    supplier_vat_number: Optional[str] = Field(None, description="EU VAT number (for foreign companies)")
    
    # Other fields
    currency: Optional[str] = Field("CZK", description="Currency code")
    tax_amount: Optional[float] = Field(None, description="VAT/tax amount")
    line_items: Optional[list] = Field(None, description="List of invoice line items")
    notes: Optional[str] = Field(None, description="Additional notes or description")
    
    # Metadata
    confidence: Optional[float] = Field(None, description="Extraction confidence (0-1)")
    source_file: Optional[str] = Field(None, description="Source file name")


class AIInvoiceExtractor:
    """Extract invoice data using AI vision models."""
    
    # Supported providers and their default models
    PROVIDER_MODELS = {
        'anthropic': 'claude-3-5-sonnet-20241022',
        'openai': 'gpt-4o',
        'deepseek': 'deepseek-chat',
        'groq': 'llama-3.2-90b-vision-preview',
        'ollama': 'llama3.2-vision'
    }
    
    EXTRACTION_PROMPT = """Analyze this invoice document and extract the following information in JSON format:

Required fields:
- invoice_number: The invoice number or ID
- issue_date: Invoice issue date in YYYY-MM-DD format
- supplier_name: Name of the company/supplier
- total_amount: Total amount including tax (as a number)

Optional fields (if available):
- due_date: Payment due date in YYYY-MM-DD format
- taxable_fulfillment_due: Date of taxable fulfillment / chargeable event (DUZP - Datum uskutečnění zdanitelného plnění) in YYYY-MM-DD format
- variable_symbol: Variable symbol for payment (VS)

Supplier address (extract separately if possible):
- supplier_street: Street name and number
- supplier_city: City name
- supplier_zip: Postal/ZIP code
- supplier_country: Country name or ISO code (e.g., CZ, DE, US)
- supplier_address: Complete address as one string (if structured fields not available)

Supplier identification numbers:
- supplier_ico: IČO (Czech company registration number, 8 digits)
- supplier_dic: DIČ (Czech tax ID, starts with CZ)
- supplier_vat_number: EU VAT number (for foreign companies, e.g., DE123456789, GB999999999)

Other fields:
- currency: Currency code in ISO format (CZK, EUR, USD, GBP - NOT "Kc" or "Kč"!)
- tax_amount: VAT/tax amount (as a number)
- line_items: Array of items with description, quantity, unit_price, total
- notes: Any additional notes or payment instructions

Return ONLY valid JSON in this exact format:
{
  "invoice_number": "...",
  "issue_date": "YYYY-MM-DD",
  "supplier_name": "...",
  "total_amount": 0.0,
  "supplier_street": "123 Main St",
  "supplier_city": "Prague",
  "supplier_zip": "11000",
  "supplier_country": "CZ",
  "supplier_vat_number": "DE123456789",
  "currency": "EUR",
  ...
}

Important:
- For Czech companies: extract supplier_ico and supplier_dic
- For foreign companies: extract supplier_vat_number
- Always extract address components (street, city, zip, country) separately if visible
- If a field is not visible or unclear, omit it from the JSON
- Be precise and only extract data that you can clearly see in the document"""
    
    def __init__(self, config_or_api_key, model: str = "claude-3-5-sonnet-20241022", provider: str = "anthropic"):
        """Initialize AI extractor.
        
        Args:
            config_or_api_key: Either a Config object or an API key string
            model: Model to use for extraction (ignored if config is provided)
            provider: AI provider to use (ignored if config is provided)
        """
        # Support both config object and direct API key
        if hasattr(config_or_api_key, 'ai'):
            # It's a config object
            self.config = config_or_api_key
            self.provider = config_or_api_key.ai.provider
            self.model = config_or_api_key.ai.model
            self.temperature = config_or_api_key.ai.temperature
            self.max_tokens = config_or_api_key.ai.max_tokens
            self.api_key = config_or_api_key.get_api_key(self.provider)
        else:
            # It's an API key string
            self.config = None
            self.provider = provider
            self.model = model
            self.temperature = 0.0
            self.max_tokens = 4096
            self.api_key = config_or_api_key
        
        # Initialize the appropriate client
        self._init_client()
    
    def _init_client(self):
        """Initialize the AI client based on provider."""
        if self.provider == "anthropic":
            if Anthropic is None:
                raise ImportError("anthropic library not installed. Install with: pip install anthropic")
            self.client = Anthropic(api_key=self.api_key)
            
        elif self.provider == "openai":
            if OpenAI is None:
                raise ImportError("openai library not installed. Install with: pip install openai")
            self.client = OpenAI(api_key=self.api_key)
            
        elif self.provider == "deepseek":
            if OpenAI is None:
                raise ImportError("openai library not installed. Install with: pip install openai")
            # DeepSeek uses OpenAI-compatible API
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            
        elif self.provider == "groq":
            if OpenAI is None:
                raise ImportError("openai library not installed. Install with: pip install openai")
            # Groq uses OpenAI-compatible API
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            
        elif self.provider == "ollama":
            if OpenAI is None:
                raise ImportError("openai library not installed. Install with: pip install openai")
            # Ollama uses OpenAI-compatible API
            base_url = self.config.ai.ollama_base_url if self.config else "http://localhost:11434"
            self.client = OpenAI(
                api_key="ollama",  # Ollama doesn't need real API key
                base_url=f"{base_url}/v1"
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
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
        if self.provider == "anthropic":
            response_text = self._extract_anthropic_image(image_base64, media_type)
        elif self.provider in ["openai", "deepseek", "groq", "ollama"]:
            response_text = self._extract_openai_compatible_image(image_base64, media_type)
        else:
            raise ValueError(f"Provider {self.provider} doesn't support image extraction")
        
        # Extract JSON from response
        json_data = self._extract_json_from_text(response_text)
        
        # Add metadata
        json_data['source_file'] = source_file
        json_data['ai_provider'] = self.provider
        json_data['ai_model'] = self.model
        
        # Parse and validate with Pydantic
        return InvoiceData(**json_data)
    
    def _extract_anthropic_image(self, image_base64: str, media_type: str) -> str:
        """Extract using Anthropic Claude."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
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
        return message.content[0].text
    
    def _extract_openai_compatible_image(self, image_base64: str, media_type: str) -> str:
        """Extract using OpenAI-compatible API (OpenAI, DeepSeek, Groq, Ollama)."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": self.EXTRACTION_PROMPT
                        }
                    ]
                }
            ]
        )
        return response.choices[0].message.content
    
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
        if self.provider == "anthropic":
            response_text = self._extract_anthropic_pdf(pdf_base64)
        elif self.provider in ["openai", "deepseek", "groq", "ollama"]:
            # OpenAI-compatible APIs don't support PDF directly, convert to image
            # For now, we'll raise an error - in production, use pdf2image
            raise NotImplementedError(
                f"{self.provider} doesn't support direct PDF extraction. "
                "Use Anthropic or convert PDF to images first."
            )
        else:
            raise ValueError(f"Provider {self.provider} doesn't support PDF extraction")
        
        # Extract JSON from response
        json_data = self._extract_json_from_text(response_text)
        
        # Add metadata
        json_data['source_file'] = source_file
        json_data['ai_provider'] = self.provider
        json_data['ai_model'] = self.model
        
        # Parse and validate with Pydantic
        return InvoiceData(**json_data)
    
    def _extract_anthropic_pdf(self, pdf_base64: str) -> str:
        """Extract using Anthropic Claude (supports PDF natively)."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
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
        return message.content[0].text
    
    def extract_invoice_data(self, file_path: Path) -> Dict[str, Any]:
        """Extract invoice data from a file (PDF or image).
        
        Args:
            file_path: Path to invoice file
            
        Returns:
            Extracted invoice data as dictionary
        """
        from .document_processor import DocumentProcessor
        
        doc_processor = DocumentProcessor(file_path.parent)
        
        # Convert file to base64
        base64_data, media_type = doc_processor.file_to_base64(file_path)
        
        # Extract based on file type
        if doc_processor.is_pdf(file_path):
            invoice_data = self.extract_from_pdf(base64_data, source_file=file_path.name)
        elif doc_processor.is_image(file_path):
            invoice_data = self.extract_from_image(base64_data, media_type=media_type, source_file=file_path.name)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        
        # Return as dictionary
        return invoice_data.model_dump()
    
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


# Alias for convenience
AIExtractor = AIInvoiceExtractor
