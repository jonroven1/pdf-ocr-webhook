import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';
import * as cors from 'cors';

// Initialize Firebase Admin
admin.initializeApp();

// CORS middleware
const corsHandler = cors({ origin: true });

// Import Adobe PDF Services
import { ServicePrincipalCredentials } from 'pdfservices-sdk/operation/auth/service_principal_credentials';
import { PDFServices } from 'pdfservices-sdk/operation/pdf_services';
import { PDFServicesMediaType } from 'pdfservices-sdk/operation/pdf_services_media_type';
import { OCRPDFJob } from 'pdfservices-sdk/operation/pdfjobs/jobs/ocr_pdf_job';
import { OCRParams } from 'pdfservices-sdk/operation/pdfjobs/params/ocr_pdf/ocr_params';
import { OCRSupportedLocale } from 'pdfservices-sdk/operation/pdfjobs/params/ocr_pdf/ocr_supported_locale';
import { OCRSupportedType } from 'pdfservices-sdk/operation/pdfjobs/params/ocr_pdf/ocr_supported_type';
import { OCRPDFResult } from 'pdfservices-sdk/operation/pdfjobs/result/ocr_pdf_result';
import { CloudAsset } from 'pdfservices-sdk/operation/io/cloud_asset';
import { StreamAsset } from 'pdfservices-sdk/operation/io/stream_asset';

// OCR Webhook Class
class OCRWebhook {
  private pdfServices: PDFServices;

  constructor() {
    const clientId = functions.config().adobe?.client_id;
    const clientSecret = functions.config().adobe?.client_secret;

    if (!clientId || !clientSecret) {
      throw new Error('Adobe PDF Services credentials not configured');
    }

    const credentials = new ServicePrincipalCredentials(clientId, clientSecret);
    this.pdfServices = new PDFServices(credentials);
  }

  async processPDFOCR(pdfData: Buffer, locale: string = 'en-US', ocrType: string = 'SEARCHABLE_IMAGE'): Promise<Buffer> {
    let inputAsset: CloudAsset | null = null;
    let resultAsset: CloudAsset | null = null;

    try {
      // Upload PDF to Adobe services
      inputAsset = await this.pdfServices.upload(pdfData, PDFServicesMediaType.PDF);

      // Configure OCR parameters
      const ocrParams = new OCRParams(
        OCRSupportedLocale[locale.toUpperCase().replace('-', '_') as keyof typeof OCRSupportedLocale],
        OCRSupportedType[ocrType as keyof typeof OCRSupportedType]
      );

      // Create and submit OCR job
      const ocrJob = new OCRPDFJob(inputAsset, ocrParams);
      const location = await this.pdfServices.submit(ocrJob);
      const response = await this.pdfServices.getJobResult(location, OCRPDFResult);

      // Get the result
      resultAsset = response.getResult().getAsset();
      const streamAsset: StreamAsset = await this.pdfServices.getContent(resultAsset);
      
      // Read the result data before cleanup
      const resultData = await streamAsset.getInputStream();
      const buffer = Buffer.from(await resultData.arrayBuffer());
      
      // Clean up assets immediately after processing
      await this.cleanupAssets(inputAsset, resultAsset);
      
      return buffer;

    } catch (error) {
      // Still attempt cleanup even on error
      if (inputAsset || resultAsset) {
        await this.cleanupAssets(inputAsset, resultAsset);
      }
      throw error;
    }
  }

  private async cleanupAssets(inputAsset: CloudAsset | null, resultAsset: CloudAsset | null): Promise<void> {
    try {
      if (inputAsset) {
        console.log(`Cleaning up input asset: ${inputAsset.getAssetId()}`);
        await this.pdfServices.deleteAsset(inputAsset);
      }
      
      if (resultAsset) {
        console.log(`Cleaning up result asset: ${resultAsset.getAssetId()}`);
        await this.pdfServices.deleteAsset(resultAsset);
      }
      
      console.log('Asset cleanup completed successfully');
    } catch (error) {
      console.warn(`Asset cleanup failed (non-critical): ${error}`);
    }
  }
}

// Initialize OCR processor
let ocrProcessor: OCRWebhook | null = null;
try {
  ocrProcessor = new OCRWebhook();
} catch (error) {
  console.error(`Failed to initialize OCR processor: ${error}`);
}

// Health check endpoint
export const health = functions.https.onRequest((req, res) => {
  corsHandler(req, res, () => {
    res.json({
      status: 'healthy',
      ocr_available: ocrProcessor !== null,
      timestamp: new Date().toISOString()
    });
  });
});

// Main OCR endpoint
export const ocr = functions.https.onRequest((req, res) => {
  corsHandler(req, res, async () => {
    try {
      if (!ocrProcessor) {
        res.status(500).json({ error: 'OCR service not available' });
        return;
      }

      if (req.method !== 'POST') {
        res.status(405).json({ error: 'Method not allowed' });
        return;
      }

      const { pdf_data, locale = 'en-US', ocr_type = 'SEARCHABLE_IMAGE' } = req.body;

      if (!pdf_data) {
        res.status(400).json({ error: 'No pdf_data provided' });
        return;
      }

      // Decode base64 PDF data
      let pdfData: Buffer;
      try {
        pdfData = Buffer.from(pdf_data, 'base64');
      } catch (error) {
        res.status(400).json({ error: `Invalid base64 PDF data: ${error}` });
        return;
      }

      // Process PDF with OCR
      console.log(`Processing PDF with locale: ${locale}, type: ${ocr_type}`);
      const ocrResult = await ocrProcessor.processPDFOCR(pdfData, locale, ocr_type);
      
      // Encode result as base64 for return
      const resultB64 = ocrResult.toString('base64');
      
      res.json({
        success: true,
        ocr_pdf_data: resultB64,
        original_size: pdfData.length,
        processed_size: ocrResult.length,
        timestamp: new Date().toISOString(),
        assets_cleaned: true
      });

    } catch (error) {
      console.error(`OCR processing error: ${error}`);
      res.status(500).json({ error: `OCR processing failed: ${error}` });
    }
  });
});

// File upload endpoint (alternative)
export const ocrFile = functions.https.onRequest((req, res) => {
  corsHandler(req, res, async () => {
    try {
      if (!ocrProcessor) {
        res.status(500).json({ error: 'OCR service not available' });
        return;
      }

      if (req.method !== 'POST') {
        res.status(405).json({ error: 'Method not allowed' });
        return;
      }

      // This would require multipart form handling
      // For now, we'll redirect to the JSON endpoint
      res.status(400).json({ 
        error: 'File upload not supported in this version. Use the /ocr endpoint with base64 data.' 
      });

    } catch (error) {
      console.error(`OCR file processing error: ${error}`);
      res.status(500).json({ error: `OCR processing failed: ${error}` });
    }
  });
});
