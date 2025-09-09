# Zapier PDF OCR Automation Setup Guide

This guide will help you set up an automated OCR workflow that processes PDFs from emails using Adobe PDF Services and Zapier.

## Overview

The workflow will:
1. Trigger when you receive an email with a PDF attachment
2. Send the PDF to a webhook for OCR processing
3. Return the OCR'd (searchable) PDF back to you

## Prerequisites

- Adobe PDF Services API credentials (already configured in your `pdfservices-api-credentials.json`)
- A Heroku account (free tier works)
- A Zapier account (free tier works)

## Step 1: Deploy the Webhook to Heroku

### 1.1 Install Heroku CLI
```bash
# On macOS with Homebrew
brew install heroku/brew/heroku

# Or download from https://devcenter.heroku.com/articles/heroku-cli
```

### 1.2 Login to Heroku
```bash
heroku login
```

### 1.3 Create a new Heroku app
```bash
cd /Users/jonathanroven/Downloads/PDFServicesSDK-PythonSamples
heroku create your-pdf-ocr-webhook
# Replace 'your-pdf-ocr-webhook' with a unique name
```

### 1.4 Set up environment variables
```bash
# Set your Adobe PDF Services credentials
heroku config:set PDF_SERVICES_CLIENT_ID=bc4b6b89bfc1457b89ed7a2ef920ccbe
heroku config:set PDF_SERVICES_CLIENT_SECRET=p8e-XfFf7D42xo0wSNaDAWHgEIapRRd_N1ed
```

### 1.5 Deploy the app
```bash
git init
git add .
git commit -m "Initial commit"
git push heroku main
```

### 1.6 Test the deployment
```bash
# Check if the app is running
heroku open

# Test the health endpoint
curl https://your-pdf-ocr-webhook.herokuapp.com/health
```

## Step 2: Configure Zapier

### 2.1 Create a New Zap

1. Go to [Zapier.com](https://zapier.com) and create a new Zap
2. Choose **Gmail** as the trigger app
3. Select **"New Email"** as the trigger event
4. Connect your Gmail account
5. Set up the trigger with these filters:
   - **Has Attachment**: Yes
   - **Attachment Type**: PDF

### 2.2 Add Webhook Action

1. Choose **Webhooks by Zapier** as the action app
2. Select **"POST"** as the action event
3. Configure the webhook:
   - **URL**: `https://your-pdf-ocr-webhook.herokuapp.com/ocr`
   - **Method**: POST
   - **Headers**: 
     - `Content-Type: application/json`
   - **Data**: 
     ```json
     {
       "pdf_data": "{{attachment_content}}",
       "locale": "en-US",
       "ocr_type": "SEARCHABLE_IMAGE"
     }
     ```

### 2.3 Add Email Action (Send OCR'd PDF back)

1. Add another action step
2. Choose **Gmail** as the action app
3. Select **"Send Email"** as the action event
4. Configure the email:
   - **To**: Your email address
   - **Subject**: "OCR'd PDF: {{subject}}"
   - **Body**: 
     ```
     Hi,
     
     Your PDF has been processed with OCR and is now searchable.
     
     Original email: {{subject}}
     Processed on: {{zap_meta_human_now}}
     
     Best regards,
     Your PDF OCR Bot
     ```
   - **Attachments**: 
     - **File Name**: `ocr_{{attachment_name}}`
     - **File Content**: `{{ocr_pdf_data}}` (from webhook response)

### 2.4 Test and Turn On

1. Test each step of your Zap
2. Once everything works, turn on the Zap

## Step 3: Alternative Setup (Using File Upload Endpoint)

If you prefer to use the file upload endpoint instead of base64 encoding:

### 3.1 Modify the Webhook Action

- **URL**: `https://your-pdf-ocr-webhook.herokuapp.com/ocr-file`
- **Method**: POST
- **Data**: 
  - **file**: `{{attachment_file}}`
  - **locale**: `en-US`
  - **ocr_type**: `SEARCHABLE_IMAGE`

## Step 4: Advanced Configuration

### 4.1 OCR Options

You can customize the OCR processing by modifying the webhook data:

- **locale**: Language for OCR (e.g., "en-US", "es-ES", "fr-FR")
- **ocr_type**: 
  - `SEARCHABLE_IMAGE`: Keeps original image, adds searchable text layer
  - `SEARCHABLE_IMAGE_EXACT`: Maximum fidelity to original image
  - `SEARCHABLE_IMAGE_EDITABLE`: Creates editable text

### 4.2 Error Handling

The webhook includes error handling and will return appropriate error messages if:
- PDF processing fails
- Invalid file format
- Adobe API errors
- Service unavailable

## Step 5: Monitoring and Maintenance

### 5.1 Check Logs
```bash
heroku logs --tail
```

### 5.2 Monitor Usage
- Check your Adobe PDF Services usage in the Adobe Developer Console
- Monitor Heroku app performance in the Heroku dashboard

### 5.3 Troubleshooting

Common issues:
1. **Webhook timeout**: Large PDFs may take time to process
2. **Memory limits**: Heroku free tier has memory constraints
3. **API limits**: Adobe PDF Services has usage limits

## Security & Privacy Features

- **Automatic Asset Cleanup**: All uploaded PDFs and processed results are automatically deleted from Adobe's servers immediately after processing
- **Secure Credentials**: Your Adobe credentials are stored as environment variables (secure)
- **No Data Persistence**: The webhook doesn't store any files locally or in the cloud
- **Public Endpoint**: The webhook is public but only processes valid PDFs
- **Consider Authentication**: Add authentication if needed for production use

## Cost Considerations

- **Heroku**: Free tier includes 550-1000 dyno hours per month
- **Adobe PDF Services**: Pay-per-use pricing (check current rates)
- **Zapier**: Free tier includes 100 tasks per month

## Support

If you encounter issues:
1. Check the Heroku logs for webhook errors
2. Verify your Adobe PDF Services credentials
3. Test the webhook directly using curl or Postman
4. Check Zapier's task history for failed runs
