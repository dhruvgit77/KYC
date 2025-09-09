from langgraph.graph import StateGraph, START, END
<<<<<<< HEAD
from langgraph.checkpoint.memory import InMemorySaver
from verification import PanVerificationLLM
from state import OverallState, InputState

def main():
    # Initialize the system
    system = PanVerificationLLM()
    
    # Create the graph
    builder = StateGraph(OverallState, input_state=InputState)
    checkpoint = InMemorySaver()
    
    # Add nodes
    builder.add_node("greet", system.greet)
    builder.add_node("ask_pan_question", system.ask_pan_card_question)
    
    # Add edges
    builder.add_edge(START, "greet")
    builder.add_edge("greet", "ask_pan_question")
    builder.add_edge("ask_pan_question", END)
    
    # Compile the graph
    graph = builder.compile(checkpointer=checkpoint)
    config = {"configurable": {"thread_id": "123"}}
    
    print("🏦 Tata AIA Life Insurance - PAN Verification System")
    print("=" * 50)
    
    # Start the conversation
    result = graph.invoke(InputState(input_message=""), config=config)
    
    print("\n✅ Process completed successfully!")

if __name__ == "__main__":
    main()
=======
from langgraph.types import Command
from verification import PanVerificationLLM
from state import OverallState, InputState
from langgraph.checkpoint.memory import InMemorySaver

system = PanVerificationLLM()
builder = StateGraph(OverallState, input_state=InputState)
checkpoint = InMemorySaver()

builder.add_node("greet", system.greet)
builder.add_node("system", system.accept_pan_input)
builder.add_node("verify_from_NSDL", system.verify_from_NSDL)

builder.add_edge(START, "greet")
builder.add_edge('greet', "system")
builder.add_edge("system", "verify_from_NSDL")
builder.add_edge("verify_from_NSDL", END)

graph = builder.compile(checkpointer=checkpoint)
config = {"configurable": {"thread_id": "123"}}

result = graph.invoke(InputState(input_message=""), config=config)

while "__interrupt__" in result:
    interrupt_value = result["__interrupt__"][0].value
    print(f"\n--- INTERRUPT: {interrupt_value} ---")
    
    answer = input("Your answer: ")
    
    result = graph.invoke(Command(resume=answer), config=config)

print("\n--- GRAPH FINISHED ---")
print("Final State:")
print(result)
>>>>>>> 920f314 (AADHAR + PAN workflow)
