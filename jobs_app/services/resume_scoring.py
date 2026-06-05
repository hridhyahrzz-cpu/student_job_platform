import os
import time
from django.conf import settings
from google import genai
from google.oauth2 import service_account
from google.auth.transport.requests import Request

def get_gemini_client():
    """Initializes the Gemini client cleanly using direct service account credentials and OAuth token."""
    json_path = os.path.join(settings.BASE_DIR, 'google-credentials.json')
    scopes = ['https://www.googleapis.com/auth/generative-language', 'https://www.googleapis.com/auth/cloud-platform']
    creds = service_account.Credentials.from_service_account_file(json_path, scopes=scopes)
    
    # Force refresh the token to obtain the access token
    creds.refresh(Request())
    access_token = creds.token
    
    # Initialize the client by passing a dummy api_key to satisfy validation,
    # and pass the actual Bearer token in the http_options headers.
    client = genai.Client(
        api_key="dummy_key_to_bypass_validation",
        http_options={
            "headers": {
                "Authorization": f"Bearer {access_token}"
            }
        }
    )
    
    # Remove the dummy x-goog-api-key header so it doesn't conflict with Authorization
    if hasattr(client, '_api_client'):
        headers = client._api_client._http_options.headers
        if 'x-goog-api-key' in headers:
            del headers['x-goog-api-key']
            
    return client

def analyze_resume(structured_prompt, job_description):
    """Sends the structured evaluation prompt directly to Gemini with automatic 503 retry backoff."""
    client = get_gemini_client()
    max_retries = 3
    initial_delay = 2  # Start with a 2-second delay
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=structured_prompt,
            )
            return response.text
        except Exception as e:
            # Check if it's a 503 or transient network spike
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < max_retries - 1:
                    sleep_time = initial_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s...
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Gemini API 503 spike. Retrying in {sleep_time} seconds (Attempt {attempt + 1}/{max_retries})...")
                    time.sleep(sleep_time)
                    continue
            
            # If it's a non-503 error or we exhausted all retries, raise it
            raise Exception(f"Google API Handshake Failed: {str(e)}")