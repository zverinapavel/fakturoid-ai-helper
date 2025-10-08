"""Main orchestration agent for invoice processing."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil
from datetime import datetime

from .config import config
from .document_processor import DocumentProcessor
from .ai_extractor import AIInvoiceExtractor, InvoiceData
from .fakturoid_client import FakturoidClient


class InvoiceProcessingAgent:
    """Orchestrates the complete invoice processing pipeline."""
    
    def __init__(
        self,
        config_obj=None,
        invoices_dir: Optional[Path] = None,
        processed_dir: Optional[Path] = None,
        auto_submit: bool = False
    ):
        """Initialize the agent.
        
        Args:
            config_obj: Config object (if None, uses global config)
            invoices_dir: Directory containing invoices to process (overrides config)
            processed_dir: Directory to move processed invoices (overrides config)
            auto_submit: Whether to automatically submit to Fakturoid (overrides config)
        """
        # Use provided config or global config
        self.config = config_obj if config_obj is not None else config
        
        self.invoices_dir = invoices_dir or self.config.directories.invoices
        self.processed_dir = processed_dir or self.config.directories.processed
        self.auto_submit = auto_submit or self.config.processing.auto_submit
        
        # Initialize components with config
        self.doc_processor = DocumentProcessor(self.invoices_dir)
        self.ai_extractor = AIInvoiceExtractor(self.config)
        self.fakturoid_client = FakturoidClient(self.config)
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        log_dir = self.config.logging.file.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=self.config.logging.level,
            format=self.config.logging.format,
            handlers=[
                logging.FileHandler(self.config.logging.file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def test_connections(self) -> bool:
        """Test all external connections.
        
        Returns:
            True if all connections successful
        """
        self.logger.info("Testing Fakturoid connection...")
        if not self.fakturoid_client.test_connection():
            self.logger.error("Fakturoid connection failed")
            return False
        
        self.logger.info("All connections successful")
        return True
    
    def process_file(
        self,
        file_path: Path,
        review: bool = True
    ) -> Dict[str, Any]:
        """Process a single invoice file.
        
        Args:
            file_path: Path to invoice file
            review: Whether to show extracted data for review
            
        Returns:
            Processing result dictionary
        """
        self.logger.info(f"Processing file: {file_path.name}")
        
        result = {
            'file': file_path.name,
            'status': 'pending',
            'extracted_data': None,
            'fakturoid_response': None,
            'error': None
        }
        
        try:
            # Extract document data
            base64_data, media_type = self.doc_processor.file_to_base64(file_path)
            
            # Extract invoice data using AI
            if media_type == 'application/pdf':
                invoice_data = self.ai_extractor.extract_from_pdf(
                    base64_data,
                    source_file=file_path.name
                )
            else:
                invoice_data = self.ai_extractor.extract_from_image(
                    base64_data,
                    media_type=media_type,
                    source_file=file_path.name
                )
            
            result['extracted_data'] = invoice_data.model_dump()
            result['status'] = 'extracted'
            
            self.logger.info(f"Extracted data from {file_path.name}")
            
            # Display for review if requested
            if review:
                self._display_invoice_data(invoice_data)
                if not self.auto_submit:
                    return result
            
            # Submit to Fakturoid
            if self.auto_submit or not review:
                fakturoid_response = self.fakturoid_client.submit_expense(invoice_data)
                result['fakturoid_response'] = fakturoid_response
                result['status'] = 'submitted'
                self.logger.info(f"Submitted expense {invoice_data.invoice_number} to Fakturoid")
                
                # Move to processed directory
                self._move_to_processed(file_path)
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path.name}: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def process_batch(
        self,
        review: bool = True,
        max_files: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Process a batch of invoice files.
        
        Args:
            review: Whether to review each invoice before submission
            max_files: Maximum number of files to process (None = all)
            
        Returns:
            List of processing results
        """
        files = self.doc_processor.list_invoice_files()
        
        if max_files:
            files = files[:max_files]
        
        self.logger.info(f"Processing {len(files)} invoice files")
        
        results = []
        for file_path in files:
            result = self.process_file(file_path, review=review)
            results.append(result)
        
        # Summary
        successful = sum(1 for r in results if r['status'] == 'submitted')
        errors = sum(1 for r in results if r['status'] == 'error')
        
        self.logger.info(
            f"Batch processing complete: {successful} submitted, "
            f"{errors} errors out of {len(results)} total"
        )
        
        return results
    
    def _display_invoice_data(self, invoice_data: InvoiceData):
        """Display extracted invoice data for review.
        
        Args:
            invoice_data: Extracted invoice data
        """
        print("\n" + "="*60)
        print("EXTRACTED INVOICE DATA")
        print("="*60)
        print(f"Invoice Number: {invoice_data.invoice_number}")
        print(f"Issue Date: {invoice_data.issue_date}")
        print(f"Supplier: {invoice_data.supplier_name}")
        print(f"Total Amount: {invoice_data.total_amount} {invoice_data.currency or 'CZK'}")
        
        if invoice_data.due_date:
            print(f"Due Date: {invoice_data.due_date}")
        if invoice_data.variable_symbol:
            print(f"Variable Symbol: {invoice_data.variable_symbol}")
        if invoice_data.supplier_ico:
            print(f"IČO: {invoice_data.supplier_ico}")
        if invoice_data.supplier_dic:
            print(f"DIČ: {invoice_data.supplier_dic}")
        
        if invoice_data.line_items:
            print("\nLine Items:")
            for i, item in enumerate(invoice_data.line_items, 1):
                print(f"  {i}. {item.get('description', 'N/A')} - "
                      f"{item.get('quantity', 1)} x {item.get('unit_price', 0)}")
        
        print("="*60 + "\n")
    
    def _move_to_processed(self, file_path: Path):
        """Move processed file to processed directory.
        
        Args:
            file_path: Path to file to move
        """
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to filename to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{timestamp}_{file_path.name}"
        destination = self.processed_dir / new_name
        
        shutil.move(str(file_path), str(destination))
        self.logger.info(f"Moved {file_path.name} to processed directory")

