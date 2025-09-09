"""
Firebase Functions for PDF OCR Webhook
Python-based implementation using Adobe PDF Services SDK
"""

import functions_framework
import json
import base64
import logging
from datetime import datetime

# Import Adobe PDF Services
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRWebhook:
    def __init__(self):
        # Get credentials from environment variables
        import os
        client_id = os.getenv('PDF_SERVICES_CLIENT_ID')
        client_secret = os.getenv('PDF_SERVICES_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError("PDF_SERVICES_CLIENT_ID and PDF_SERVICES_CLIENT_SECRET environment variables must be set")
        
        self.credentials = ServicePrincipalCredentials(client_id, client_secret)
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

# Initialize OCR processor
try:
    ocr_processor = OCRWebhook()
except Exception as e:
    logger.error(f"Failed to initialize OCR processor: {e}")
    ocr_processor = None

@functions_framework.http
def health(request):
    """Health check endpoint"""
    # Handle CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*'
    }
    
    return (json.dumps({
        "status": "healthy",
        "ocr_available": ocr_processor is not None,
        "timestamp": datetime.now().isoformat()
    }), 200, headers)

@functions_framework.http
def ocr(request):
    """
    Main OCR endpoint for Zapier webhook
    Expects JSON with 'pdf_data' (base64 encoded) and optional 'locale', 'ocr_type'
    """
    # Handle CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*'
    }
    
    try:
        if not ocr_processor:
            return (json.dumps({"error": "OCR service not available"}), 500, headers)

        if request.method != 'POST':
            return (json.dumps({"error": "Method not allowed"}), 405, headers)

        # Get JSON data from request
        data = request.get_json()
        if not data:
            return (json.dumps({"error": "No JSON data provided"}), 400, headers)

        # Extract PDF data (base64 encoded)
        pdf_data_b64 = data.get('pdf_data')
        if not pdf_data_b64:
            return (json.dumps({"error": "No pdf_data provided"}), 400, headers)

        # Decode base64 PDF data
        try:
            pdf_data = base64.b64decode(pdf_data_b64)
        except Exception as e:
            return (json.dumps({"error": f"Invalid base64 PDF data: {str(e)}"}), 400, headers)

        # Get optional parameters
        locale = data.get('locale', 'en-US')
        ocr_type = data.get('ocr_type', 'SEARCHABLE_IMAGE')
        
        # Process PDF with OCR
        logger.info(f"Processing PDF with locale: {locale}, type: {ocr_type}")
        ocr_result = ocr_processor.process_pdf_ocr(pdf_data, locale, ocr_type)
        
        # Encode result as base64 for return
        result_b64 = base64.b64encode(ocr_result).decode('utf-8')
        
        return (json.dumps({
            "success": True,
            "ocr_pdf_data": result_b64,
            "original_size": len(pdf_data),
            "processed_size": len(ocr_result),
            "timestamp": datetime.now().isoformat(),
            "assets_cleaned": True
        }), 200, headers)

    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        return (json.dumps({"error": f"OCR processing failed: {str(e)}"}), 500, headers)
