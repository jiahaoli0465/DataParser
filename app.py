from quart import Quart, Response, request, send_from_directory
from quart_cors import cors
import json
import os
import tempfile
from werkzeug.utils import secure_filename
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from file_processor import process_single_file
from deepseek_processor import DeepSeekProcessor
from dotenv import load_dotenv

# Initialize app
app = Quart(__name__)
app = cors(app, allow_origin="*")

# Initialize processors
deepseek_processor = DeepSeekProcessor()

# Ensure static directory exists
os.makedirs('static', exist_ok=True)

load_dotenv()

def create_json_response(data: Dict[str, Any], status_code: int = 200) -> Response:
    """Helper function to create JSON responses with proper headers."""
    return Response(
        json.dumps(data),
        status=status_code,
        mimetype='application/json'
    )

# Serve the HTML file at the root URL
@app.route('/', methods=['GET'])
async def index():
    """Serve the HTML file for uploading PDFs."""
    return await send_from_directory('static', 'index.html')

# Test endpoint
@app.route('/api/test', methods=['GET'])
async def test():
    """Test endpoint to verify the backend is running."""
    return create_json_response({"message": "Backend is running successfully!"})

# PDF processing endpoint
@app.route('/api/process', methods=['POST'])
async def process_pdf():
    """Handle PDF file processing request."""
    try:
        # Get the file directly from the request
        files = await request.files
        file = None
        if 'file' in files:
            file = files['file']
        
        print(f"Received file: {file.filename if file else 'None'}")
        
        # Basic validation
        if not file:
            return create_json_response({
                "error": "Validation error",
                "message": "No file provided",
                "details": "Request must include a PDF file with key 'file'"
            }, 400)
            
        # Validate file is a PDF
        if not file.filename.lower().endswith('.pdf'):
            return create_json_response({
                "error": "Validation error",
                "message": "Invalid file type",
                "details": "Only PDF files are supported"
            }, 400)
        
        # Process the PDF file
        try:
            # Extract text from PDF
            result = await process_single_file(file)
            
            # If processing was successful, extract names from the content
            if "processedContent" in result:
                # Extract names and assets using DeepSeek
                extraction_result = deepseek_processor.extract_items(result["processedContent"])
                
                # Add extracted information to the result
                result["extractedNames"] = {
                    "items": extraction_result["names"],
                    "count": extraction_result["namesCount"],
                    "reasoning": extraction_result["reasoning"]
                }
                
                # Add extracted assets to the result
                result["extractedAssets"] = {
                    "items": extraction_result["assets"],
                    "count": extraction_result["assetsCount"],
                    "reasoning": extraction_result["reasoning"]
                }
            
            print(f"Result received from process_single_file: {json.dumps(result, indent=2)}")
            
            return create_json_response({
                "success": True,
                "data": result,
                "status": "completed",
                "message": "PDF processing completed successfully"
            })
            
        except Exception as e:
            error_message = str(e)
            print(f"Error processing PDF file: {error_message}")
            
            return create_json_response({
                "error": "Processing error",
                "message": error_message,
                "details": "Failed to process PDF file"
            }, 500)
            
    except Exception as e:
        error_message = str(e)
        print(f"Unexpected error in process_pdf: {error_message}")
        return create_json_response({
            "error": "Server error",
            "message": "An unexpected error occurred",
            "details": error_message
        }, 500)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 