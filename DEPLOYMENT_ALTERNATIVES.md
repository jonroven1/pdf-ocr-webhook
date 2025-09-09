# Alternative Deployment Options for PDF OCR Webhook

Since we're encountering Git version issues with Heroku, here are several alternative deployment options:

## Option 1: Railway (Recommended - Easiest)

Railway is a modern alternative to Heroku with better Git support:

### Steps:
1. Go to [railway.app](https://railway.app) and sign up
2. Connect your GitHub account
3. Create a new project from GitHub
4. Select your repository (you'll need to push to GitHub first)
5. Set environment variables:
   - `PDF_SERVICES_CLIENT_ID`: `bc4b6b89bfc1457b89ed7a2ef920ccbe`
   - `PDF_SERVICES_CLIENT_SECRET`: `p8e-XfFf7D42xo0wSNaDAWHgEIapRRd_N1ed`
6. Deploy automatically

## Option 2: Render

Render is another Heroku alternative:

### Steps:
1. Go to [render.com](https://render.com) and sign up
2. Create a new Web Service
3. Connect your GitHub repository
4. Set environment variables
5. Deploy

## Option 3: Fix Heroku Git Issue

### Option 3a: Update Git via Homebrew
```bash
brew install git
# Then use the updated git for deployment
```

### Option 3b: Use Heroku CLI with GitHub Integration
1. Push your code to GitHub first
2. Connect Heroku to GitHub
3. Enable automatic deployments

## Option 4: Local Development + ngrok (For Testing)

For immediate testing without deployment:

### Steps:
1. Install ngrok: `brew install ngrok`
2. Run webhook locally: `python webhook_ocr.py`
3. In another terminal: `ngrok http 5000`
4. Use the ngrok URL in Zapier (e.g., `https://abc123.ngrok.io/ocr`)

## Option 5: PythonAnywhere

PythonAnywhere is great for Python web apps:

### Steps:
1. Sign up at [pythonanywhere.com](https://pythonanywhere.com)
2. Create a new web app
3. Upload your files
4. Set environment variables
5. Configure WSGI file

## Quick GitHub Setup (For Railway/Render)

If you want to use Railway or Render, push to GitHub first:

```bash
# Create a GitHub repository, then:
git remote add origin https://github.com/yourusername/your-repo-name.git
git branch -M main
git push -u origin main
```

## Recommended Next Steps

1. **For immediate testing**: Use Option 4 (ngrok) to test your Zapier integration
2. **For production**: Use Option 1 (Railway) for the easiest deployment
3. **For cost optimization**: Use Option 2 (Render) which has a generous free tier

## Testing Your Webhook

Once deployed, test with:

```bash
curl https://your-app-url.railway.app/health
```

Or use the test script:
```bash
python test_webhook.py
```

## Zapier Configuration

Once you have a working webhook URL, configure Zapier:

1. **Trigger**: Gmail → New Email (with PDF attachment)
2. **Action**: Webhooks by Zapier → POST
   - URL: `https://your-app-url.railway.app/ocr`
   - Data: 
     ```json
     {
       "pdf_data": "{{attachment_content}}",
       "locale": "en-US",
       "ocr_type": "SEARCHABLE_IMAGE"
     }
     ```
3. **Action**: Gmail → Send Email (with OCR'd PDF)

The webhook will automatically clean up all assets after processing for security and cost optimization.
