from langchain.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
from langgraph.types import interrupt
import openai
import os

from state import PANVerificationState, OverallState, InputState, PANVerificationStateAck
from prompts import GREETING_PROMPT, DISPLAY_PROMPT
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import pandas as pd

load_dotenv()

class AadharVerificationLLM:
    def __init__(self):
        self.llm = openai.OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url=os.getenv("GEMINI_BASE_URL")
        )

    def uidai_verification(self, state: OverallState):
        print("Verifying from UIDAI...")
        return state

    def ekyc_verification(self, state: OverallState):
        print("eKYC verification...")

        dob = state['aadhar_details'].get('date_of_birth', "").strip()
        name = state['aadhar_details'].get('name', "").strip()

        if dob:
            print("Aadhar is considered valid and is a used as Age|ID|Address Proof")
            state['aadhar_details']['new_doc_needed'] = False
            return state

        else:
            print("Aadhar is considered valid and is used as ID|Address Proof")
            print("Please upload another document for age proof")
            state['aadhar_details']['new_doc_needed'] = True
            return state

    def ocr_data_verification(self, state: OverallState):
        print("Verifying OCR data...")

        dob = state[''].get('date_of_birth', "").strip()
        name = state['aadhar_details'].get('name', "").strip()

        if name and dob:
            print("OCR data is considered valid and is used as Age Proof")