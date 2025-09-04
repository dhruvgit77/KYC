from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
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

class PanVerificationLLM:
    def __init__(self):
        self.llm = openai.OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url=os.getenv("GEMINI_BASE_URL")
        )
        self.df = pd.read_csv(r"/Users/administrator/Desktop/chat/databse.csv")

    def greet(self, state:OverallState):
        
        print("Greeting the user...")
        messages = [
            {"role": "system", "content": GREETING_PROMPT},
            {"role": "user", "content": "Please greet me and ask for my PAN card details."}
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
                    print(state['ai_response'])
                    return state

                elif not response.choices or response.choices[0].message.content is None:
                    print("Warning: API returned no choices in greet method.")
            
            except Exception as e:
                print(f"Error in greet method: {e}")
                state['ai_response'] = "I am having trouble greeting you right now. Please try again."
                return state
            
            retries += 1
            
    def accept_pan_input(self, state:OverallState):
        questions = [
            "Enter your PAN card number",
            "Enter your date of birth (DD/MM/YYYY)",
            "Enter your father's name",
            "Enter your PAN card holders name"
        ]
        answers = []
        qa_map={}

        # HUMAN in the LOOP
        for question in questions:
            # interrupt the user for the answer
            answer = interrupt(f"{question}")
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
            response_format=PANVerificationState
        )

        result = response.choices[0].message.parsed

        fields = list(PANVerificationStateAck.model_fields.keys())

        for field in fields:
            field_value = getattr(result, field)
            if field_value is not None:
                state[field] = field_value

        while True:
            current_details_str = f"""
    Here are the details I have:
    - PAN Number: {state.get('pan_card_number')}
    - Date of Birth: {state.get('date_of_birth')}
    - Father's Name: {state.get('father_name')}
    - Holder's Name: {state.get('pan_card_holders_name')}

    Are these details correct? (yes/no)
    """
            human_input = interrupt(current_details_str)
    
            
            if human_input.lower() == "no":
                print("Please enter the correct details in the format: \nfield_name: value \nExample: pan_card_holders_name: New Name")
                
                human_details_correction = interrupt("Enter your corrected details:")

                current_details = {
                    "pan_card_number": state.get("pan_card_number"),
                    "date_of_birth": state.get("date_of_birth"),
                    "father_name": state.get("father_name"),
                    "pan_card_holders_name": state.get("pan_card_holders_name")
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
                    response_format=PANVerificationStateAck 
                )

                result = response.choices[0].message.parsed

                print("\n\nAfter no acknowledgement (with context):\n")

                fields = list(PANVerificationStateAck.model_fields.keys())
                map_pan = {}

                for field in fields:
                    field_value = getattr(result, field)
                    if field_value is not None:
                        state[field] = field_value
                        map_pan[field] = field_value
                    else:
                        map_pan[field] = state.get(field)

            elif human_input.lower() == "yes":
                print("Thank you for your acknowledgement. I will verify the PAN card details from the NSDL database.")
                return state
        

    def verify_from_NSDL(self, state: OverallState):
        print("Verifying from NSDL database...")
        
        # Get the PAN details from state
        pan_number = state.get("pan_card_number", "").strip().upper()
        dob = state.get("date_of_birth", "").strip()
        father_name = state.get("father_name", "").strip()
        full_name = state.get("pan_card_holders_name", "").strip()
        
        print(f"Verifying PAN: {pan_number}")
        print(f"DOB: {dob}")
        print(f"Father: {father_name}")
        print(f"Name: {full_name}")
        
        # Check if all required fields are present
        if not all([pan_number, dob, father_name, full_name]):
            print("Error: Missing required PAN details for verification")
            state['verification_status'] = 'error'
            state['verification_message'] = 'Missing required information for verification'
            return state
        
        # Search for matching record in database
        try:
            # Create a mask for exact matches using the correct column names
            mask = (
                (self.df['pan_card_number'].str.strip().str.upper() == pan_number) &
                (self.df['date_of_birth'].str.strip() == dob) &
                (self.df['father_name'].str.strip().str.upper() == father_name.upper()) &
                (self.df['pan_card_holders_name'].str.strip().str.upper() == full_name.upper())
            )
            
            matching_records = self.df[mask]
            
            if not matching_records.empty:
                print("✅ PAN verification successful!")
                print("Data found in NSDL database")
                state['verification_status'] = 'success'
                state['verification_message'] = 'PAN card details verified successfully'
                state['verification_timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                print("❌ PAN verification failed!")
                print("No matching data found in NSDL database")
                state['verification_status'] = 'failed'
                state['verification_message'] = 'PAN card details not found in database'
                state['verification_timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                
        except Exception as e:
            print(f"Error during verification: {e}")
            state['verification_status'] = 'error'
            state['verification_message'] = f'Verification error: {str(e)}'
        
        return state