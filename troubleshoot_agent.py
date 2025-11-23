import os
import getpass
import random
from typing import Annotated, List, Dict, Any, TypedDict
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from qdrant_client import QdrantClient

# --- Configuration ---
load_dotenv()

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google API Key: ")

QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "electronics_troubleshooting_guidelines"

# --- Tools ---

# Global Data & State
MOCK_ORDERS = [
    {"item_id": "ITEM_001", "name": "Canon G3000 Printer", "price": 200.0, "date": "2023-10-01"},
    {"item_id": "ITEM_002", "name": "Sony WH-1000XM5 Headphones", "price": 350.0, "date": "2023-11-15"},
    {"item_id": "ITEM_003", "name": "DJI Mini 3 Pro", "price": 450.0, "date": "2023-11-20"},
]

REFUND_CONTEXT = {"item_id": None, "attempts": 0}

@tool
def check_order_history(user_id: str) -> str:
    """Retrieve the list of recent orders for a user."""
    return str(MOCK_ORDERS)

@tool
def verify_broken_item(image_path: str, item_id: str) -> str:
    """
    Analyze an uploaded image to verify if an item is broken.
    Returns 'Verified' or 'Not Verified'.
    """
    # Mock logic: If "broken" is in the path or description, return Verified.
    if "broken" in image_path.lower():
        return "Verified: The item appears to be damaged."
    return "Not Verified: The item does not appear to be damaged based on the provided image."

@tool
def refund_api(item_id: str, amount: float) -> str:
    """Process a refund for an item. Validates the amount against the item price."""
    global REFUND_CONTEXT
    
    # Handle numeric item_id (user selection index)
    if item_id.isdigit():
        idx = int(item_id) - 1
        if 0 <= idx < len(MOCK_ORDERS):
            item_id = MOCK_ORDERS[idx]["item_id"]
        else:
            return f"Error: Invalid item selection '{item_id}'. Please choose a valid item number."
    
    # Find item price
    item = next((item for item in MOCK_ORDERS if item["item_id"] == item_id), None)
    if not item:
        return f"Error: Item {item_id} not found in order history."
    
    max_price = item["price"]
    
    # Check context
    if REFUND_CONTEXT["item_id"] != item_id:
        REFUND_CONTEXT = {"item_id": item_id, "attempts": 0}
        
    # Validate amount
    if 0 < amount <= max_price:
        # Success
        REFUND_CONTEXT = {"item_id": None, "attempts": 0} # Reset
        return f"Refund of ${amount} processed for item {item_id}. Transaction ID: REF-{item_id}-12345."
    else:
        REFUND_CONTEXT["attempts"] += 1
        current_attempts = REFUND_CONTEXT["attempts"]
        
        if current_attempts > 3:
            # Auto refund random amount
            random_amount = round(random.uniform(1, max_price), 2)
            REFUND_CONTEXT = {"item_id": None, "attempts": 0} # Reset
            return f"Invalid amount provided {current_attempts} times. Automatically chose a random amount. Refund of ${random_amount} processed for item {item_id}. Transaction ID: REF-{item_id}-12345."
        else:
            return f"Invalid amount. The amount must be between 1 and {max_price}. You have tried {current_attempts} times."

@tool
def troubleshooting_knowledge_base(query: str) -> str:
    """
    Search the knowledge base for troubleshooting guides.
    Useful for finding manuals, reset instructions, and solutions to common problems.
    """
    client = QdrantClient(url=QDRANT_URL)
    results = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=get_embedding(query),
        limit=3
    ).points
    
    # We need an embedding model. 
    # Since we used sentence-transformers in ingest, we should use it here too.
    # Or use Gemini's embedding if we want to switch, but the collection is already built with MiniLM.
    # Let's use sentence-transformers to be consistent with ingest.
    
    formatted_results = []
    for res in results:
        payload = res.payload
        formatted_results.append(f"Title: {payload.get('title')}\nSection: {payload.get('section_title')}\nContent: {payload.get('text')}\n")
    
    return "\n---\n".join(formatted_results)

@tool
def audit_log(action: str, details: str) -> str:
    """Log critical actions for compliance."""
    print(f"\n[AUDIT LOG] Action: {action} | Details: {details}\n")
    return "Action logged."

@tool
def route_query(query: str) -> str:
    """
    Route the user query to the appropriate category: 'Refund', 'Troubleshooting', or 'Order Status'.
    """
    query_lower = query.lower()
    if "refund" in query_lower or "money" in query_lower or "cashback" in query_lower:
        return "Refund"
    elif "broken" in query_lower or "damaged" in query_lower:
        return "Refund" # Broken items usually lead to refund/replacement
    elif "order" in query_lower or "status" in query_lower or "delivery" in query_lower:
        return "Order Status"
    else:
        return "Troubleshooting"

# --- Helper for Embeddings ---
# We need to load the same model as ingest to query Qdrant
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def get_embedding(text: str) -> List[float]:
    return embedding_model.encode(text).tolist()


from langgraph.graph.message import add_messages

# --- Agent State ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str

# --- Graph Definition ---

def chatbot(state: AgentState):
    # print(f"DEBUG: Messages in state: {state['messages']}")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    llm_with_tools = llm.bind_tools(tools)
    
    user_id = state.get("user_id", "Unknown")
    system_msg = SystemMessage(content=f"You are a helpful customer support agent. You are communicating with user {user_id}. You already know their User ID, so do NOT ask for it. When displaying order history, list items with numbers (e.g., 1) Item Name, 2) Item Name). Allow the user to select an item by its number. IMPORTANT: When calling tools like 'refund_api', you MUST convert the user's selection (number) back to the corresponding 'item_id' (e.g., ITEM_001) from the order history. Do NOT pass the number '1' or '2' as the item_id. When asking for a refund amount, check the item's price and specify the valid range (1 to price). After successfully processing a refund, you MUST end your response with: 'Is there anything else I can help you with today?'")
    messages = [system_msg] + state["messages"]
    
    return {"messages": [llm_with_tools.invoke(messages)]}

tools = [check_order_history, verify_broken_item, refund_api, troubleshooting_knowledge_base, audit_log, route_query]
tool_node = ToolNode(tools)

graph_builder = StateGraph(AgentState)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")

graph = graph_builder.compile(checkpointer=MemorySaver())

# --- Main Loop ---
def main():
    print("Troubleshooting Agent (Gemini Pro + LangGraph)")
    print("Type 'exit' to quit.")
    
    user_id = "USER_123" # Mock user ID
    config = {"configurable": {"thread_id": "1"}}
    
    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        events = graph.stream(
            {"messages": [HumanMessage(content=user_input)], "user_id": user_id},
            config,
            stream_mode="values"
        )
        
        tools_used = []
        final_response = ""

        for event in events:
            if "messages" in event:
                last_msg = event["messages"][-1]
                
                # Collect tools used
                if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                    for tool_call in last_msg.tool_calls:
                        tools_used.append(tool_call['name'])
                
                # Capture final response
                if isinstance(last_msg, AIMessage) and last_msg.content:
                    final_response = last_msg.content

        # Print tools used if any
        if tools_used:
            print(f"\n[Tools Used]: {', '.join(tools_used)}")
        
        if final_response:
            print(f"Agent: {final_response}")

if __name__ == "__main__":
    main()
