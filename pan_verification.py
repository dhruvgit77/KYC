from langchain.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
from langgraph.types import interrupt
import openai
import time
import re
import os

from state import PANDetailsState_pydantic, OverallState, InputState, VerificationState
from prompts import PAN_GREETING_PROMPT, DISPLAY_PROMPT, PAN_QUESTIONS_PROMPT, PAN_VALIDATION_PROMPT, PAN_VERIFICATION_SUCCESS_PROMPT, PAN_VERIFICATION_FAILED_PROMPT, FORM_60_PROMPT, DISPLAY_FORM_60_PROMPT
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import pandas as pd

load_dotenv()

def is_integer(s):
    try:
        int(s)
        return True
    except ValueError:
        return False
    
class PanVerificationLLM:
    def __init__(self):
        self.llm = openai.OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url=os.getenv("GEMINI_BASE_URL")
        )
        self.df = pd.read_csv(r"E:\KYC\KYC\databse.csv")
        self.retry = 0
        self.pan_pattern = r'[A-Z]{5}[0-9]{4}[A-Z]{1}'
        self.dob_pattern = r'[0-9]{2}/[0-9]{2}/[0-9]{4}'

    def greet(self, state:OverallState):
        
        print("Greeting the user...")
        messages = [
            {"role": "system", "content": PAN_GREETING_PROMPT},
            {"role": "user", "content": "Do not greet me but continue to ask whether I have a PAN card(IMPORTANT)."}
        ]

        retries = 0

        while retries < 3:
            try:
                response = self.llm.chat.completions.create(
                    model="gemini-2.5-flash", 
                    messages=messages,
                    temperature=0.7
                )

                if response.choices[0].message.content:
                    state['ai_response'] = response.choices[0].message.content
                    print("\n",state['ai_response'])
                    return state

                elif not response.choices or response.choices[0].message.content is None:
                    print("Warning: API returned no choices in greet method.")
            
            except Exception as e:
                print(f"Error in greet method: {e}")
                state['ai_response'] = "I am having trouble greeting you right now. Please try again."
                return state
            
            retries += 1

    def _human_in_the_loop(self, state:OverallState):        
        self.retry += 1
        answer = interrupt("Please acknowledge the message (yes/no):\n")
        state["human_response"] = answer
        return state
    
    def _condition(self, state:OverallState):
        # This should only return routing decisions based on state
        answer = state.get("human_response", "").lower()
        
        if "yes" in answer:
            return "yes"
        elif "no" in answer:
            return "no"
        elif self.retry >= 6:
            print("Session Expired!! Start a new session")
            return "end"
        else:
            return "retry"
        
    def _after_ekyc(self, state:OverallState):
        if state["aadhar_verification_status"]['verification_status'] == 'success':
            return "PAN"
        else:
            return "other"
        
    def _verify(self, i, answer: str):
        if i == 0 or i == "pan_card_number":
            match = re.search(self.pan_pattern, answer.upper())

            if match:
                answer = match.group(0)
                return True, answer.upper()
            else:
                answer = "LOOKS LIKE THE PAN NUMBER YOU HAVE ENTERED HAS AN INVALID FORMAT"
                
        elif i == 1 or i == "date_of_birth":
            match = re.search(self.dob_pattern, answer)

            if match:
                answer = match.group(0)
                return True, answer
            else:
                answer = "LOOKS LIKE THE DATE OF BIRTH YOU HAVE ENTERED HAS AN INVALID FORMAT. It should be in DD/MM/YYYY"

        else:
            return True, answer
        
        return False, answer
    
    def accept_pan_input(self, state:OverallState):
        questions = [
            "Enter your PAN card number",
            "Enter your date of birth (DD/MM/YYYY)",
            "Enter your PAN card holders name"
        ]
        answers = []
        qa_map={}

        # HUMAN in the LOOP
        for i,question in enumerate(questions):
            # interrupt the user for the answer
            retry = 0
            messages = [
                {"role": "system", "content": PAN_QUESTIONS_PROMPT},
                {"role": "user", "content": question}
            ]

            response = self.llm.chat.completions.create(
                    model="gemini-2.5-flash", 
                    messages=messages,
                    temperature=0.7
            )

            answer: str = interrupt(f"{response.choices[0].message.content}")

            while retry < 3:
                status, answer = self._verify(i, answer)
                
                if status:
                    break

                messages = [
                    {"role": "system", "content": PAN_VALIDATION_PROMPT},
                    {"role": "user", "content": f"{question}:-{answer}"}
                ]
                response = self.llm.chat.completions.create(
                    model="gemini-2.5-flash", 
                    messages=messages,
                    temperature=0.7
                )

                answer: str = interrupt(f"{response.choices[0].message.content}")
                retry += 1

            answers.append(answer)
            qa_map[question] = answer
        
        # HUMAN MESSAGE for prompting the LLM to display the PAN card details
        human = "Here are the customer PAN details: {answers} print it in a neat beautified and correct format. {status}"
        human_message = human.format(answers=qa_map, status = "new")
        
        messages=[
            {"role": "system", "content": DISPLAY_PROMPT},
            {"role": "user", "content": human_message}
        ]
        
        response = self.llm.beta.chat.completions.parse(
            model="gemini-2.5-flash",
            messages=messages,
            response_format =PANDetailsState_pydantic
        )

        result = response.choices[0].message.parsed

        fields = list(PANDetailsState_pydantic.model_fields.keys())

        for field in fields:
            field_value = getattr(result, field)
            if field_value is not None:
                state["pan_details"][field] = field_value

        while True:
            current_details_str = f"""
Here are the final PAN card details I have:
- PAN Number: {state['pan_details'].get('pan_card_number')}
- Date of Birth: {state['pan_details'].get('date_of_birth')}
- Holder's Name: {state['pan_details'].get('pan_card_holders_name')}

Are these details correct? (yes/no)
                """

            human_input = interrupt(current_details_str)
            
            if human_input.lower() == "no":
                human_details_correction = interrupt("Please enter the correct details in the format: \nfield_name: value \nExample: pan_card_holders_name: New Name\nEnter your corrected details:")

                current_details = {
                    "pan_card_number": state['pan_details'].get("pan_card_number"),
                    "date_of_birth": state['pan_details'].get("date_of_birth"),
                    "pan_card_holders_name": state['pan_details'].get("pan_card_holders_name")
                }

                contextual_prompt = f"""
                Here are the user's current PAN details:
                {current_details}

                The user wants to make the following correction:
                "{human_details_correction}"

                Please apply the correction and provide the full, complete, and updated set of PAN details.
                """

                messages = [
                    {"role": "system", "content": "You are an assistant that updates user data based on their corrections. Return the complete, updated data AND THE UPDATED DATA ONLY"},
                    {"role": "user", "content": contextual_prompt}
                ]

                response = self.llm.beta.chat.completions.parse(
                    model="gemini-2.5-flash", 
                    messages=messages,
                    response_format=PANDetailsState_pydantic 
                )

                result = response.choices[0].message.parsed

                fields = list(PANDetailsState_pydantic.model_fields.keys())
                map_pan = {}

                for field in fields:
                    field_value = getattr(result, field)

                    if field_value is not None:
                        retry = 0
                        while retry < 3:
                            status, answer = self._verify(field, field_value)
                            
                            if status:
                                state["pan_details"][field] = answer
                                map_pan[field] = answer
                            
                            else:
                                messages = [
                                    {"role": "system", "content": PAN_VALIDATION_PROMPT},
                                    {"role": "user", "content": f"{answer}:-{field_value}"}
                                ]

                                response = self.llm.chat.completions.create(
                                    model="gemini-2.5-flash", 
                                    messages=messages,
                                    temperature=0.7
                                )

                                field_value: str = interrupt(f"{response.choices[0].message.content}")
                            
                            retry += 1
                            
                    else:
                        map_pan[field] = state['pan_details'].get(field)

            elif human_input.lower() == "yes":
                print("Thank you for your acknowledgement. I will verify the PAN card details from the NSDL database.")
                return state
        

    def verify_from_NSDL(self, state: OverallState):
        print("Verifying from NSDL database...")    

        pan_number = state['pan_details'].get("pan_card_number", "").strip().upper()
        dob = state['pan_details'].get("date_of_birth", "").strip()
        full_name = state['pan_details'].get("pan_card_holders_name", "").strip()
        
        print(f"Verifying PAN: {pan_number}")
        print(f"DOB: {dob}")
        print(f"Name: {full_name}")
        
        if not all([pan_number, dob, full_name]):
            print("Error: Missing required PAN details for verification")
            state['pan_verification_status']['verification_status'] = 'error'
            state['pan_verification_status']['verification_message'] = 'Missing required information for verification'
            return state
        
        try:
            mask = (
                (self.df['pan_card_number'].str.strip().str.upper() == pan_number) &
                (self.df['date_of_birth'].str.strip() == dob) &
                (self.df['pan_card_holders_name'].str.strip().str.upper() == full_name.upper())
            )
            
            matching_records = self.df[mask]
            
            if not matching_records.empty:
                messages = [
                    {"role": "system", "content": PAN_VERIFICATION_SUCCESS_PROMPT},
                    {"role": "user", "content": "PAN validation is successful"}
                ]

                response = self.llm.chat.completions.create(
                    model="gemini-2.5-flash", 
                    messages=messages,
                    temperature=0.7
                )

                print(response.choices[0].message.content)

                state['pan_verification_status']['verification_status'] = 'success'
                state['pan_verification_status']['verification_message'] = 'PAN card details verified successfully'
                state['pan_verification_status']['verification_timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                messages = [
                    {"role": "system", "content": PAN_VERIFICATION_FAILED_PROMPT},
                    {"role": "user", "content": "PAN validation is unsuccessful"}
                ]

                response = self.llm.chat.completions.create(
                    model="gemini-2.5-flash", 
                    messages=messages,
                    temperature=0.7
                )

                print(response.choices[0].message.content)
                state['pan_verification_status']['verification_status'] = 'failed'
                state['pan_verification_status']['verification_message'] = 'PAN card details not found in database'
                state['pan_verification_status']['verification_timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                
        except Exception as e:
            print(f"Error during verification: {e}")
            state['pan_verification_status']['verification_status'] = 'error'
            state['pan_verification_status']['verification_message'] = f'Verification error: {str(e)}'
        
        return state
    
    def _accept_form60(self, state:OverallState):
        questions = [
            "Ask the user for his income with agricultue as your source",
            "Ask the user for his income from sources other than agriculture"
        ]

        for i,question in enumerate(questions):
            retry = 0

            messages = [
                {"role": "system", "content": FORM_60_PROMPT},
                {"role": "user", "content": f"{question}"}
            ]

            response = self.llm.chat.completions.create(
                model="gemini-2.5-flash", 
                messages=messages,
                temperature=0.7
            )

            human_message = interrupt(response.choices[0].message.content)

            while retry < 3:
                if i == 0:
                    isint = is_integer(human_message)
                    if isint:
                        state["Form_60"]["agricultural_income"] = human_message
                    else:
                        human_message = interrupt("PLEASE ENTER A VALID INCOME")
                
                else:
                    isint = is_integer(human_message)
                    if isint:
                        state["Form_60"]["other_income"] = human_message
                    else:
                        human_message = interrupt("PLEASE ENTER A VALID INCOME")
                
                retry += 1

            print("CONGARTULATIONS!! Your KYC PROCESS has been SUCCESFULLY COMPLETED")

        return state