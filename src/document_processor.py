"""Document processing utilities for invoices."""

import base64
import io
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import pypdf


class DocumentProcessor:
    """Handles loading and preprocessing of invoice documents."""
    
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    SUPPORTED_PDF_FORMAT = {'.pdf'}
    
    def __init__(self, invoices_dir):
        """Initialize document processor.
        
        Args:
            invoices_dir: Directory containing invoice files (str or Path)
        """
        if isinstance(invoices_dir, Path):
            self.invoices_dir = invoices_dir
        else:
            self.invoices_dir = Path(invoices_dir)
        
    def list_invoice_files(self) -> List[Path]:
        """List all supported invoice files in the directory.
        
        Returns:
            List of paths to invoice files
        """
        files = []
        for ext in self.SUPPORTED_IMAGE_FORMATS | self.SUPPORTED_PDF_FORMAT:
            # Search for both lowercase and uppercase extensions
            files.extend(self.invoices_dir.glob(f"*{ext}"))
            files.extend(self.invoices_dir.glob(f"*{ext.upper()}"))
        
        # Remove duplicates (in case filesystem is case-insensitive)
        unique_files = list(set(files))
        return sorted(unique_files)
    
    def is_pdf(self, file_path: Path) -> bool:
        """Check if file is a PDF.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if PDF, False otherwise
        """
        return file_path.suffix.lower() in self.SUPPORTED_PDF_FORMAT
    
    def is_image(self, file_path: Path) -> bool:
        """Check if file is an image.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if image, False otherwise
        """
        return file_path.suffix.lower() in self.SUPPORTED_IMAGE_FORMATS
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            reader = pypdf.PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def pdf_to_images(self, pdf_path: Path) -> List[Image.Image]:
        """Convert PDF pages to images (for scanned PDFs).
        
        Note: This is a basic implementation. For production, you might want
        to use pdf2image which requires poppler.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PIL Images
        """
        # This is a placeholder - actual implementation would require pdf2image
        # For now, we'll note that scanned PDFs should be converted separately
        # or we can use the AI vision model directly on the PDF
        return []
    
    def load_image(self, image_path: Path) -> Image.Image:
        """Load an image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            PIL Image
        """
        return Image.open(image_path)
    
    def image_to_base64(self, image: Image.Image, format: str = "PNG") -> str:
        """Convert PIL Image to base64 string.
        
        Args:
            image: PIL Image
            format: Output format (PNG, JPEG, etc.)
            
        Returns:
            Base64 encoded string
        """
        buffered = io.BytesIO()
        image.save(buffered, format=format)
        return base64.b64encode(buffered.getvalue()).decode()
    
    def file_to_base64(self, file_path: Path) -> Tuple[str, str]:
        """Convert file to base64 string.
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (base64_string, media_type)
        """
        if self.is_image(file_path):
            image = self.load_image(file_path)
            # Determine media type from extension
            ext = file_path.suffix.lower()
            media_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            media_type = media_type_map.get(ext, 'image/png')
            format_map = {
                'image/jpeg': 'JPEG',
                'image/png': 'PNG',
                'image/gif': 'GIF',
                'image/webp': 'WEBP'
            }
            base64_str = self.image_to_base64(image, format=format_map.get(media_type, 'PNG'))
            return base64_str, media_type
        
        elif self.is_pdf(file_path):
            with open(file_path, 'rb') as f:
                base64_str = base64.b64encode(f.read()).decode()
            return base64_str, 'application/pdf'
        
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

