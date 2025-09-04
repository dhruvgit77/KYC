from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from pan_verification import PanVerificationLLM
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

# Start the graph initially
result = graph.invoke(InputState(input_message=""), config=config)

# Loop ONLY while the graph is interrupted
while "__interrupt__" in result:
    # Print the reason for the interruption
    interrupt_value = result["__interrupt__"][0].value
    print(f"\n--- INTERRUPT: {interrupt_value} ---")
    
    # Get user input
    answer = input("Your answer: ")
    
    # Resume the graph with the user's answer
    result = graph.invoke(Command(resume=answer), config=config)

# Once the loop finishes, the graph is done. Print the final state.
# print("\n--- GRAPH FINISHED ---")
# print("Final State:")
# print(result)