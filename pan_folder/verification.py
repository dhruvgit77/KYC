from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
from langgraph.types import interrupt
import openai
import os

from state import PANVerificationState, OverallState, InputState, PANVerificationStateAck
from prompts import (
    GREETING_PROMPT, DISPLAY_PAN_PROMPT, DISPLAY_FORM_60_PROMPT, 
    PAN_CARD_QUESTION_PROMPT, PROGRESS_PROMPT, FORM_60_PROMPT,
    VERIFICATION_SUCCESS_PROMPT, FORM_60_SUCCESS_PROMPT
)
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

    def greet(self, state: OverallState):
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

    def ask_pan_card_question(self, state: OverallState):
        """Ask if user has PAN card or not - Streamlit compatible version"""
        print("Asking about PAN card...")
        messages = [
            {"role": "system", "content": PAN_CARD_QUESTION_PROMPT},
            {"role": "user", "content": "Ask the user if they have a PAN card."}
        ]

        try:
            response = self.llm.chat.completions.create(
                model="gemini-2.5-flash", 
                messages=messages,
                temperature=0.7
            )

            if response.choices[0].message.content:
                question = response.choices[0].message.content
                # Instead of interrupt, store the question in state for Streamlit to handle
                state['pan_card_question'] = question
                state['waiting_for_pan_answer'] = True
                return state
            else:
                state['ai_response'] = "I need to know if you have a PAN card. Do you have one?"
                return state
                
        except Exception as e:
            print(f"Error asking PAN card question: {e}")
            state['ai_response'] = "I need to know if you have a PAN card. Do you have one?"
            return state

    def handle_pan_verification(self, state: OverallState):
        """Handle PAN card verification workflow using single PROGRESS_PROMPT"""
        print("Starting PAN verification...")
        
        # Step 1: PAN Number
        messages = [
            {"role": "system", "content": PROGRESS_PROMPT},
            {"role": "user", "content": "Ask for PAN number input - Step 1."}
        ]
        
        response = self.llm.chat.completions.create(
            model="gemini-2.5-flash", 
            messages=messages,
            temperature=0.7
        )
        
        pan_question = response.choices[0].message.content
        state['pan_question'] = pan_question
        state['waiting_for_pan_input'] = True
        return state

    def handle_form_60(self, state: OverallState):
        """Handle Form 60 workflow for users without PAN card"""
        print("Starting Form 60 process...")
        
        # Step 1: Agricultural Income
        messages = [
            {"role": "system", "content": FORM_60_PROMPT},
            {"role": "user", "content": "Ask for agricultural income input - Step 1."}
        ]
        
        response = self.llm.chat.completions.create(
            model="gemini-2.5-flash", 
            messages=messages,
            temperature=0.7
        )
        
        agri_question = response.choices[0].message.content
        state['form60_question'] = agri_question
        state['waiting_for_form60_input'] = True
        return state

    def display_pan_details(self, state: OverallState):
        """Display PAN details for confirmation"""
        print("Displaying PAN details...")
        
        pan_details_message = f"""
             Here are the PAN card details we have collected:

             PAN Number: {state.get('pan_card_number', 'N/A')}
             Date of Birth: {state.get('date_of_birth', 'N/A')}
             Full Name: {state.get('pan_card_holders_name', 'N/A')}

             Please display these details in a neat, beautified format with emojis and ask for user confirmation.
             """
        
        messages = [
            {"role": "system", "content": DISPLAY_PAN_PROMPT},
            {"role": "user", "content": pan_details_message}
        ]

        response = self.llm.chat.completions.create(
            model="gemini-2.5-flash", 
            messages=messages,
            temperature=0.7
        )

        confirmation_message = response.choices[0].message.content
        state['pan_confirmation'] = confirmation_message
        state['waiting_for_pan_confirmation'] = True
        return state

    def display_form_60_details(self, state: OverallState):
        """Display Form 60 details for confirmation"""
        print("Displaying Form 60 details...")
        
        form_60_message = f"""
             Here are the Form 60 details we have collected:

             Annual Agricultural Income: ₹{state.get('agricultural_income', 'N/A')}
             Annual Other Income: ₹{state.get('other_income', 'N/A')}

             Please display these details in a neat, beautified format with emojis and ask for user confirmation.
             """
        
        messages = [
            {"role": "system", "content": DISPLAY_FORM_60_PROMPT},
            {"role": "user", "content": form_60_message}
        ]

        response = self.llm.chat.completions.create(
            model="gemini-2.5-flash", 
            messages=messages,
            temperature=0.7
        )

        confirmation_message = response.choices[0].message.content
        state['form60_confirmation'] = confirmation_message
        state['waiting_for_form60_confirmation'] = True
        return state

    def verify_from_NSDL(self, state: OverallState):
        """Verify PAN details from NSDL database"""
        print("Verifying from NSDL database...")
        
        # Show progress message
        messages = [
            {"role": "system", "content": PROGRESS_PROMPT},
            {"role": "user", "content": "Show validation progress message - Step 4."}
        ]
        
        response = self.llm.chat.completions.create(
            model="gemini-2.5-flash", 
            messages=messages,
            temperature=0.7
        )
        
        progress_message = response.choices[0].message.content
        state['verification_progress'] = progress_message
        
        # Get the PAN details from state
        pan_number = state.get("pan_card_number", "").strip().upper()
        dob = state.get("date_of_birth", "").strip()
        full_name = state.get("pan_card_holders_name", "").strip()
        
        print(f"Verifying PAN: {pan_number}")
        print(f"DOB: {dob}")
        print(f"Name: {full_name}")
        
        # Check if all required fields are present
        if not all([pan_number, dob, full_name]):
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
                (self.df['pan_card_holders_name'].str.strip().str.upper() == full_name.upper())
            )
            
            matching_records = self.df[mask]
            
            if not matching_records.empty:
                print("Data found in NSDL database")
                state['verification_status'] = 'success'
                state['verification_message'] = 'PAN card details verified successfully'
                state['verification_timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Display success message
                messages = [
                    {"role": "system", "content": VERIFICATION_SUCCESS_PROMPT},
                    {"role": "user", "content": "Display success message for PAN verification."}
                ]
                
                response = self.llm.chat.completions.create(
                    model="gemini-2.5-flash", 
                    messages=messages,
                    temperature=0.7
                )
                
                success_message = response.choices[0].message.content
                state['verification_success'] = success_message
                
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

    def complete_form_60(self, state: OverallState):
        """Complete Form 60 process"""
        print("Completing Form 60...")
        
        state['verification_status'] = 'success'
        state['verification_message'] = 'Form 60 completed successfully'
        state['verification_timestamp'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Display success message
        messages = [
            {"role": "system", "content": FORM_60_SUCCESS_PROMPT},
            {"role": "user", "content": "Display success message for Form 60 completion."}
        ]
        
        response = self.llm.chat.completions.create(
            model="gemini-2.5-flash", 
            messages=messages,
            temperature=0.7
        )
        
        success_message = response.choices[0].message.content
        state['form60_success'] = success_message
        
        return state