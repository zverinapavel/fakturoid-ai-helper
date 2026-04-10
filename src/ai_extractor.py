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
        'anthropic': 'claude-sonnet-4-5-20250929',
        'openai': 'gpt-4o',
        'deepseek': 'deepseek-chat',
        'groq': 'llama-3.2-90b-vision-preview',
        'ollama': 'llama3.2-vision'
    }
    
    # Approximate costs per 1M tokens (input/output) in USD
    MODEL_COSTS = {
        'claude-sonnet-4-5-20250929': {'input': 3.0, 'output': 15.0},
        'claude-3-5-sonnet-20241022': {'input': 3.0, 'output': 15.0},  # Deprecated
        'claude-3-opus-20240229': {'input': 15.0, 'output': 75.0},
        'gpt-4o': {'input': 2.5, 'output': 10.0},
        'gpt-4o-mini': {'input': 0.15, 'output': 0.6},
        'deepseek-chat': {'input': 0.14, 'output': 0.28},
        'llama-3.2-90b-vision-preview': {'input': 0.0, 'output': 0.0},  # Groq is free
        'llama3.2-vision': {'input': 0.0, 'output': 0.0}  # Ollama local
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
    
    def __init__(self, config_or_api_key, model: str = "claude-sonnet-4-5-20250929", provider: str = "anthropic"):
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
        
        # Usage tracking
        self.usage_stats = {
            'total_requests': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost_usd': 0.0,
            'requests': []
        }
    
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
        
        # Track usage
        self._track_usage(
            message.usage.input_tokens,
            message.usage.output_tokens,
            operation='extract_image'
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
        
        # Track usage
        if hasattr(response, 'usage') and response.usage:
            self._track_usage(
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                operation='extract_image'
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
        
        # Track usage
        self._track_usage(
            message.usage.input_tokens,
            message.usage.output_tokens,
            operation='extract_pdf'
        )
        
        return message.content[0].text
    
    def extract_invoice_data(self, file_path: Path, validate: bool = True) -> Dict[str, Any]:
        """Extract invoice data from a file (PDF or image).
        
        Args:
            file_path: Path to invoice file
            validate: Whether to validate and correct extraction with AI
            
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
        
        # Validate and correct if requested
        if validate:
            invoice_data = self._validate_and_correct(invoice_data, base64_data, media_type, doc_processor.is_pdf(file_path))
        
        # Return as dictionary
        return invoice_data.model_dump()
    
    def _validate_and_correct(self, invoice_data: InvoiceData, document_base64: str, media_type: str, is_pdf: bool) -> InvoiceData:
        """Validate extracted data and correct if needed using AI.
        
        Args:
            invoice_data: Initially extracted invoice data
            document_base64: Base64 encoded document
            media_type: Media type of document
            is_pdf: Whether document is PDF
            
        Returns:
            Validated and potentially corrected invoice data
        """
        import json
        
        # Create validation prompt
        validation_prompt = f"""You are validating invoice data extraction. Review the extracted data and the original invoice document.

EXTRACTED DATA:
{json.dumps(invoice_data.model_dump(), indent=2, ensure_ascii=False)}

VALIDATION CHECKLIST:
1. **Line Items Check**: 
   - Are the line_items actual products/services from the invoice?
   - NOT legal notices, tax information, payment instructions, or footer text
   - Each line item should have a clear description, quantity, and price
   - Common mistakes: extracting "Reverse charge applies" or "Tax obligation transferred" as line items

2. **Amounts Check**:
   - Does total_amount match the invoice total?
   - If line_items exist, do they roughly add up to total_amount?
   
3. **Date Format Check**:
   - Are dates in YYYY-MM-DD format?
   
4. **Currency Check**:
   - Is currency a valid ISO code (CZK, EUR, USD, not "Kc" or "Kč")?

If you find issues, return corrected JSON with the same structure.
If everything is correct, return the original JSON unchanged.

IMPORTANT RULES:
- For line_items: Only include actual products/services being sold
- If line_items look suspicious (like tax notices), remove them and leave line_items empty
- Preserve all other fields exactly as extracted

Return ONLY the corrected JSON, no explanations:"""

        try:
            # Send validation request
            if self.provider == "anthropic":
                response_text = self._validate_anthropic(document_base64, media_type, is_pdf, validation_prompt)
            elif self.provider in ["openai", "deepseek", "groq", "ollama"]:
                if is_pdf:
                    # Can't validate PDF with OpenAI-compatible APIs
                    print("⚠ Validation skipped: Provider doesn't support PDF")
                    return invoice_data
                response_text = self._validate_openai_compatible(document_base64, media_type, validation_prompt)
            else:
                print("⚠ Validation skipped: Provider not supported")
                return invoice_data
            
            # Parse corrected data
            corrected_data = self._extract_json_from_text(response_text)
            
            # Check if anything was corrected
            original_dict = invoice_data.model_dump()
            if corrected_data != original_dict:
                print("✓ AI validation corrected some fields")
                # Show what changed
                for key in corrected_data:
                    if corrected_data.get(key) != original_dict.get(key):
                        print(f"  - {key}: {original_dict.get(key)} → {corrected_data.get(key)}")
            else:
                print("✓ AI validation: data looks good")
            
            return InvoiceData(**corrected_data)
            
        except Exception as e:
            print(f"⚠ Validation failed: {e}")
            print("  Using original extraction")
            return invoice_data
    
    def _validate_anthropic(self, document_base64: str, media_type: str, is_pdf: bool, prompt: str) -> str:
        """Validate using Anthropic Claude."""
        if is_pdf:
            content = [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": document_base64,
                    },
                },
                {"type": "text", "text": prompt}
            ]
        else:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": document_base64,
                    },
                },
                {"type": "text", "text": prompt}
            ]
        
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0.0,
            messages=[{"role": "user", "content": content}]
        )
        
        # Track usage
        self._track_usage(
            message.usage.input_tokens,
            message.usage.output_tokens,
            operation='validation'
        )
        
        return message.content[0].text
    
    def _validate_openai_compatible(self, document_base64: str, media_type: str, prompt: str) -> str:
        """Validate using OpenAI-compatible API."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media_type};base64,{document_base64}"}
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        )
        
        # Track usage
        if hasattr(response, 'usage') and response.usage:
            self._track_usage(
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                operation='validation'
            )
        
        return response.choices[0].message.content
    
    def _track_usage(self, input_tokens: int, output_tokens: int, operation: str = 'extraction'):
        """Track API usage and costs.
        
        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            operation: Type of operation (extraction, validation)
        """
        import datetime
        
        # Calculate cost
        costs = self.MODEL_COSTS.get(self.model, {'input': 0, 'output': 0})
        cost_usd = (input_tokens * costs['input'] / 1_000_000) + (output_tokens * costs['output'] / 1_000_000)
        
        # Update totals
        self.usage_stats['total_requests'] += 1
        self.usage_stats['total_input_tokens'] += input_tokens
        self.usage_stats['total_output_tokens'] += output_tokens
        self.usage_stats['total_cost_usd'] += cost_usd
        
        # Store request details
        self.usage_stats['requests'].append({
            'timestamp': datetime.datetime.now().isoformat(),
            'operation': operation,
            'model': self.model,
            'provider': self.provider,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost_usd': cost_usd
        })
        
        # Print summary
        print(f"💰 API Usage: {input_tokens:,} in + {output_tokens:,} out = ${cost_usd:.4f} ({operation})")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics.
        
        Returns:
            Dictionary with usage stats
        """
        return self.usage_stats.copy()
    
    def _convert_to_czk(self, usd_amount: float) -> float:
        """Convert USD to CZK using current ČNB exchange rate.
        
        Args:
            usd_amount: Amount in USD
            
        Returns:
            Amount in CZK
        """
        import requests
        from datetime import datetime
        
        # Get current exchange rate from ČNB
        today = datetime.now().strftime('%d.%m.%Y')
        
        try:
            # ČNB daily exchange rates API
            url = f"https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/denni_kurz.txt"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            # Parse the response (format: "datum|země|měna|množství|kód|kurz")
            lines = response.text.strip().split('\n')
            
            for line in lines[2:]:  # Skip header lines
                parts = line.split('|')
                if len(parts) >= 5 and parts[3] == 'USD':
                    # Exchange rate format: "1" USD = "XX,XXX" CZK
                    rate_str = parts[4].replace(',', '.')
                    exchange_rate = float(rate_str)
                    return usd_amount * exchange_rate
            
            # If USD not found in the list, fallback
            raise ValueError("USD not found in ČNB rates")
            
        except Exception as e:
            # Fallback to approximate rate
            raise e
    
    def print_usage_summary(self):
        """Print usage summary."""
        stats = self.usage_stats
        print("\n" + "="*60)
        print("📊 AI USAGE SUMMARY")
        print("="*60)
        print(f"Provider: {self.provider}")
        print(f"Model: {self.model}")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Total Input Tokens: {stats['total_input_tokens']:,}")
        print(f"Total Output Tokens: {stats['total_output_tokens']:,}")
        print(f"Total Cost: ${stats['total_cost_usd']:.4f} USD")
        
        # Get current USD/CZK exchange rate and convert
        try:
            czk_cost = self._convert_to_czk(stats['total_cost_usd'])
            print(f"Total Cost: {czk_cost:.2f} Kč (kurz ČNB)")
        except Exception as e:
            # Fallback to approximate rate if ČNB API fails
            approx_czk = stats['total_cost_usd'] * 23.0
            print(f"Total Cost: ~{approx_czk:.2f} Kč (odhadovaný kurz)")
        
        print("="*60 + "\n")
    
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
