"""from dotenv import load_dotenv
import openai
from langgraph.types import interrupt
import os

from state import OverallState
from prompts import GREETING_PROMPT, DISPLAY_PROMPT
import pandas as pd

load_dotenv()

class Interaction:
    def __init__(self):
        self.llm = openai.OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url=os.getenv("GEMINI_BASE_URL")
        )

    def greet(self, state:OverallState):
        
        print("Greeting the user...")
        messages = [
            {"role": "system", "content": GREETING_PROMPT},
            {"role": "user", "content": "Please greet me and ask whether you have a PAN card or not."}
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
        
        return state
    
    def _condition(self, state:OverallState):
        answer = interrupt("Please acknowledge the message\n")
        state["human_response"] = answer

        if answer.lower() == "yes":
            return "pan"
        else:
            return "aadhar"
"""
from dotenv import load_dotenv
import openai
from langgraph.types import interrupt
import os

from state import OverallState
from prompts import AADHAR_GREETING_PROMPT

load_dotenv()

class Interaction:
    def __init__(self):
        self.llm = openai.OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url=os.getenv("GEMINI_BASE_URL")
        )
        self.retry = 0
        self.greet_retry = 0

    def greet(self, state:OverallState):
        
        print("Greeting the user...")
        messages = [
            {"role": "system", "content": AADHAR_GREETING_PROMPT},
            {"role": "user", "content": "Please greet me and ask for entering AADHAR number."}
        ]


        while self.greet_retry < 3:
            try:
                response = self.llm.chat.completions.create(
                    model="gemini-2.5-flash", 
                    messages=messages,
                    temperature=0.7
                )

                if response.choices[0].message.content:
                    state['ai_response'] = response.choices[0].message.content
                    print(state['ai_response'])
                    break  # Exit the retry loop on success

                elif not response.choices or response.choices[0].message.content is None:
                    print("Warning: API returned no choices in greet method.")
            
            except Exception as e:
                print(f"Error in greet method: {e}")
                if self.greet_retry == 2:  # Last retry
                    state['ai_response'] = "I am having trouble greeting you right now. Please try again later."
                    print(state["ai_response"])
                    return state
            
            self.greet_retry += 1
        
        return state
    
    def _greet_proceed(self, state:OverallState):
        if self.retry >= 2:
            return "end"
        else:
            return "ack"
    
    def _human_in_the_loop(self, state:OverallState):        
        self.retry += 1
        answer = interrupt("Please acknowledge the message (yes/no):\n")
        state["human_response"] = answer
        return state
    
    def _condition(self, state:OverallState):
        # This should only return routing decisions based on state
        answer = state.get("human_response", "").lower()
        
        if "yes" in answer:
            return "pan"
        elif "no" in answer:
            return "aadhar"
        elif self.retry >= 6:
            print("Session Expired!! Start a new session")
            return "end"
        else:
            return "human"
        
    def _after_ekyc(self, state:OverallState):
        if state["aadhar_verification_status"]['verification_status'] == 'success':
            return "PAN"
        else:
            return "other"
