import os
import json
import asyncio
import tempfile
import base64
from datetime import datetime
from werkzeug.utils import secure_filename
from mistral_processor import MistralProcessor

# Initialize processors
mistral_processor = MistralProcessor()

async def save_temp_file(file_data):
    """Save file data to a temporary file and return its path."""
    try:
        temp_dir = tempfile.gettempdir()
        # Get original filename but ensure it's secure
        original_filename = secure_filename(file_data.filename)
        # Generate a unique filename while preserving the original name
        temp_path = os.path.join(temp_dir, original_filename)
        # If file exists, add a number to make it unique
        counter = 1
        while os.path.exists(temp_path):
            name, ext = os.path.splitext(original_filename)
            temp_path = os.path.join(temp_dir, f"{name}_{counter}{ext}")
            counter += 1
        
        # Save the file in binary mode to preserve file integrity
        await file_data.save(temp_path)
        
        # Verify file was saved and is not empty
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise ValueError(f"Failed to save file or file is empty: {original_filename}")
            
        return temp_path
    except Exception as e:
        print(f"Error saving temporary file: {str(e)}")
        raise

async def process_file(file_path):
    """Process a PDF file using Mistral for content processing."""
    try:
        print(f"Starting to process PDF file: {file_path}")
        # Get original file name and content
        file_name = os.path.basename(file_path)
        
        # Read file content in binary mode to preserve file integrity
        with open(file_path, 'rb') as file:
            file_bytes = file.read()
            if len(file_bytes) == 0:
                raise ValueError(f"File {file_name} is empty")
                
            # Create proper base64 data URL for PDF
            file_content = f"data:application/pdf;base64,{base64.b64encode(file_bytes).decode('utf-8')}"
            print(f"Successfully read PDF file {file_name} ({len(file_bytes)} bytes)")

        # Process PDF using Mistral's OCR
        content = await mistral_processor.process_pdf(file_path)
        print(f"Successfully extracted content from PDF: {file_name}")

        # Return the processed content
        result = {
            "fileName": file_name,
            "processedContent": content
        }
        print(f"Returning processed content for file: {file_name}")
        return result

    except Exception as e:
        print(f"Error processing PDF file {os.path.basename(file_path)}: {str(e)}")
        # Return a structured error result
        error_result = {
            "fileName": os.path.basename(file_path),
            "error": f"Error: {str(e)}"
        }
        return error_result

async def process_single_file(file):
    """Process a single PDF file and return its content."""
    temp_path = None
    try:
        # Verify file is a PDF
        if not file.filename.lower().endswith('.pdf'):
            raise ValueError("Only PDF files are supported")
            
        # Save file to temporary location
        print(f"Processing PDF file: {file.filename}")
        temp_path = await save_temp_file(file)
        
        # Process the file
        result = await process_file(temp_path)
        return result
        
    except Exception as e:
        print(f"Error processing PDF file: {str(e)}")
        raise
        
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                print(f"Error cleaning up temporary file {temp_path}: {str(e)}") 