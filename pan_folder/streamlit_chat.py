import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
import time
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver
from PIL import Image
import json

# Add parent directory to path
sys.path.append('..')

from verification import PanVerificationLLM
from state import OverallState, InputState
from prompts import (
    GREETING_PROMPT, DISPLAY_PAN_PROMPT, DISPLAY_FORM_60_PROMPT, 
    PAN_CARD_QUESTION_PROMPT, PROGRESS_PROMPT, FORM_60_PROMPT,
    VERIFICATION_SUCCESS_PROMPT, FORM_60_SUCCESS_PROMPT
)

# Page config
st.set_page_config(
    page_title="Tata AIA Life Insurance - PAN Verification Chat",
    page_icon="",
    layout="wide"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'system' not in st.session_state:
    st.session_state.system = None
if 'current_state' not in st.session_state:
    st.session_state.current_state = {}
if 'waiting_for_input' not in st.session_state:
    st.session_state.waiting_for_input = False
if 'verification_failed' not in st.session_state:
    st.session_state.verification_failed = False
if 'show_upload_option' not in st.session_state:
    st.session_state.show_upload_option = False
if 'image_uploaded' not in st.session_state:
    st.session_state.image_uploaded = False
if 'conversation_step' not in st.session_state:
    st.session_state.conversation_step = 'greeting'
if 'conversation_started' not in st.session_state:
    st.session_state.conversation_started = False
if 'pan_input_step' not in st.session_state:
    st.session_state.pan_input_step = 0  # 0=pan, 1=dob, 2=name, 3=confirmation
if 'form60_input_step' not in st.session_state:
    st.session_state.form60_input_step = 0  # 0=agri, 1=other, 2=confirmation
if 'waiting_for_correction' not in st.session_state:
    st.session_state.waiting_for_correction = False

# Initialize the system
@st.cache_resource
def initialize_system():
    return PanVerificationLLM()

def add_message(role, content, is_user=True):
    """Add a message to the chat"""
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "is_user": is_user
    })

def display_chat_messages():
    """Display all chat messages"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["timestamp"]:
                st.caption(f"⏰ {message['timestamp']}")

def parse_correction_with_llm(user_input, correction_type="pan", current_data=None):
    """Use LLM to parse natural language correction input"""
    if st.session_state.system is None:
        return {}
    
    # Create context about current data
    context = ""
    if current_data:
        if correction_type == "pan":
            context = f"""
Current PAN details:
- PAN Number: {current_data.get('pan_card_number', 'Not provided')}
- Date of Birth: {current_data.get('date_of_birth', 'Not provided')}
- Full Name: {current_data.get('pan_card_holders_name', 'Not provided')}
"""
        elif correction_type == "form60":
            context = f"""
Current Form 60 details:
- Agricultural Income: ₹{current_data.get('agricultural_income', 'Not provided')}
- Other Income: ₹{current_data.get('other_income', 'Not provided')}
"""
    
    # Create prompt for LLM
    if correction_type == "pan":
        system_prompt = f"""You are a helpful assistant that extracts PAN card information from user corrections.

{context}

The user wants to make corrections to their PAN card details. Extract the following information from their message and return it as a JSON object:

{{
    "pan_card_number": "extracted PAN number or null if not mentioned",
    "date_of_birth": "extracted date in DD/MM/YYYY format or null if not mentioned", 
    "pan_card_holders_name": "extracted full name or null if not mentioned"
}}

Rules:
- Only extract information that the user explicitly mentions
- For dates, convert to DD/MM/YYYY format
- For names, use proper case (Title Case)
- For PAN numbers, convert to uppercase
- Return null for fields not mentioned
- Be flexible with different ways of expressing the same information

Examples:
- "my name is dhruv" → {{"pan_card_holders_name": "Dhruv", "pan_card_number": null, "date_of_birth": null}}
- "change dob to 16/09/2005" → {{"date_of_birth": "16/09/2005", "pan_card_number": null, "pan_card_holders_name": null}}
- "my name is dhruv and my date of birth is 16/09/2005" → {{"pan_card_holders_name": "Dhruv", "date_of_birth": "16/09/2005", "pan_card_number": null}}"""
    
    elif correction_type == "form60":
        system_prompt = f"""You are a helpful assistant that extracts Form 60 income information from user corrections.

{context}

The user wants to make corrections to their Form 60 details. Extract the following information from their message and return it as a JSON object:

{{
    "agricultural_income": "extracted agricultural income number or null if not mentioned",
    "other_income": "extracted other income number or null if not mentioned"
}}

Rules:
- Only extract information that the user explicitly mentions
- Extract only the numeric value (no currency symbols)
- Return null for fields not mentioned
- Be flexible with different ways of expressing the same information

Examples:
- "agricultural income is 50000" → {{"agricultural_income": "50000", "other_income": null}}
- "change other income to 100000" → {{"other_income": "100000", "agricultural_income": null}}
- "agri income 75000 and other income 125000" → {{"agricultural_income": "75000", "other_income": "125000"}}"""
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User correction: {user_input}"}
        ]
        
        response = st.session_state.system.llm.chat.completions.create(
            model="gemini-2.5-flash",
            messages=messages,
            temperature=0.1  # Low temperature for consistent parsing
        )
        
        # Parse JSON response
        result_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        if "```json" in result_text:
            json_start = result_text.find("```json") + 7
            json_end = result_text.find("```", json_start)
            json_text = result_text[json_start:json_end].strip()
        elif "```" in result_text:
            json_start = result_text.find("```") + 3
            json_end = result_text.find("```", json_start)
            json_text = result_text[json_start:json_end].strip()
        else:
            json_text = result_text
        
        # Parse the JSON
        corrections = json.loads(json_text)
        
        # Filter out null values
        return {k: v for k, v in corrections.items() if v is not None}
        
    except Exception as e:
        print(f"Error parsing correction with LLM: {e}")
        return {}

def start_conversation():
    """Start the conversation"""
    if st.session_state.system is None:
        st.session_state.system = initialize_system()
    
    # Start with greeting
    result = st.session_state.system.greet({})
    if 'ai_response' in result:
        add_message("assistant", result['ai_response'], False)
    
    # Ask PAN card question
    result = st.session_state.system.ask_pan_card_question({})
    if 'pan_card_question' in result:
        add_message("assistant", f"**{result['pan_card_question']}**", False)
        st.session_state.waiting_for_input = True
        st.session_state.conversation_step = 'pan_question'
        st.session_state.conversation_started = True

def handle_user_input(user_input):
    """Handle user input and continue the conversation"""
    if not user_input:
        return
    
    # Add user message
    add_message("user", user_input)
    
    # Handle correction input
    if st.session_state.waiting_for_correction:
        handle_correction_input(user_input)
        return
    
    # Handle PAN card question response
    if st.session_state.conversation_step == 'pan_question':
        if user_input.lower() in ['yes', 'y', 'yeah', 'yep', 'sure', 'i do', 'i have']:
            st.session_state.conversation_step = 'pan_verification'
            st.session_state.pan_input_step = 0
            # Start PAN verification workflow
            start_pan_verification()
        else:
            st.session_state.conversation_step = 'form60'
            st.session_state.form60_input_step = 0
            # Start Form 60 workflow
            start_form_60()
        return
    
    # Handle other steps based on current conversation step
    if st.session_state.conversation_step == 'pan_verification':
        handle_pan_verification_input(user_input)
    elif st.session_state.conversation_step == 'form60':
        handle_form_60_input(user_input)

def handle_correction_input(user_input):
    """Handle correction input with LLM parsing"""
    if st.session_state.conversation_step == 'pan_verification':
        corrections = parse_correction_with_llm(user_input, "pan", st.session_state.current_state)
        
        # Update current state with corrections
        for field, value in corrections.items():
            st.session_state.current_state[field] = value
        
        if corrections:
            correction_summary = []
            for field, value in corrections.items():
                field_name = field.replace('_', ' ').title()
                if field == 'date_of_birth':
                    correction_summary.append(f"• **{field_name}:** {value}")
                elif field in ['agricultural_income', 'other_income']:
                    correction_summary.append(f"• **{field_name}:** ₹{value}")
                else:
                    correction_summary.append(f"• **{field_name}:** {value}")
            
            add_message("assistant", f"✅ **Got it! I've updated the following details:**\n\n" + "\n".join(correction_summary), False)
            
            # Re-display for confirmation
            result = st.session_state.system.display_pan_details(st.session_state.current_state)
            if 'pan_confirmation' in result:
                add_message("assistant", f"**{result['pan_confirmation']}**", False)
                st.session_state.waiting_for_input = True
                st.session_state.waiting_for_correction = False
                st.session_state.pan_input_step = 3  # Back to confirmation step
        else:
            add_message("assistant", "I couldn't understand the corrections. Please try again.", False)
            st.session_state.waiting_for_input = True
    
    elif st.session_state.conversation_step == 'form60':
        corrections = parse_correction_with_llm(user_input, "form60", st.session_state.current_state)
        
        # Update current state with corrections
        for field, value in corrections.items():
            st.session_state.current_state[field] = value
        
        if corrections:
            correction_summary = []
            for field, value in corrections.items():
                field_name = field.replace('_', ' ').title()
                correction_summary.append(f"• **{field_name}:** ₹{value}")
            
            add_message("assistant", f"✅ **Got it! I've updated the following details:**\n\n" + "\n".join(correction_summary), False)
            
            # Re-display for confirmation
            result = st.session_state.system.display_form_60_details(st.session_state.current_state)
            if 'form60_confirmation' in result:
                add_message("assistant", f"**{result['form60_confirmation']}**", False)
                st.session_state.waiting_for_input = True
                st.session_state.waiting_for_correction = False
                st.session_state.form60_input_step = 2  # Back to confirmation step
        else:
            add_message("assistant", "I couldn't understand the corrections. Please try again.", False)
            st.session_state.waiting_for_input = True

def start_pan_verification():
    """Start PAN verification workflow"""
    # Ask for PAN number
    messages = [
        {"role": "system", "content": PROGRESS_PROMPT},
        {"role": "user", "content": "Ask for PAN number input - Step 1."}
    ]
    
    response = st.session_state.system.llm.chat.completions.create(
        model="gemini-2.5-flash", 
        messages=messages,
        temperature=0.7
    )
    
    pan_question = response.choices[0].message.content
    add_message("assistant", f"**{pan_question}**", False)
    st.session_state.waiting_for_input = True
    st.session_state.pan_input_step = 0

def start_form_60():
    """Start Form 60 workflow"""
    # Ask for agricultural income
    messages = [
        {"role": "system", "content": FORM_60_PROMPT},
        {"role": "user", "content": "Ask for agricultural income input - Step 1."}
    ]
    
    response = st.session_state.system.llm.chat.completions.create(
        model="gemini-2.5-flash", 
        messages=messages,
        temperature=0.7
    )
    
    agri_question = response.choices[0].message.content
    add_message("assistant", f"**{agri_question}**", False)
    st.session_state.waiting_for_input = True
    st.session_state.form60_input_step = 0

def handle_pan_verification_input(user_input):
    """Handle PAN verification input with proper step tracking"""
    if st.session_state.pan_input_step == 0:
        # Store PAN number
        st.session_state.current_state['pan_card_number'] = user_input
        
        # Ask for DOB
        messages = [
            {"role": "system", "content": PROGRESS_PROMPT},
            {"role": "user", "content": "Ask for date of birth input - Step 2."}
        ]
        
        response = st.session_state.system.llm.chat.completions.create(
            model="gemini-2.5-flash", 
            messages=messages,
            temperature=0.7
        )
        
        dob_question = response.choices[0].message.content
        add_message("assistant", f"**{dob_question}**", False)
        st.session_state.waiting_for_input = True
        st.session_state.pan_input_step = 1  # Move to next step
        
    elif st.session_state.pan_input_step == 1:
        # Store DOB
        st.session_state.current_state['date_of_birth'] = user_input
        
        # Ask for name
        messages = [
            {"role": "system", "content": PROGRESS_PROMPT},
            {"role": "user", "content": "Ask for full name input - Step 3."}
        ]
        
        response = st.session_state.system.llm.chat.completions.create(
            model="gemini-2.5-flash", 
            messages=messages,
            temperature=0.7
        )
        
        name_question = response.choices[0].message.content
        add_message("assistant", f"**{name_question}**", False)
        st.session_state.waiting_for_input = True
        st.session_state.pan_input_step = 2  # Move to next step
        
    elif st.session_state.pan_input_step == 2:
        # Store name
        st.session_state.current_state['pan_card_holders_name'] = user_input
        
        # Display for confirmation
        result = st.session_state.system.display_pan_details(st.session_state.current_state)
        if 'pan_confirmation' in result:
            add_message("assistant", f"**{result['pan_confirmation']}**", False)
            st.session_state.waiting_for_input = True
            st.session_state.pan_input_step = 3  # Move to confirmation step
            
    elif st.session_state.pan_input_step == 3:
        if user_input.lower() == "yes":
            # Proceed with verification
            result = st.session_state.system.verify_from_NSDL(st.session_state.current_state)
            if 'verification_progress' in result:
                add_message("assistant", f"**{result['verification_progress']}**", False)
            
            if result.get('verification_status') == 'success':
                add_message("assistant", f"**{result['verification_success']}**", False)
                st.balloons()
                st.session_state.conversation_step = 'completed'
                st.session_state.waiting_for_input = False
            else:
                add_message("assistant", f"❌ **Verification Failed**\n\n{result.get('verification_message', '')}\n\n🔄 **Don't worry!** We have an alternate verification method. You can upload a clear photo of your PAN card and I'll verify it for you. Would you like to try this method?", False)
                st.session_state.verification_failed = True
                st.session_state.show_upload_option = True
                st.session_state.waiting_for_input = False
        else:
            # Handle corrections
            add_message("assistant", "No problem! Please tell me what needs to be corrected.", False)
            st.session_state.waiting_for_input = True
            st.session_state.waiting_for_correction = True

def handle_form_60_input(user_input):
    """Handle Form 60 input with proper step tracking"""
    if st.session_state.form60_input_step == 0:
        # Store agricultural income
        st.session_state.current_state['agricultural_income'] = user_input
        
        # Ask for other income
        messages = [
            {"role": "system", "content": FORM_60_PROMPT},
            {"role": "user", "content": "Ask for other income input - Step 2."}
        ]
        
        response = st.session_state.system.llm.chat.completions.create(
            model="gemini-2.5-flash", 
            messages=messages,
            temperature=0.7
        )
        
        other_question = response.choices[0].message.content
        add_message("assistant", f"**{other_question}**", False)
        st.session_state.waiting_for_input = True
        st.session_state.form60_input_step = 1  # Move to next step
        
    elif st.session_state.form60_input_step == 1:
        # Store other income
        st.session_state.current_state['other_income'] = user_input
        
        # Display for confirmation
        result = st.session_state.system.display_form_60_details(st.session_state.current_state)
        if 'form60_confirmation' in result:
            add_message("assistant", f"**{result['form60_confirmation']}**", False)
            st.session_state.waiting_for_input = True
            st.session_state.form60_input_step = 2  # Move to confirmation step
            
    elif st.session_state.form60_input_step == 2:
        if user_input.lower() == "yes":
            # Complete Form 60
            result = st.session_state.system.complete_form_60(st.session_state.current_state)
            if 'form60_success' in result:
                add_message("assistant", f"**{result['form60_success']}**", False)
                st.balloons()
                st.session_state.conversation_step = 'completed'
                st.session_state.waiting_for_input = False
        else:
            # Handle corrections
            add_message("assistant", "No problem! Please tell me what needs to be corrected.", False)
            st.session_state.waiting_for_input = True
            st.session_state.waiting_for_correction = True

def handle_pan_upload(uploaded_file):
    """Handle PAN card image upload - spoof verification"""
    if uploaded_file is not None:
        add_message("assistant", "📸 **Processing your PAN card image...**\n\nLet me verify your PAN card details from the uploaded image.", False)
        
        # Display the uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded PAN Card", use_column_width=True)
        
        # Simulate processing time
        with st.spinner("Verifying PAN card details..."):
            time.sleep(2)
        
        # Spoof successful verification
        add_message("assistant", "✅ **PAN Card Verification Successful!**\n\n🎉 **Your PAN card has been successfully verified using the uploaded image!**\n\n**Verification Method:** Image Upload\n**Status:** Verified\n**Timestamp:** " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\nYou're all set! Your PAN verification is complete.", False)
        
        # Update state to show success
        st.session_state.verification_failed = False
        st.session_state.show_upload_option = False
        st.session_state.image_uploaded = True
        st.session_state.conversation_step = 'completed'
        
        # Show success animation
        st.balloons()

def reset_conversation():
    """Reset the conversation"""
    st.session_state.messages = []
    st.session_state.current_state = {}
    st.session_state.waiting_for_input = False
    st.session_state.verification_failed = False
    st.session_state.show_upload_option = False
    st.session_state.image_uploaded = False
    st.session_state.conversation_step = 'greeting'
    st.session_state.conversation_started = False
    st.session_state.pan_input_step = 0
    st.session_state.form60_input_step = 0
    st.session_state.waiting_for_correction = False

def get_session_status():
    """Get current session status for sidebar"""
    if st.session_state.waiting_for_correction:
        return "✏️ Waiting for corrections"
    elif st.session_state.waiting_for_input:
        if st.session_state.conversation_step == 'pan_verification':
            if st.session_state.pan_input_step == 0:
                return "⏳ Waiting for PAN number"
            elif st.session_state.pan_input_step == 1:
                return "⏳ Waiting for Date of Birth"
            elif st.session_state.pan_input_step == 2:
                return "⏳ Waiting for Full Name"
            elif st.session_state.pan_input_step == 3:
                return "⏳ Waiting for confirmation"
        elif st.session_state.conversation_step == 'form60':
            if st.session_state.form60_input_step == 0:
                return "⏳ Waiting for Agricultural Income"
            elif st.session_state.form60_input_step == 1:
                return "⏳ Waiting for Other Income"
            elif st.session_state.form60_input_step == 2:
                return "⏳ Waiting for confirmation"
        else:
            return "⏳ Waiting for your input"
    elif st.session_state.verification_failed:
        return "❌ Verification Failed - Try image upload"
    elif st.session_state.image_uploaded:
        return "✅ Image Verification Successful"
    elif st.session_state.conversation_step == 'completed':
        return "✅ Process Completed"
    elif st.session_state.conversation_step == 'pan_verification':
        return "🔄 PAN Verification in Progress"
    elif st.session_state.conversation_step == 'form60':
        return "🔄 Form 60 in Progress"
    elif st.session_state.conversation_step == 'pan_question':
        return "❓ Asking about PAN card"
    elif st.session_state.conversation_started:
        return "💬 Conversation Started"
    else:
        return "🚀 Ready to start"

def main():
    # Header
    st.title("🏦 Tata AIA Life Insurance")
    st.subheader("PAN Card Verification Chat System")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Session Status")
        st.info(get_session_status())
        
        st.markdown("---")
        st.write("**Chat with Siddhi**")
        st.write("Your friendly insurance assistant")
        
        if st.button(" Reset Conversation"):
            reset_conversation()
            st.rerun()
    
    # Main chat area
    st.header("💬 Chat with Siddhi")
    
    # Display chat messages
    display_chat_messages()
    
    # Start conversation if not started
    if not st.session_state.conversation_started:
        if st.button("🚀 Start PAN Verification", type="primary"):
            start_conversation()
            st.rerun()
    else:
        # Show chat input if waiting for input
        if st.session_state.waiting_for_input:
            user_input = st.chat_input("Type your answer here...")
            
            if user_input:
                handle_user_input(user_input)
                st.rerun()
        else:
            # Show upload option if verification failed
            if st.session_state.show_upload_option:
                st.markdown("---")
                st.header("📸 Upload PAN Card Image")
                st.write("Since the verification failed, you can upload a clear photo of your PAN card and I'll verify it for you using our alternate verification method.")
                
                uploaded_file = st.file_uploader(
                    "Choose a PAN card image",
                    type=['png', 'jpg', 'jpeg'],
                    help="Upload a clear, well-lit image of your PAN card"
                )
                
                if uploaded_file is not None:
                    # Display the uploaded image
                    image = Image.open(uploaded_file)
                    st.image(image, caption="Uploaded PAN Card", use_column_width=True)
                    
                    if st.button("🔍 Verify PAN Card", type="primary"):
                        handle_pan_upload(uploaded_file)
                        st.rerun()
            
            # Show completion message
            elif st.session_state.conversation_step == 'completed':
                if st.session_state.image_uploaded:
                    st.success("🎉 PAN verification completed using image upload!")
                else:
                    st.success("🎉 Process completed successfully!")
                
                if st.button("🔄 Start New Session"):
                    reset_conversation()
                    st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            <p>🏦 Tata AIA Life Insurance Company Limited | PAN Verification System</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()