"""
Adobe PDF Services OCR Webhook for Zapier Integration
This script processes PDF files sent via webhook and returns OCR'd versions.
"""

import os
import json
import logging
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import tempfile
import requests

from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
from adobe.pdfservices.operation.io.stream_asset import StreamAsset
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.ocr_pdf_job import OCRPDFJob
from adobe.pdfservices.operation.pdfjobs.params.ocr_pdf.ocr_params import OCRParams
from adobe.pdfservices.operation.pdfjobs.params.ocr_pdf.ocr_supported_locale import OCRSupportedLocale
from adobe.pdfservices.operation.pdfjobs.params.ocr_pdf.ocr_supported_type import OCRSupportedType
from adobe.pdfservices.operation.pdfjobs.result.ocr_pdf_result import OCRPDFResult

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRWebhook:
    def __init__(self):
        # Initialize Adobe PDF Services credentials
        self.client_id = os.getenv('PDF_SERVICES_CLIENT_ID')
        self.client_secret = os.getenv('PDF_SERVICES_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("PDF_SERVICES_CLIENT_ID and PDF_SERVICES_CLIENT_SECRET environment variables must be set")
        
        self.credentials = ServicePrincipalCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self.pdf_services = PDFServices(credentials=self.credentials)

    def process_pdf_ocr(self, pdf_data, locale='en-US', ocr_type='SEARCHABLE_IMAGE'):
        """
        Process PDF with OCR and return the result as bytes
        Automatically cleans up assets after processing
        """
        input_asset = None
        result_asset = None
        
        try:
            # Upload PDF to Adobe services
            input_asset = self.pdf_services.upload(
                input_stream=pdf_data,
                mime_type=PDFServicesMediaType.PDF
            )

            # Configure OCR parameters
            ocr_pdf_params = OCRParams(
                ocr_locale=getattr(OCRSupportedLocale, locale.upper().replace('-', '_')),
                ocr_type=getattr(OCRSupportedType, ocr_type)
            )

            # Create and submit OCR job
            ocr_pdf_job = OCRPDFJob(input_asset=input_asset, ocr_pdf_params=ocr_pdf_params)
            location = self.pdf_services.submit(ocr_pdf_job)
            pdf_services_response = self.pdf_services.get_job_result(location, OCRPDFResult)

            # Get the result
            result_asset: CloudAsset = pdf_services_response.get_result().get_asset()
            stream_asset: StreamAsset = self.pdf_services.get_content(result_asset)
            
            # Read the result data before cleanup
            result_data = stream_asset.get_input_stream()
            
            # Clean up assets immediately after processing
            self._cleanup_assets(input_asset, result_asset)
            
            return result_data

        except (ServiceApiException, ServiceUsageException, SdkException) as e:
            logger.error(f'Adobe PDF Services error: {e}')
            # Still attempt cleanup even on error
            if input_asset or result_asset:
                self._cleanup_assets(input_asset, result_asset)
            raise Exception(f"OCR processing failed: {str(e)}")
        except Exception as e:
            # Cleanup on any other error
            if input_asset or result_asset:
                self._cleanup_assets(input_asset, result_asset)
            raise e

    def _cleanup_assets(self, input_asset, result_asset):
        """
        Clean up Adobe PDF Services assets after processing
        """
        try:
            if input_asset:
                logger.info(f"Cleaning up input asset: {input_asset.asset_id}")
                self.pdf_services.delete_asset(input_asset)
                
            if result_asset:
                logger.info(f"Cleaning up result asset: {result_asset.asset_id}")
                self.pdf_services.delete_asset(result_asset)
                
            logger.info("Asset cleanup completed successfully")
            
        except Exception as e:
            logger.warning(f"Asset cleanup failed (non-critical): {str(e)}")
            # Don't raise the exception as cleanup failure shouldn't break the main flow

    def _list_dropbox_files(self, folder_path="/0 - MAIL ROOM"):
        """
        List files in Dropbox folder
        """
        try:
            dropbox_token = os.getenv('DROPBOX_ACCESS_TOKEN')
            if not dropbox_token:
                logger.warning("No Dropbox access token provided")
                return []
                
            # Dropbox API endpoint for listing files
            url = "https://api.dropboxapi.com/2/files/list_folder"
            
            headers = {
                "Authorization": f"Bearer {dropbox_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "path": folder_path,
                "recursive": False
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                files = []
                for entry in result.get('entries', []):
                    if entry.get('.tag') == 'file' and entry.get('name', '').lower().endswith('.pdf'):
                        files.append({
                            'name': entry['name'],
                            'path': entry['path_lower'],
                            'id': entry['id'],
                            'size': entry.get('size', 0),
                            'modified': entry.get('client_modified', entry.get('server_modified'))
                        })
                logger.info(f"Found {len(files)} PDF files in {folder_path}")
                return files
            else:
                logger.error(f"Failed to list Dropbox files: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing Dropbox files: {str(e)}")
            return []

    def _download_from_dropbox(self, file_path):
        """
        Download file from Dropbox
        """
        try:
            dropbox_token = os.getenv('DROPBOX_ACCESS_TOKEN')
            if not dropbox_token:
                logger.warning("No Dropbox access token provided")
                return None
                
            # Dropbox API endpoint for downloading files
            url = "https://content.dropboxapi.com/2/files/download"
            
            headers = {
                "Authorization": f"Bearer {dropbox_token}",
                "Dropbox-API-Arg": json.dumps({"path": file_path})
            }
            
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Successfully downloaded {file_path}")
                return response.content
            else:
                logger.error(f"Failed to download {file_path}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading from Dropbox: {str(e)}")
            return None

    def _upload_to_dropbox(self, pdf_data, filename):
        """
        Upload OCR'd PDF directly to Dropbox
        """
        try:
            dropbox_token = os.getenv('DROPBOX_ACCESS_TOKEN')
            if not dropbox_token:
                logger.warning("No Dropbox access token provided")
                return None
                
            # Dropbox API endpoint
            url = "https://content.dropboxapi.com/2/files/upload"
            
            # Dropbox API arguments
            dropbox_args = {
                "path": f"/0 - MAIL ROOM/{filename}",
                "mode": "add",
                "autorename": True
            }
            
            headers = {
                "Authorization": f"Bearer {dropbox_token}",
                "Dropbox-API-Arg": json.dumps(dropbox_args),
                "Content-Type": "application/octet-stream"
            }
            
            # Upload the file
            response = requests.post(url, headers=headers, data=pdf_data)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully uploaded to Dropbox: {result.get('path_display', 'unknown')}")
                return result.get('path_display', result.get('path_lower'))
            else:
                logger.error(f"Dropbox upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Dropbox upload error: {str(e)}")
            return None

# Initialize OCR processor
try:
    ocr_processor = OCRWebhook()
except Exception as e:
    logger.error(f"Failed to initialize OCR processor: {e}")
    ocr_processor = None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Check if credentials are available
    client_id = os.getenv('PDF_SERVICES_CLIENT_ID')
    client_secret = os.getenv('PDF_SERVICES_CLIENT_SECRET')
    
    return jsonify({
        "status": "healthy",
        "ocr_available": ocr_processor is not None,
        "credentials_loaded": bool(client_id and client_secret),
        "client_id_set": bool(client_id),
        "client_secret_set": bool(client_secret)
    })

@app.route('/ocr', methods=['POST'])
def process_ocr():
    """
    Main OCR endpoint for Zapier webhook
    Expects JSON with 'pdf_data' (base64 encoded) and optional 'locale', 'ocr_type'
    """
    try:
        if not ocr_processor:
            return jsonify({"error": "OCR service not available"}), 500

        # Handle different content types
        data = None
        
        # Log the request details for debugging
        logger.info(f"Request content-type: {request.content_type}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # Try to get JSON data first
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            logger.info(f"JSON data keys: {list(data.keys()) if data else 'None'}")
        
        # If no JSON, try form data
        elif request.form:
            data = dict(request.form)
            logger.info(f"Form data keys: {list(data.keys())}")
        
        # If no form data, try raw data
        elif request.get_data():
            # Try to parse as JSON
            try:
                data = request.get_json(force=True)
                logger.info(f"Parsed JSON from raw data: {list(data.keys()) if data else 'None'}")
            except:
                logger.info("Could not parse as JSON, treating as raw data")
        
        logger.info(f"Files in request: {list(request.files.keys()) if request.files else 'None'}")

        # Extract PDF data - handle multiple formats
        pdf_data = None
        
        # Check if pdf_data is provided (base64 encoded)
        pdf_data_b64 = data.get('pdf_data') if data else None
        if pdf_data_b64:
            try:
                # Clean up base64 string (remove any whitespace/newlines)
                pdf_data_b64 = pdf_data_b64.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                
                # Add padding if needed
                missing_padding = len(pdf_data_b64) % 4
                if missing_padding:
                    pdf_data_b64 += '=' * (4 - missing_padding)
                
                # Try to decode as base64
                pdf_data = base64.b64decode(pdf_data_b64)
                
                # Validate that it's actually a PDF
                if not pdf_data.startswith(b'%PDF'):
                    return jsonify({"error": "Decoded data is not a valid PDF file"}), 400
                    
                logger.info(f"Successfully decoded PDF: {len(pdf_data)} bytes")
                
            except Exception as e:
                logger.error(f"Base64 decode error: {str(e)}")
                return jsonify({"error": f"Invalid base64 PDF data: {str(e)}"}), 400
        
        # Check if file is provided in request (for direct file uploads)
        elif 'file' in request.files:
            file = request.files['file']
            if file and file.filename.endswith('.pdf'):
                pdf_data = file.read()
        
        # Check if raw binary data is provided
        elif request.content_type and 'application/octet-stream' in request.content_type:
            pdf_data = request.get_data()
        
        if not pdf_data:
            return jsonify({"error": "No PDF data provided. Send 'pdf_data' (base64) or upload file directly"}), 400

        # Get optional parameters
        locale = data.get('locale', 'en-US') if data else 'en-US'
        ocr_type = data.get('ocr_type', 'SEARCHABLE_IMAGE') if data else 'SEARCHABLE_IMAGE'
        
        # Process PDF with OCR
        logger.info(f"Processing PDF with locale: {locale}, type: {ocr_type}")
        ocr_result = ocr_processor.process_pdf_ocr(pdf_data, locale, ocr_type)
        
        # Encode result as base64 for return
        result_b64 = base64.b64encode(ocr_result).decode('utf-8')
        
        return jsonify({
            "success": True,
            "ocr_pdf_data": result_b64,
            "original_size": len(pdf_data),
            "processed_size": len(ocr_result),
            "timestamp": datetime.now().isoformat(),
            "assets_cleaned": True
        })

    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        return jsonify({"error": f"OCR processing failed: {str(e)}"}), 500

@app.route('/ocr-download', methods=['POST'])
def process_ocr_download():
    """
    OCR endpoint that returns the actual PDF file for download
    """
    try:
        if not ocr_processor:
            return jsonify({"error": "OCR service not available"}), 500

        # Handle different content types
        data = None
        
        # Try to get JSON data first
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
        
        # If no JSON, try form data
        elif request.form:
            data = dict(request.form)
        
        # If no form data, try raw data
        elif request.get_data():
            try:
                data = request.get_json(force=True)
            except:
                pass

        # Extract PDF data - handle multiple formats
        pdf_data = None
        
        # Check if pdf_data is provided (base64 encoded)
        pdf_data_b64 = data.get('pdf_data') if data else None
        if pdf_data_b64:
            try:
                # Clean up base64 string
                pdf_data_b64 = pdf_data_b64.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                
                # Add padding if needed
                missing_padding = len(pdf_data_b64) % 4
                if missing_padding:
                    pdf_data_b64 += '=' * (4 - missing_padding)
                
                # Try to decode as base64
                pdf_data = base64.b64decode(pdf_data_b64)
                
                # Validate that it's actually a PDF
                if not pdf_data.startswith(b'%PDF'):
                    return jsonify({"error": "Decoded data is not a valid PDF file"}), 400
                    
            except Exception as e:
                return jsonify({"error": f"Invalid base64 PDF data: {str(e)}"}), 400
        
        # Check if file is provided in request
        elif 'file' in request.files:
            file = request.files['file']
            if file and file.filename.endswith('.pdf'):
                pdf_data = file.read()
        
        # Check if raw binary data is provided
        elif request.content_type and 'application/octet-stream' in request.content_type:
            pdf_data = request.get_data()
        
        if not pdf_data:
            return jsonify({"error": "No PDF data provided"}), 400

        # Get optional parameters
        locale = data.get('locale', 'en-US') if data else 'en-US'
        ocr_type = data.get('ocr_type', 'SEARCHABLE_IMAGE') if data else 'SEARCHABLE_IMAGE'
        
        # Process PDF with OCR
        ocr_result = ocr_processor.process_pdf_ocr(pdf_data, locale, ocr_type)
        
        # Return JSON with file data for Zapier compatibility
        result_b64 = base64.b64encode(ocr_result).decode('utf-8')
        filename = f"ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return jsonify({
            "success": True,
            "file_content": result_b64,
            "file_name": filename,
            "file_size": len(ocr_result),
            "mime_type": "application/pdf",
            "original_size": len(pdf_data),
            "processed_size": len(ocr_result),
            "timestamp": datetime.now().isoformat(),
            "assets_cleaned": True
        })

    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        return jsonify({"error": f"OCR processing failed: {str(e)}"}), 500

@app.route('/ocr-dropbox', methods=['POST'])
def process_ocr_dropbox():
    """
    OCR endpoint that automatically uploads the result to Dropbox
    """
    try:
        if not ocr_processor:
            return jsonify({"error": "OCR service not available"}), 500

        # Handle different content types
        data = None
        
        # Try to get JSON data first
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
        
        # If no JSON, try form data
        elif request.form:
            data = dict(request.form)
        
        # If no form data, try raw data
        elif request.get_data():
            try:
                data = request.get_json(force=True)
            except:
                pass

        # Extract PDF data - handle multiple formats
        pdf_data = None
        
        # Check if pdf_data is provided (base64 encoded)
        pdf_data_b64 = data.get('pdf_data') if data else None
        if pdf_data_b64:
            try:
                # Clean up base64 string
                pdf_data_b64 = pdf_data_b64.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                
                # Add padding if needed
                missing_padding = len(pdf_data_b64) % 4
                if missing_padding:
                    pdf_data_b64 += '=' * (4 - missing_padding)
                
                # Try to decode as base64
                pdf_data = base64.b64decode(pdf_data_b64)
                
                # Validate that it's actually a PDF
                if not pdf_data.startswith(b'%PDF'):
                    return jsonify({"error": "Decoded data is not a valid PDF file"}), 400
                    
            except Exception as e:
                return jsonify({"error": f"Invalid base64 PDF data: {str(e)}"}), 400
        
        # Check if file is provided in request
        elif 'file' in request.files:
            file = request.files['file']
            if file and file.filename.endswith('.pdf'):
                pdf_data = file.read()
        
        # Check if raw binary data is provided
        elif request.content_type and 'application/octet-stream' in request.content_type:
            pdf_data = request.get_data()
        
        if not pdf_data:
            return jsonify({"error": "No PDF data provided"}), 400

        # Get optional parameters
        locale = data.get('locale', 'en-US') if data else 'en-US'
        ocr_type = data.get('ocr_type', 'SEARCHABLE_IMAGE') if data else 'SEARCHABLE_IMAGE'
        
        # Process PDF with OCR
        ocr_result = ocr_processor.process_pdf_ocr(pdf_data, locale, ocr_type)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ocr_{timestamp}.pdf"
        
        # Upload to Dropbox
        dropbox_path = ocr_processor._upload_to_dropbox(ocr_result, filename)
        
        return jsonify({
            "success": True,
            "message": "PDF processed and uploaded to Dropbox",
            "dropbox_path": dropbox_path,
            "filename": filename,
            "original_size": len(pdf_data),
            "processed_size": len(ocr_result),
            "timestamp": datetime.now().isoformat(),
            "assets_cleaned": True
        })

    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        return jsonify({"error": f"OCR processing failed: {str(e)}"}), 500

@app.route('/check-mailroom', methods=['POST', 'GET'])
def check_mailroom():
    """
    Check /0 - MAIL ROOM folder for new PDFs and OCR them automatically
    """
    try:
        if not ocr_processor:
            return jsonify({"error": "OCR service not available"}), 500

        # List all PDF files in the mail room
        files = ocr_processor._list_dropbox_files("/0 - MAIL ROOM")
        
        if not files:
            return jsonify({
                "message": "No PDF files found in /0 - MAIL ROOM",
                "processed_count": 0
            })
        
        processed_count = 0
        results = []
        
        for file_info in files:
            try:
                # Download the PDF
                pdf_data = ocr_processor._download_from_dropbox(file_info['path'])
                
                if not pdf_data:
                    logger.error(f"Failed to download {file_info['name']}")
                    continue
                
                # Check if it's already OCR'd (look for "ocr_" prefix)
                if file_info['name'].startswith('ocr_'):
                    logger.info(f"Skipping {file_info['name']} - already OCR'd")
                    continue
                
                # Process with OCR
                logger.info(f"Processing {file_info['name']} with OCR")
                ocr_result = ocr_processor.process_pdf_ocr(pdf_data, 'en-US', 'SEARCHABLE_IMAGE')
                
                # Create OCR'd filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                ocr_filename = f"ocr_{timestamp}_{file_info['name']}"
                
                # Upload OCR'd version back to the same folder
                ocr_path = ocr_processor._upload_to_dropbox(ocr_result, ocr_filename)
                
                if ocr_path:
                    processed_count += 1
                    results.append({
                        "original": file_info['name'],
                        "ocr_file": ocr_filename,
                        "dropbox_path": ocr_path,
                        "status": "success"
                    })
                    logger.info(f"Successfully processed {file_info['name']} -> {ocr_filename}")
                else:
                    results.append({
                        "original": file_info['name'],
                        "status": "failed - upload error"
                    })
                    
            except Exception as e:
                logger.error(f"Error processing {file_info['name']}: {str(e)}")
                results.append({
                    "original": file_info['name'],
                    "status": f"failed - {str(e)}"
                })
        
        return jsonify({
            "message": f"Mail room check completed",
            "total_files": len(files),
            "processed_count": processed_count,
            "results": results,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Mail room check error: {str(e)}")
        return jsonify({"error": f"Mail room check failed: {str(e)}"}), 500

@app.route('/ocr-file', methods=['POST'])
def process_ocr_file():
    """
    Alternative endpoint that accepts file uploads directly
    """
    try:
        if not ocr_processor:
            return jsonify({"error": "OCR service not available"}), 500

        # Check if file is present
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Check if it's a PDF
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "File must be a PDF"}), 400

        # Read file data
        pdf_data = file.read()
        
        # Get optional parameters from form data
        locale = request.form.get('locale', 'en-US')
        ocr_type = request.form.get('ocr_type', 'SEARCHABLE_IMAGE')
        
        # Process PDF with OCR
        logger.info(f"Processing PDF file: {file.filename}")
        ocr_result = ocr_processor.process_pdf_ocr(pdf_data, locale, ocr_type)
        
        # Create temporary file for response
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(ocr_result)
            tmp_file_path = tmp_file.name

        return send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=f"ocr_{secure_filename(file.filename)}",
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"OCR file processing error: {str(e)}")
        return jsonify({"error": f"OCR processing failed: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))  # Changed default port to avoid AirPlay conflict
    app.run(host='0.0.0.0', port=port, debug=False)
