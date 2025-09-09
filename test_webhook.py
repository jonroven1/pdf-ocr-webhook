#!/usr/bin/env python3
"""
Test script for the OCR webhook
"""

import requests
import base64
import json
import os

def test_webhook():
    # Test with a sample PDF from the resources folder
    pdf_path = "adobe-dc-pdf-services-sdk-python/src/resources/ocrInput.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Error: Test PDF not found at {pdf_path}")
        print("Please make sure you're running this from the correct directory")
        return
    
    # Read and encode the PDF
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    pdf_b64 = base64.b64encode(pdf_data).decode('utf-8')
    
    # Test data
    test_data = {
        "pdf_data": pdf_b64,
        "locale": "en-US",
        "ocr_type": "SEARCHABLE_IMAGE"
    }
    
    # Test local webhook (if running locally)
    local_url = "http://localhost:5001/ocr"
    heroku_url = "https://your-pdf-ocr-webhook.herokuapp.com/ocr"  # Replace with your actual URL
    
    print("Testing OCR webhook...")
    print(f"PDF size: {len(pdf_data)} bytes")
    
    try:
        # Test health endpoint first
        health_response = requests.get(f"{local_url.replace('/ocr', '/health')}")
        print(f"Health check: {health_response.status_code} - {health_response.json()}")
        
        # Test OCR endpoint
        response = requests.post(
            local_url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ OCR processing successful!")
            print(f"Original size: {result['original_size']} bytes")
            print(f"Processed size: {result['processed_size']} bytes")
            print(f"Timestamp: {result['timestamp']}")
            print(f"Assets cleaned: {result.get('assets_cleaned', 'N/A')}")
            
            # Save the result
            ocr_pdf_data = base64.b64decode(result['ocr_pdf_data'])
            with open('test_ocr_output.pdf', 'wb') as f:
                f.write(ocr_pdf_data)
            print("✅ OCR'd PDF saved as 'test_ocr_output.pdf'")
            print("✅ Assets automatically cleaned up from Adobe servers")
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the webhook is running locally")
        print("Run: python webhook_ocr.py")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_webhook()
