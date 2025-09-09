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
            result_data = stream_asset.get_input_stream().read()
            
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

# Initialize OCR processor
try:
    ocr_processor = OCRWebhook()
except Exception as e:
    logger.error(f"Failed to initialize OCR processor: {e}")
    ocr_processor = None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "ocr_available": ocr_processor is not None})

@app.route('/ocr', methods=['POST'])
def process_ocr():
    """
    Main OCR endpoint for Zapier webhook
    Expects JSON with 'pdf_data' (base64 encoded) and optional 'locale', 'ocr_type'
    """
    try:
        if not ocr_processor:
            return jsonify({"error": "OCR service not available"}), 500

        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Extract PDF data (base64 encoded)
        pdf_data_b64 = data.get('pdf_data')
        if not pdf_data_b64:
            return jsonify({"error": "No pdf_data provided"}), 400

        # Decode base64 PDF data
        try:
            pdf_data = base64.b64decode(pdf_data_b64)
        except Exception as e:
            return jsonify({"error": f"Invalid base64 PDF data: {str(e)}"}), 400

        # Get optional parameters
        locale = data.get('locale', 'en-US')
        ocr_type = data.get('ocr_type', 'SEARCHABLE_IMAGE')
        
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
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
