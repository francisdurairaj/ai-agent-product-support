# Troubleshooting Agent

An intelligent customer support agent for electronics troubleshooting and refund processing, powered by **Gemini 2.0 Flash** and **LangGraph**.

## Overview

This project implements an AI-powered customer support agent that can:
- **Troubleshoot electronics issues** by searching a vector database of 40+ product manuals
- **Process refunds** for broken items with intelligent verification
- **Access order history** and guide users through support workflows
- **Audit critical actions** for compliance

The agent uses a RAG (Retrieval-Augmented Generation) architecture with semantic search over product documentation.

📄 **[Read the Complete POC Summary](docs/POC_SUMMARY.md)** - Detailed proof of concept documentation with workflows, tool paths, and evaluation criteria.


## Architecture

### Tech Stack
- **LLM**: Gemini 2.0 Flash (`gemini-2.0-flash`) via `langchain-google-genai`
- **Orchestration**: LangGraph with StateGraph and MemorySaver
- **Vector Database**: Qdrant (local instance)
- **Embeddings**: Sentence Transformers (`all-MiniLM-L6-v2`)
- **Python**: 3.13+ with `uv` package manager

📊 **[View Detailed Architecture Diagrams](docs/architecture.md)** - Comprehensive Mermaid diagrams showing system flow, LangGraph execution, tool interactions, and data pipeline.


### Data Pipeline

```
metadata/ (40 JSON files)
    ↓
chunk_documents.py (splits by sections)
    ↓
chunks/ (41 text chunks + metadata)
    ↓
ingest_quadrant.py (embeds & indexes)
    ↓
Qdrant Collection: electronics_troubleshooting_guidelines
    ↓
troubleshoot_agent.py (queries via semantic search)
```

### Knowledge Base

The system includes troubleshooting guides for **40 electronics products** across categories:
- **Audio**: Sony WH-1000XM5, Bose QC45, JBL Flip6, Sonos Arc
- **Office**: Canon G3000, HP OfficeJet 9015
- **Smart Home**: Philips Hue, Nest Thermostat, Ring Doorbell, Amazon Echo
- **Wearables**: Apple Watch Ultra, Fitbit Charge 5, Oura Ring Gen3
- **Gaming**: PS5, Xbox Series X, Nintendo Switch
- **Camera/Drone**: DJI Mini 3 Pro, GoPro Hero 11, Instax Mini 11
- **Kitchen**: Instant Pot, Nespresso Vertuo, Breville Barista Express
- **And more...**

Each document contains:
- Product-specific troubleshooting steps
- Reset/pairing instructions
- Common error codes and solutions
- Maintenance guidelines

## Agent Capabilities

### Tools

1. **`check_order_history(user_id: str)`**
   - Retrieves recent orders (mock data: Canon G3000, Sony WH-1000XM5, DJI Mini 3 Pro)
   - Returns item IDs, names, prices, and dates

2. **`verify_broken_item(image_path: str, item_id: str)`**
   - Simulates image verification for damaged items
   - Mock logic: checks if "broken" appears in filename

3. **`refund_api(item_id: str, amount: float)`**
   - Processes refunds with validation
   - Validates amount against item price (1 to max_price)
   - Auto-refunds random amount after 3 failed attempts
   - Returns transaction ID

4. **`troubleshooting_knowledge_base(query: str)`**
   - Semantic search over Qdrant collection
   - Returns top 3 relevant document sections
   - Uses cosine similarity with MiniLM embeddings

5. **`audit_log(action: str, details: str)`**
   - Logs critical actions (refunds, etc.) for compliance

6. **`route_query(query: str)`**
   - Classifies queries: Refund, Troubleshooting, or Order Status

### Conversation Flow

The agent maintains context across turns using LangGraph's memory:
- **User ID is assumed known** (no need to ask)
- Displays order history with numbered lists
- Guides through refund verification workflow
- **Ends refund conversations** with: "Is there anything else I can help you with today?"

## Setup & Installation

### Prerequisites

1. **Python 3.13+** and `uv` package manager
2. **Qdrant** running locally:
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```
3. **Google API Key** for Gemini

### Installation Steps

1. **Clone and navigate to project**:
   ```bash
   cd ai-agent-product-support
   ```

2. **Create `.env` file**:
   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Prepare knowledge base** (first time only):
   ```bash
   # Split documents into chunks
   uv run chunk_documents.py
   
   # Embed and ingest into Qdrant
   uv run ingest_quadrant.py
   ```

5. **Run the agent**:
   ```bash
   uv run troubleshoot_agent.py
   ```

## Usage Examples

### Example 1: Troubleshooting Canon Printer

```
User: My Canon G3000 won't print, showing error 5B00
Agent: [Searches knowledge base]
       Error 5B00 indicates the ink absorber is full. Here's how to reset:
       1. Turn off the printer
       2. Hold Power + Stop buttons
       3. Release Stop, keep holding Power
       4. Press Stop 5 times, then release Power
       
       Is there anything else I can help you with today?
```

### Example 2: Broken Item Refund

```
User: My order arrived broken.
Agent: I'm sorry to hear that. Let me check your order history.

[Tools Used]: check_order_history
Agent: Here is your order history:
       1) Canon G3000 Printer
       2) Sony WH-1000XM5 Headphones
       3) DJI Mini 3 Pro
       
       Please indicate which item is broken by selecting the number.

User: broken.jpg
Agent: Please provide the item number from your order history.

User: 1

[Tools Used]: verify_broken_item
Agent: The item is verified as broken. The price for Canon G3000 Printer is $200.
       How much would you like to be refunded? (1 to 200)

User: 200

[AUDIT LOG] Action: Refund processed | Details: Full refund of $200 issued for ITEM_001 due to damage.

[Tools Used]: refund_api, audit_log
Agent: A full refund of $200 has been processed for the broken Canon G3000 Printer.
       Transaction ID: REF-ITEM_001-12345.
       
       Is there anything else I can help you with today?
```

### Example 3: Sony Headphones Reset

```
User: How do I reset my Sony WH-1000XM5 headphones?
Agent: [Searches knowledge base]
       To factory reset your Sony WH-1000XM5:
       1. Turn off the headset
       2. Press and hold Power + NC/AMB buttons simultaneously for 7 seconds
       3. The blue indicator will flash 4 times
       4. This resets volume and deletes pairing information
       
       To enter pairing mode: Hold Power for 5 seconds until you hear "Bluetooth Pairing"
       
       Is there anything else I can help you with today?
```

## Project Structure

```
ai-agent-product-support/
├── docs/                  # Documentation
│   ├── architecture.md    # Mermaid architecture diagrams
│   └── POC_SUMMARY.md     # Proof of concept summary
├── metadata/              # 40 JSON product manuals
├── chunks/                # Generated text chunks (41 files)
│   └── chunks_metadata.json
├── chunk_documents.py     # Splits docs into sections
├── ingest_quadrant.py     # Embeds & loads into Qdrant
├── troubleshoot_agent.py  # Main agent (LangGraph + Gemini)
├── pyproject.toml         # Dependencies
├── .env                   # API keys (create this)
└── README.md
```

## Key Features

✅ **Context-aware conversations** with memory across turns  
✅ **Semantic search** over 40+ product manuals  
✅ **Intelligent refund workflow** with validation and retry logic  
✅ **User-friendly** numbered selection for order items  
✅ **Audit logging** for compliance  
✅ **No user ID prompting** - assumes known context  
✅ **Polite conversation endings** after task completion  

## Dependencies

- `langchain` >= 1.0.8
- `langchain-google-genai` >= 3.1.0
- `langgraph` >= 1.0.3
- `qdrant-client` >= 1.16.0
- `sentence-transformers` >= 5.1.2
- `python-dotenv` >= 1.2.1
- `numpy` >= 2.3.5

## Notes

- The agent uses **mock data** for order history and image verification
- Refund amounts are validated (must be 1 to item price)
- After 3 invalid refund attempts, a random amount is auto-selected
- The knowledge base uses **cosine similarity** for semantic search
- Embeddings are 384-dimensional vectors from MiniLM-L6-v2
