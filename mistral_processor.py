import os
import json
import asyncio
from mistralai import Mistral
from dotenv import load_dotenv
from typing import Dict, Any

class MistralProcessor:
    def __init__(self):
        """Initialize the Mistral processor with API credentials."""
        load_dotenv()
        self.api_key = os.getenv('MISTRAL_API_KEY')
        if not self.api_key:
            raise ValueError("Missing MISTRAL_API_KEY environment variable")
            
        print(f"Initializing Mistral client with API key starting with: {self.api_key[:4]}...")
        self.client = Mistral(api_key=self.api_key)

    async def process_pdf(self, file_path: str) -> str:
        """
        Process a PDF file using Mistral's OCR capabilities to extract raw content.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text content from the PDF
        """
        try:
            print(f"Processing PDF: {os.path.basename(file_path)}")
            
            # Upload the PDF file for OCR
            with open(file_path, "rb") as file:
                uploaded_file = await self.client.files.upload_async(
                    file={
                        "file_name": os.path.basename(file_path),
                        "content": file,
                    },
                    purpose="ocr"
                )
                
                print(f"Uploaded file with ID: {uploaded_file.id}")
                
                # Get signed URL for the uploaded file
                signed_url = await self.client.files.get_signed_url_async(file_id=uploaded_file.id)
                
                # Process the PDF with OCR
                ocr_response = await self.client.ocr.process_async(
                    model="mistral-ocr-latest",
                    document={
                        "type": "document_url",
                        "document_url": signed_url.url,
                    }
                )
                
                # Print the OCR response structure for debugging
                print(f"OCR Response type: {type(ocr_response)}")
                print(f"OCR Response attributes: {dir(ocr_response)}")
                
                # Extract the text content from the OCR response
                # The actual attribute might be different based on the response structure
                if hasattr(ocr_response, 'pages'):
                    # If the response has pages, extract text from each page
                    text_content = ""
                    for page in ocr_response.pages:
                        if hasattr(page, 'text'):
                            text_content += page.text + "\n\n"
                        elif hasattr(page, 'markdown'):
                            text_content += page.markdown + "\n\n"
                elif hasattr(ocr_response, 'content'):
                    # If the response has content attribute
                    text_content = ocr_response.content
                elif hasattr(ocr_response, 'markdown'):
                    # If the response has markdown attribute
                    text_content = ocr_response.markdown
                else:
                    # Convert the entire response to a string as a fallback
                    text_content = str(ocr_response)
                
                print(f"Successfully extracted content from PDF")
                return text_content
                
        except Exception as e:
            print(f"Error processing PDF with Mistral OCR: {str(e)}")
            raise 