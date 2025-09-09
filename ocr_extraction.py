<<<<<<< HEAD
=======
from state import OverallState
import time
>>>>>>> 920f314 (AADHAR + PAN workflow)
class OCR:
    def __init__(self):
        self.ocr_client = None

<<<<<<< HEAD
    def extract_ocr(self, image_path: str):
        print("Extracting OCR from image...")
        return "OCR extracted from image"
=======
    def extract_ocr(self, state: OverallState):
        print("Extracting OCR from image...")
        time.sleep(2.0)
        print("OCR Extraction Succesful")
        return state
>>>>>>> 920f314 (AADHAR + PAN workflow)
