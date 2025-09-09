# Firebase Functions Setup for PDF OCR Webhook

This guide will help you deploy your PDF OCR webhook using Firebase Functions, which is an excellent choice for serverless webhook hosting.

## Why Firebase Functions?

- ✅ **Serverless**: Pay only for what you use
- ✅ **Automatic scaling**: Handles traffic spikes automatically
- ✅ **Global CDN**: Fast response times worldwide
- ✅ **Easy deployment**: Simple CLI commands
- ✅ **Built-in HTTPS**: Secure by default
- ✅ **Free tier**: Generous free usage limits

## Prerequisites

- Firebase CLI installed (✅ you have version 14.2.1)
- Node.js 18+ installed
- A Google account

## Step 1: Create Firebase Project

### 1.1 Create Project in Firebase Console
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project"
3. Enter project name: `pdf-ocr-webhook` (or your preferred name)
4. Enable Google Analytics (optional)
5. Click "Create project"

### 1.2 Initialize Firebase in Your Directory
```bash
cd /Users/jonathanroven/Downloads/PDFServicesSDK-PythonSamples
firebase login
firebase init
```

When prompted:
- **Select features**: Functions, Hosting
- **Select project**: Choose the project you just created
- **Language**: TypeScript
- **ESLint**: No (for simplicity)
- **Install dependencies**: Yes

### 1.3 Update Project ID
Edit `.firebaserc` and replace `your-project-id` with your actual project ID:
```json
{
  "projects": {
    "default": "your-actual-project-id"
  }
}
```

## Step 2: Install Dependencies

```bash
cd firebase_functions
npm install
```

## Step 3: Configure Adobe PDF Services Credentials

### 3.1 Set Environment Variables
```bash
firebase functions:config:set adobe.client_id="bc4b6b89bfc1457b89ed7a2ef920ccbe"
firebase functions:config:set adobe.client_secret="p8e-XfFf7D42xo0wSNaDAWHgEIapRRd_N1ed"
```

### 3.2 Verify Configuration
```bash
firebase functions:config:get
```

## Step 4: Deploy to Firebase

### 4.1 Build and Deploy
```bash
cd ..
firebase deploy --only functions
```

### 4.2 Deploy Hosting (Optional - for custom domain)
```bash
firebase deploy --only hosting
```

## Step 5: Test Your Deployment

### 5.1 Health Check
```bash
curl https://your-project-id-default-rtdb.firebaseapp.com/health
```

### 5.2 Test OCR Endpoint
```bash
# Test with a sample PDF (base64 encoded)
curl -X POST https://your-project-id-default-rtdb.firebaseapp.com/ocr \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_data": "JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PAovVHlwZSAvUGFnZQovUGFyZW50IDMgMCBSCi9NZWRpYUJveCBbMCAwIDYxMiA3OTJdCi9SZXNvdXJjZXMgPDwKL0ZvbnQgPDwKL0YxIDIgMCBSCj4+Cj4+Ci9Db250ZW50cyA0IDAgUgo+PgplbmRvYmoKNiAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9IZWx2ZXRpY2EKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL0ZvbnQKL1N1YnR5cGUgL1R5cGUxCi9CYXNlRm9udCAvSGVsdmV0aWNhCj4+CmVuZG9iago0IDAgb2JqCjw8Ci9MZW5ndGggNDQKPj4Kc3RyZWFtCkJUCi9GMSAxMiBUZgoyNTAgNzAwIFRkCihIZWxsbyBXb3JsZCkgVGoKRVQKZW5kc3RyZWFtCmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9QYWdlcwovQ291bnQgMQovS2lkcyBbNSAwIFJdCj4+CmVuZG9iagoxIDAgb2JqCjw8Ci9UeXBlIC9DYXRhbG9nCi9QYWdlcyAzIDAgUgo+PgplbmRvYmoKeHJlZgowIDcKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBuIAowMDAwMDAwMjQ5IDAwMDAwIG4gCjAwMDAwMDAzMjggMDAwMDAgbiAKMDAwMDAwMDQwNyAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDcKL1Jvb3QgMSAwIFIKPj4Kc3RhcnR4cmVmCjQ5NQolJUVPRgo=",
    "locale": "en-US",
    "ocr_type": "SEARCHABLE_IMAGE"
  }'
```

## Step 6: Configure Zapier

### 6.1 Get Your Webhook URL
Your Firebase Functions URL will be:
```
https://your-project-id-default-rtdb.firebaseapp.com/ocr
```

### 6.2 Zapier Configuration
1. **Trigger**: Gmail → New Email (with PDF attachment)
2. **Action**: Webhooks by Zapier → POST
   - **URL**: `https://your-project-id-default-rtdb.firebaseapp.com/ocr`
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
3. **Action**: Gmail → Send Email (with OCR'd PDF)

## Step 7: Monitoring and Logs

### 7.1 View Logs
```bash
firebase functions:log
```

### 7.2 Monitor Usage
- Check Firebase Console → Functions for usage statistics
- Monitor Adobe PDF Services usage in Adobe Developer Console

## Firebase Functions Benefits

### Cost Efficiency
- **Free tier**: 2M invocations/month, 400K GB-seconds compute time
- **Pay-per-use**: Only pay for actual function executions
- **No idle costs**: Unlike always-on servers

### Performance
- **Cold start**: ~1-2 seconds for first request
- **Warm start**: ~100-200ms for subsequent requests
- **Auto-scaling**: Handles traffic spikes automatically

### Security
- **HTTPS by default**: All endpoints are secure
- **Environment variables**: Credentials stored securely
- **IAM integration**: Fine-grained access control

## Troubleshooting

### Common Issues

1. **Function timeout**: Increase timeout in `firebase.json`
2. **Memory limits**: Increase memory allocation if needed
3. **Cold starts**: Consider keeping functions warm with scheduled triggers

### Debug Commands
```bash
# Test locally
firebase emulators:start --only functions

# View function logs
firebase functions:log --only ocr

# Check function status
firebase functions:list
```

## Advanced Configuration

### Custom Domain (Optional)
1. Go to Firebase Console → Hosting
2. Add custom domain
3. Update Zapier webhook URL

### Environment-specific Deployments
```bash
# Deploy to staging
firebase use staging
firebase deploy --only functions

# Deploy to production
firebase use production
firebase deploy --only functions
```

## Cost Estimation

For typical usage:
- **100 PDFs/month**: ~$0.00 (within free tier)
- **1,000 PDFs/month**: ~$0.50
- **10,000 PDFs/month**: ~$5.00

Plus Adobe PDF Services costs (check current pricing).

Your Firebase Functions webhook is now ready for production use with automatic scaling, security, and cost optimization!
