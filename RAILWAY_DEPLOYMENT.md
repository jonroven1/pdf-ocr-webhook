# Railway Deployment - Easiest Solution for PDF OCR Webhook

Railway is the simplest and most reliable way to deploy your PDF OCR webhook. Here's the complete setup:

## Why Railway?

- ✅ **Zero configuration** - Just connect GitHub and deploy
- ✅ **Automatic HTTPS** - Secure endpoints out of the box
- ✅ **Environment variables** - Easy credential management
- ✅ **Auto-scaling** - Handles traffic spikes automatically
- ✅ **Free tier** - $5 credit monthly, perfect for testing
- ✅ **No Git version issues** - Works with any Git version

## Step 1: Push to GitHub

### 1.1 Create GitHub Repository
1. Go to [GitHub.com](https://github.com) and create a new repository
2. Name it: `pdf-ocr-webhook`
3. Make it public (for free Railway deployment)

### 1.2 Push Your Code
```bash
cd /Users/jonathanroven/Downloads/PDFServicesSDK-PythonSamples

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "PDF OCR webhook with automatic asset cleanup"

# Add GitHub remote (replace with your actual repo URL)
git remote add origin https://github.com/yourusername/pdf-ocr-webhook.git

# Push to GitHub
git push -u origin main
```

## Step 2: Deploy to Railway

### 2.1 Sign Up for Railway
1. Go to [railway.app](https://railway.app)
2. Sign up with your GitHub account
3. Authorize Railway to access your repositories

### 2.2 Deploy Your Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your `pdf-ocr-webhook` repository
4. Railway will automatically detect it's a Python project

### 2.3 Configure Environment Variables
In Railway dashboard:
1. Go to your project → Variables tab
2. Add these environment variables:
   ```
   PDF_SERVICES_CLIENT_ID=bc4b6b89bfc1457b89ed7a2ef920ccbe
   PDF_SERVICES_CLIENT_SECRET=p8e-XfFf7D42xo0wSNaDAWHgEIapRRd_N1ed
   PORT=5000
   ```

### 2.4 Deploy
Railway will automatically:
- Install dependencies from `webhook_requirements.txt`
- Start your webhook using the `Procfile`
- Provide you with a public URL

## Step 3: Get Your Webhook URL

After deployment, Railway will give you a URL like:
```
https://pdf-ocr-webhook-production-xxxx.up.railway.app
```

Your endpoints will be:
- **Health Check**: `https://pdf-ocr-webhook-production-xxxx.up.railway.app/health`
- **OCR Endpoint**: `https://pdf-ocr-webhook-production-xxxx.up.railway.app/ocr`

## Step 4: Test Your Deployment

### 4.1 Health Check
```bash
curl https://pdf-ocr-webhook-production-xxxx.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "ocr_available": true,
  "timestamp": "2024-01-09T20:30:00.000Z"
}
```

### 4.2 Test OCR Processing
```bash
curl -X POST https://pdf-ocr-webhook-production-xxxx.up.railway.app/ocr \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_data": "JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PAovVHlwZSAvUGFnZQovUGFyZW50IDMgMCBSCi9NZWRpYUJveCBbMCAwIDYxMiA3OTJdCi9SZXNvdXJjZXMgPDwKL0ZvbnQgPDwKL0YxIDIgMCBSCj4+Cj4+Ci9Db250ZW50cyA0IDAgUgo+PgplbmRvYmoKNiAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9IZWx2ZXRpY2EKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL0ZvbnQKL1N1YnR5cGUgL1R5cGUxCi9CYXNlRm9udCAvSGVsdmV0aWNhCj4+CmVuZG9iago0IDAgb2JqCjw8Ci9MZW5ndGggNDQKPj4Kc3RyZWFtCkJUCi9GMSAxMiBUZgoyNTAgNzAwIFRkCihIZWxsbyBXb3JsZCkgVGoKRVQKZW5kc3RyZWFtCmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9QYWdlcwovQ291bnQgMQovS2lkcyBbNSAwIFJdCj4+CmVuZG9iagoxIDAgb2JqCjw8Ci9UeXBlIC9DYXRhbG9nCi9QYWdlcyAzIDAgUgo+PgplbmRvYmoKeHJlZgowIDcKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBuIAowMDAwMDAwMjQ5IDAwMDAwIG4gCjAwMDAwMDAzMjggMDAwMDAgbiAKMDAwMDAwMDQwNyAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDcKL1Jvb3QgMSAwIFIKPj4Kc3RhcnR4cmVmCjQ5NQolJUVPRgo=",
    "locale": "en-US",
    "ocr_type": "SEARCHABLE_IMAGE"
  }'
```

## Step 5: Configure Zapier

### 5.1 Create New Zap
1. **Trigger**: Gmail → New Email (with PDF attachment)
2. **Action**: Webhooks by Zapier → POST
   - **URL**: `https://pdf-ocr-webhook-production-xxxx.up.railway.app/ocr`
   - **Method**: POST
   - **Headers**: `Content-Type: application/json`
   - **Data**:
     ```json
     {
       "pdf_data": "{{attachment_content}}",
       "locale": "en-US",
       "ocr_type": "SEARCHABLE_IMAGE"
     }
     ```

### 5.2 Add Email Action
1. **Action**: Gmail → Send Email
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
     - **File Content**: `{{ocr_pdf_data}}`

## Step 6: Monitor and Maintain

### 6.1 Railway Dashboard
- Monitor usage and performance
- View logs in real-time
- Check deployment status

### 6.2 Cost Management
- **Free tier**: $5 credit monthly
- **Usage**: ~$0.10 per 1,000 requests
- **Storage**: No persistent storage costs

### 6.3 Automatic Updates
Railway automatically redeploys when you push to GitHub:
```bash
git add .
git commit -m "Update webhook"
git push origin main
```

## Troubleshooting

### Common Issues

1. **Deployment fails**: Check Railway logs for dependency issues
2. **OCR not working**: Verify environment variables are set correctly
3. **Timeout errors**: Large PDFs may need more processing time

### Debug Commands
```bash
# Check Railway logs
railway logs

# Test locally first
python webhook_ocr.py
curl http://localhost:5001/health
```

## Benefits of Railway vs Firebase

| Feature | Railway | Firebase |
|---------|---------|----------|
| Setup Time | 5 minutes | 30+ minutes |
| Git Compatibility | Any version | Specific versions |
| Python Support | Native | Complex setup |
| Environment Variables | Easy UI | CLI commands |
| Logs | Real-time UI | CLI only |
| Cost | $5/month credit | Pay-per-use |

## Your Complete Workflow

1. **Email arrives** with PDF attachment
2. **Zapier triggers** and sends PDF to your Railway webhook
3. **Webhook processes** PDF with Adobe OCR
4. **Assets cleaned up** automatically for security
5. **OCR'd PDF returned** to Zapier
6. **Email sent** with searchable PDF attachment

Your PDF OCR automation is now live and ready to process emails automatically!

## Next Steps

1. **Deploy to Railway** (5 minutes)
2. **Test the webhook** with a sample PDF
3. **Configure Zapier** with your Railway URL
4. **Send yourself a test email** with a PDF attachment
5. **Enjoy automated OCR processing!**

Railway is the fastest path to a working PDF OCR webhook. No Git version issues, no complex configuration - just connect GitHub and deploy!
