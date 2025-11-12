import os
import sys
import base64
import argparse
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Attempt to import the required Gemini client and types
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: The 'google-genai' library is not installed.")
    print("Please install it using: pip install google-genai")
    sys.exit(1)

load_dotenv()

# --- Utility Functions ---

def encode_image_to_base64(image_path: str) -> tuple[str, str] | tuple[None, None]:
    """Encodes an image file into a Base64 string and determines its MIME type."""
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return None, None
        
    try:
        # Infer MIME type from file extension
        ext = os.path.splitext(image_path)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        else:
            print(f"Warning: Unsupported image type '{ext}'. Using 'image/jpeg'.")
            mime_type = 'image/jpeg'

        with open(image_path, "rb") as image_file:
            # Read the binary data and encode it
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string, mime_type
            
    except Exception as e:
        print(f"Error during image encoding: {e}")
        return None, None


def test_multimodal_api(client: genai.Client, model_name: str, image_path: str, prompt: str):
    """Calls the Gemini API with the image and text prompt."""

    # 1. Encode the image
    encoded_image, mime_type = encode_image_to_base64(image_path)
    
    if not encoded_image:
        print("API test aborted due to encoding failure.")
        return

    print("\n--- Sending Request to Gemini ---")
    print(f"Model: {model_name}")
    print(f"Prompt: '{prompt}'")
    
    try:
        # 2. Structure the content payload (text and image part)
        image_part = types.Part.from_bytes(
            data=base64.b64decode(encoded_image),
            mime_type=mime_type
        )
        
        contents = [prompt, image_part]

        # 3. Call the API
        response = client.models.generate_content(
            model=model_name,
            contents=contents
        )
        
        # 4. Print results
        print("\n--- Gemini Interpretation (SUCCESS) ---")
        print(response.text)
        print("\n-------------------------------------")

    except Exception as e:
        print("\n--- API Call Failed (ERROR) ---")
        print(f"An error occurred: {e}")
        print("Please check your API key and permissions.")
        print("-------------------------------------")