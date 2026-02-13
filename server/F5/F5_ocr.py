import pytesseract


def ocr_frame(frame):
    text = pytesseract.image_to_string(frame)
    return text.strip()