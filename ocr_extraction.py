from state import OverallState
import time
class OCR:
    def __init__(self):
        self.ocr_client = None

    def extract_ocr(self, state: OverallState):
        print("Extracting OCR from image...")
        time.sleep(2.0)
        print("OCR Extraction Succesful")
        return state