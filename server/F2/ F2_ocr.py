import pytesseract
import cv2
import numpy as np
import requests
from PIL import Image
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


def preprocess_image_for_ocr(image):
    """
    Preprocess image to improve OCR accuracy
    - Convert to grayscale
    - Apply adaptive thresholding
    - Denoise
    - Increase contrast
    """
    # Convert PIL Image to numpy array if needed
    if isinstance(image, Image.Image):
        image = np.array(image)
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    # Increase contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(contrast, None, 10, 7, 21)
    
    # Apply adaptive thresholding
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Dilation to make text bolder (helps with thin fonts)
    kernel = np.ones((1, 1), np.uint8)
    dilated = cv2.dilate(binary, kernel, iterations=1)
    
    # Erosion to remove noise
    eroded = cv2.erode(dilated, kernel, iterations=1)
    
    return eroded


def extract_text_from_image_url(image_url: str) -> str:
    """
    Download image from Supabase URL and extract text using OCR with preprocessing
    
    Args:
        image_url: Supabase image URL
    
    Returns:
        Extracted text from the image
    """
    try:
        logger.info(f"🖼️ Downloading image from: {image_url}")
        
        # Download image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Open image
        image = Image.open(BytesIO(response.content))
        
        # Convert to RGB if needed (handles RGBA, grayscale, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        logger.info("🔍 Preprocessing image for better OCR accuracy...")
        
        # Preprocess image
        preprocessed = preprocess_image_for_ocr(image)
        
        # Extract text using Tesseract with custom config
        # --psm 6: Assume a single uniform block of text
        # --oem 3: Use both legacy and LSTM OCR engine
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(preprocessed, config=custom_config)
        
        # Also try with original image for comparison
        text_original = pytesseract.image_to_string(image, config=custom_config)
        
        # Use whichever extraction is longer (usually more accurate)
        if len(text_original.strip()) > len(text.strip()):
            text = text_original
            logger.info("✅ Using original image OCR (better result)")
        else:
            logger.info("✅ Using preprocessed image OCR (better result)")
        
        # Clean up text
        text = text.strip()
        
        if not text:
            logger.warning("⚠️ No text extracted from image")
            return "No text found in image. The image might be blank or contain only graphics/diagrams."
        
        logger.info(f"✅ Extracted {len(text)} characters from image")
        return text
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error downloading image: {e}")
        return f"Error downloading image: {str(e)}"
    except Exception as e:
        logger.error(f"❌ Error extracting text from image: {e}")
        return f"Error processing image: {str(e)}"


def extract_text_with_layout(image_url: str) -> str:
    """
    Extract text while preserving layout (useful for mathematical equations)
    
    Args:
        image_url: Supabase image URL
    
    Returns:
        Extracted text with layout preservation
    """
    try:
        # Download image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        image = Image.open(BytesIO(response.content))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Preprocess
        preprocessed = preprocess_image_for_ocr(image)
        
        # PSM 4: Single column of text of variable sizes
        custom_config = r'--oem 3 --psm 4'
        text = pytesseract.image_to_string(preprocessed, config=custom_config)
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error in layout extraction: {e}")
        return extract_text_from_image_url(image_url)  # Fallback to regular extraction