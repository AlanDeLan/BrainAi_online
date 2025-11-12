"""
Module for processing and chunking text files for vector database.
Supports: txt, md, docx, pdf, and other text formats.
"""
import os
import sys
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# Lazy import logger
def get_logger():
    """Get logger instance (lazy import)."""
    try:
        from core.logger import logger
        return logger
    except ImportError:
        import logging
        return logging.getLogger("local_brain")

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into chunks with overlap.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk (characters)
        chunk_overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within last 200 chars
            search_start = max(start, end - 200)
            sentence_end = max(
                text.rfind('.', search_start, end),
                text.rfind('!', search_start, end),
                text.rfind('?', search_start, end),
                text.rfind('\n', search_start, end)
            )
            
            if sentence_end > start:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - chunk_overlap
        if start >= len(text):
            break
    
    return chunks

def extract_text_from_txt(file_path: str) -> str:
    """Extract text from .txt file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with different encodings
        encodings = ['latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, Exception):
                continue
        raise ValueError(f"Could not decode file {file_path} with any encoding")

def extract_text_from_md(file_path: str) -> str:
    """Extract text from .md file."""
    return extract_text_from_txt(file_path)  # Markdown is just text

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from .docx file."""
    try:
        from docx import Document
        doc = Document(file_path)
        text_parts = []
        for paragraph in doc.paragraphs:
            text_parts.append(paragraph.text)
        return '\n'.join(text_parts)
    except ImportError:
        raise ImportError("python-docx not installed. Install with: pip install python-docx")
    except Exception as e:
        raise ValueError(f"Error reading DOCX file: {e}")

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from .pdf file."""
    try:
        import PyPDF2
        text_parts = []
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())
        return '\n'.join(text_parts)
    except ImportError:
        raise ImportError("PyPDF2 not installed. Install with: pip install PyPDF2")
    except Exception as e:
        raise ValueError(f"Error reading PDF file: {e}")

def extract_text_from_file(file_path: str) -> Tuple[str, str]:
    """
    Extract text from file based on extension.
    
    Args:
        file_path: Path to file
    
    Returns:
        Tuple of (text_content, file_extension)
    """
    logger = get_logger()
    file_path_obj = Path(file_path)
    extension = file_path_obj.suffix.lower()
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    logger.debug(f"Extracting text from {file_path} (extension: {extension})")
    
    if extension == '.txt':
        text = extract_text_from_txt(file_path)
    elif extension == '.md':
        text = extract_text_from_md(file_path)
    elif extension == '.docx':
        text = extract_text_from_docx(file_path)
    elif extension == '.pdf':
        text = extract_text_from_pdf(file_path)
    else:
        # Try as text file
        logger.warning(f"Unknown extension {extension}, trying as text file")
        text = extract_text_from_txt(file_path)
    
    return text, extension

def process_file(file_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, any]]:
    """
    Process file and return chunks with metadata.
    
    Args:
        file_path: Path to file
        chunk_size: Maximum size of each chunk (characters)
        chunk_overlap: Number of characters to overlap between chunks
    
    Returns:
        List of dictionaries with chunk data:
        {
            "text": str,
            "chunk_index": int,
            "file_name": str,
            "file_path": str,
            "file_type": str,
            "total_chunks": int
        }
    """
    logger = get_logger()
    
    try:
        # Extract text
        text, extension = extract_text_from_file(file_path)
        
        if not text or not text.strip():
            logger.warning(f"File {file_path} is empty or contains no text")
            return []
        
        # Chunk text
        chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        file_name = os.path.basename(file_path)
        
        # Create chunk metadata
        chunk_data = []
        for i, chunk in enumerate(chunks):
            chunk_data.append({
                "text": chunk,
                "chunk_index": i,
                "file_name": file_name,
                "file_path": file_path,
                "file_type": extension,
                "total_chunks": len(chunks)
            })
        
        logger.info(f"Processed file {file_name}: {len(chunks)} chunks from {len(text)} characters")
        return chunk_data
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
        raise

def get_supported_extensions() -> List[str]:
    """Get list of supported file extensions."""
    return ['.txt', '.md', '.docx', '.pdf']

def is_file_supported(file_path: str) -> bool:
    """Check if file extension is supported."""
    extension = Path(file_path).suffix.lower()
    return extension in get_supported_extensions()




