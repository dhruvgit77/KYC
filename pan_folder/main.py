from langgraph.graph import StateGraph, START, END
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