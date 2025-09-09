from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver

from pan_verification import PanVerificationLLM
from aadhar_verification import AadharVerificationLLM
from state import OverallState, InputState
from interact_initialize import Interaction
from ocr_extraction import OCR

interact = Interaction()
pan_system = PanVerificationLLM()
aadhar_system = AadharVerificationLLM()
ocr = OCR()
builder = StateGraph(OverallState)
checkpoint = InMemorySaver()

pan_subgraph_builder = StateGraph(OverallState)
aadhar_subgraph_builder = StateGraph(OverallState)

# Pan Subgraph build
pan_subgraph_builder.add_node("greet", pan_system.greet)
pan_subgraph_builder.add_node("human", pan_system._human_in_the_loop)
pan_subgraph_builder.add_node("accept_pan_details", pan_system.accept_pan_input)
pan_subgraph_builder.add_node("verify_from_NSDL", pan_system.verify_from_NSDL)
pan_subgraph_builder.add_node("form60", pan_system._accept_form60)

pan_subgraph_builder.add_edge(START, "greet")
pan_subgraph_builder.add_edge("greet", "human")

pan_subgraph_builder.add_conditional_edges(
    "human",
    pan_system._condition,
    {
        "yes": "accept_pan_details",
        "no": "form60",
        "retry": "human",
        "end": END
    }
)

pan_subgraph_builder.add_edge("accept_pan_details", "verify_from_NSDL")
pan_subgraph_builder.add_edge("verify_from_NSDL", END)

pan_subgraph_builder.add_edge("form60", END)

pan_subgraph = pan_subgraph_builder.compile(checkpointer=checkpoint)

# Aadhar Subgraph build
aadhar_subgraph_builder.add_node("Accept_Aadhar_no", aadhar_system._accept_AADHAR_no)
aadhar_subgraph_builder.add_node("Enter_verify_OTP", aadhar_system._enter_verify_OTP)
aadhar_subgraph_builder.add_node("EKYC", aadhar_system.uidai_verification)
aadhar_subgraph_builder.add_node("DOB_check", aadhar_system.dob_verification)
aadhar_subgraph_builder.add_node("OCR_Extract", ocr.extract_ocr)
aadhar_subgraph_builder.add_node("OCR_aadhar", aadhar_system.ocr_data_verification)

aadhar_subgraph_builder.add_edge(START, "Accept_Aadhar_no")
aadhar_subgraph_builder.add_edge("Accept_Aadhar_no", "Enter_verify_OTP")

aadhar_subgraph_builder.add_conditional_edges(
    "Enter_verify_OTP", 
    aadhar_system._otp_condition,
    {
        "EKYC": "EKYC",
        "END":END
    }
)

aadhar_subgraph_builder.add_conditional_edges(
    "EKYC", 
    aadhar_system._condition,
    {
        "success": "DOB_check",
        "failed":"OCR_Extract"
    }
)

aadhar_subgraph_builder.add_edge("OCR_Extract", "OCR_aadhar")

aadhar_subgraph_builder
aadhar_subgraph_builder.add_conditional_edges(
    "OCR_aadhar", 
    aadhar_system._retry_condition,
    {
        "end": END,
        "verify":"EKYC"
    }
)

aadhar_subgraph_builder.add_edge("DOB_check", END)
aadhar_subgraph = aadhar_subgraph_builder.compile(checkpointer=checkpoint)

builder.add_node("greet", interact.greet)
builder.add_node("AADHAR_path", aadhar_subgraph)
builder.add_node("PAN_path", pan_subgraph)

# THE below nodes are note being used currently
"""builder.add_node("acknowledge", interact._human_in_the_loop)"""

builder.add_edge(START, "greet")

builder.add_conditional_edges(
    "greet",
    interact._greet_proceed,
    {
        "ack": "AADHAR_path",
        "end":END
    }
)
builder.add_edge("greet","AADHAR_path")

# builder.add_edge("greet","acknowledge")

# builder.add_conditional_edges(
#     "acknowledge",
#     interact._condition,
#     {
#         "pan":"PAN_path",
#         "aadhar": "AADHAR_path",
#         "human":"acknowledge",
#         "end":END
#     }
# )

# builder.add_edge("PAN_path", END)

builder.add_conditional_edges(
    "AADHAR_path",
    interact._after_ekyc,
    {
        "PAN": "PAN_path",
        "other": END
    }
)

graph = builder.compile(checkpointer=checkpoint)
config = {"configurable": {"thread_id": "123"}}

def create_initial_state():
    """Create a properly initialized OverallState with all nested dictionaries."""
    return {
        "input_message": "",
        "ai_response": "",
        "human_response": "",
        "OTP_verified": False,

        "pan_details": {
            "pan_card_number": "",
            "date_of_birth": "",
            "father_name": "",
            "pan_card_holders_name": ""
        },

        "pan_verification_status": {
            "verification_status": "",
            "verification_message": "",
            "verification_timestamp": "",
            "verification_doc": ""
        },

        "aadhar_details": {
            "aadhar_number": "",
            "date_of_birth": "",
            "name": "",
            "new_doc_needed": False
        },

        "aadhar_verification_status": {
            "verification_status": "",
            "verification_message": "",
            "verification_timestamp": "",
            "verification_doc": ""
        },

        "voterId_details": {
            "name": "",
            "dob": "",
            "voter_id": "",
            "new_doc_needed": False
        },

        "Form_60": {
            "agricultural_income": 0,
            "other_income": 0
        }
    }

print("Initializing graph with complete state...")
initial_state = create_initial_state()
result = graph.invoke(initial_state, config=config)

print("Starting interrupt handling loop...")
interrupt_count = 0
max_interrupts = 100  

try:
    while "__interrupt__" in result and interrupt_count < max_interrupts:
        interrupt_count += 1
        print(f"\n=== INTERRUPT {interrupt_count} ===")

        interrupt_data = result["__interrupt__"][0]
        interrupt_value = interrupt_data.value
        print(f"[INTERRUPT]: {interrupt_value}")

        answer = input("Your answer: ")

        result = graph.invoke(Command(resume=answer), config=config)

    if interrupt_count >= max_interrupts:
        print(f"\n⚠️ Maximum interrupts ({max_interrupts}) reached. Stopping to prevent infinite loop.")


except KeyError as e:
    print(f"\n❌ KeyError in interrupt handling: {e}")
    print("Available keys in result:", list(result.keys()) if isinstance(result, dict) else "Not a dictionary")

except Exception as e:
    print(f"\n❌ Error in interrupt handling: {e}")
    import traceback
    traceback.print_exc()
