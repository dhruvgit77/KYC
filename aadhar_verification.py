from dotenv import load_dotenv
from langgraph.types import interrupt
import openai
import re
import os

from state import OverallState
from prompts import ADHAAR_NO_VALIDATION_PROMPT
import pandas as pd

load_dotenv()

class AadharVerificationLLM:
    def __init__(self):
        self.llm = openai.OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url=os.getenv("GEMINI_BASE_URL")
        )
        
        self.uidai_df = pd.read_csv(
            r"E:\KYC\KYC\database_uidai.csv",
            dtype={'aadhar_number': str}
        )
        self.verification_count = 0
        self.otp_pattern = r'[0-9]{6}'
        self.aadhar_no_pattern = r'[0-9]{12}'
    
    def _accept_AADHAR_no(self, state: OverallState):
        human_message = interrupt("Enter AADHAR Number")

        retries = 0
        while retries < 3:
            aadhar_no = re.search(self.aadhar_no_pattern, human_message)

            if aadhar_no:
                state["aadhar_details"]["aadhar_number"] = aadhar_no.group(0)
                break
            
            else:
                messages = [
                    {"role": "system", "content": ADHAAR_NO_VALIDATION_PROMPT},
                    {"role": "user", "content": f"This is the AADHAR number enterd by customer {human_message}"}
                ]
                response = self.llm.chat.completions.create(
                    model="gemini-2.5-flash",
                    messages=messages,
                    temperature=0.7
                )

                human_message = interrupt(response.choices[0].message.content)

            retries += 1

        return state

    def _enter_verify_OTP(self, state: OverallState):
        messages = [
            {"role": "system", "content": "The user has entered his other number. Now ask the user for OTP by continuing the conversation flow which is next step after entering AAdhar No. You are currently working with a customer so do not make you response more than 2 lines. It should be staright to the context"},
            {"role": "user", "content": "Now ask the user for an OTP"}
        ]

        response = self.llm.chat.completions.create(
            model="gemini-2.5-flash",
            messages=messages,
            temperature=0.7
        )

        retries = 0
        
        human_message = interrupt(response.choices[0].message.content)

        while retries < 2:
            try:
                otp = re.search(self.otp_pattern, human_message)
                if otp:
                    otp_value = int(otp.group(0)) 
                else:
                    otp_value = 000000

            except Exception as e:
                print(f"[ERROR in OTP]: {e}\n")
                human_message = interrupt("Please Enter a valid OTP. It is a 6 digit number")
                retries += 1
                continue
            
            if otp_value != 456789:
                messages = [
                    {"role": "system", "content": "Keep your tone encouraging, but formal. You are currently working with a customer so do not make you response more than 2 lines. It should be staright to the context"},
                    {"role": "user", "content": "the user has entered an incorrect OTP ask him to enter the correct one. The OTP is a 6-digit number"}
                ]

                response = self.llm.chat.completions.create(
                    model="gemini-2.5-flash",
                    messages=messages,
                    temperature=0.7
                )

                human_message = interrupt(response.choices[0].message.content)
                
            else:
                state["OTP_verified"] = True
                print("\nGreat!! The OTP You have entered is correct\n")
                return state

            retries += 1
        
        state["OTP_verified"] = False
        return state
    
    def _otp_condition(self, state:OverallState):
        if state["OTP_verified"]:
            return "EKYC"
        else:
            return "END"

    def uidai_verification(self, state: OverallState):
        print("Verifying from UIDAI...")
        self.verification_count += 1

        aadhar_no = str(state["aadhar_details"]["aadhar_number"])        
        mask = self.uidai_df['aadhar_number'].str.strip() == aadhar_no
        
        print(f"Verifying Aadhar: '{aadhar_no}'")


        try:
            matching_records = self.uidai_df[mask]
            kyc_status = not matching_records.empty

            if kyc_status:
                aa_no = state["aadhar_details"]["aadhar_number"] = matching_records["aadhar_number"].iloc[0]
                dob = state['aadhar_details']["date_of_birth"] = matching_records["date_of_birth"].iloc[0]
                name = state["aadhar_details"]["name"] = matching_records["name"].iloc[0]

                print("✅ UIDAI verification successful!")
                print("THESE ARE YOUR AADHAR DETAILS")
                print(f"\nAADHAR NO:- {aa_no}\nAADHAR HOLDER NAME:- {name}\nDATE OF BIRTH:- {dob}\n")
                state["aadhar_verification_status"]['verification_status'] = 'success'
                state['aadhar_verification_status']['verification_message'] = 'Aadhar card details verified successfully'
                state['aadhar_verification_status']['verification_timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

            else:
                print("❌ UIDAI verification failed!")
                state['aadhar_verification_status']['verification_status'] = 'failed'
                state['aadhar_verification_status']['verification_message'] = 'Aadhar card details not found in database'
                state['aadhar_verification_status']['verification_timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') 
        
        except Exception as error:
            state['pan_verification_status']['verification_status'] = "error"
            state['pan_verification_status']['verification_message'] = f'Verification error: {str(error)}'
        
        return state

    def dob_verification(self, state: OverallState):
        print("eKYC verification...")
        dob = state['aadhar_details'].get('date_of_birth', "").strip()

        if dob:
            print("Aadhar is considered valid and is a used as Age|ID|Address Proof")
            state['aadhar_details']['new_doc_needed'] = False
            return state

        else:
            print("Aadhar is considered valid and is used as ID|Address Proof")
            print("Please upload another document for age proof")
            state['aadhar_details']['new_doc_needed'] = True
            return state
        
    # conditional edge
    def _condition(self, state:OverallState):
        return state['aadhar_verification_status']['verification_status']
    
    # CHECK THIS ONE PROPERLY
    def _retry_condition(self, state:OverallState):
        if self.verification_count >= 2:
            return "end"
        return "verify"

    def ocr_data_verification(self, state: OverallState):
        print("Upload an image of your aadhar card...")
        print("Verifying OCR data...")

        dob = state['aadhar_details'].get('date_of_birth', "").strip()
        name = state['aadhar_details'].get('name', "").strip()

        if name and dob:
            print("OCR data is considered valid and is used as Age Proof")
        else:
            print("Verificaiton Failed")
        return state
        