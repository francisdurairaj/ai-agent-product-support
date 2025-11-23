# Architecture Diagrams

This document contains Mermaid diagrams illustrating the system architecture.

## System Overview

```mermaid
graph TB
    subgraph "Data Preparation Pipeline"
        A[metadata/<br/>40 JSON Files] -->|Read| B[chunk_documents.py]
        B -->|Split by Sections| C[chunks/<br/>41 Text Chunks]
        C -->|Load| D[ingest_quadrant.py]
        D -->|Embed with<br/>MiniLM-L6-v2| E[Qdrant Vector DB<br/>electronics_troubleshooting_guidelines]
    end
    
    subgraph "Runtime Agent"
        F[User Input] -->|CLI| G[troubleshoot_agent.py]
        G -->|Query| E
        E -->|Top 3 Results| G
        G -->|LLM Call| H[Gemini 2.0 Flash]
        H -->|Response| G
        G -->|Output| I[User]
    end
    
    subgraph "External Services"
        J[Google Gemini API]
        K[Qdrant Server<br/>localhost:6333]
    end
    
    H -.->|API Call| J
    E -.->|Connection| K
    
    style A fill:#e1f5ff
    style E fill:#ffe1f5
    style H fill:#fff5e1
    style G fill:#e1ffe1
```

## LangGraph Agent Flow

```mermaid
graph TB
    START([START]) --> chatbot[Chatbot Node<br/>Gemini 2.0 Flash]
    
    chatbot -->|Decision| condition{tools_condition}
    
    condition -->|Tool Call Needed| tools[Tools Node<br/>Execute Tool]
    condition -->|No Tool Call| END([END])
    
    tools --> chatbot
    
    subgraph "Agent State"
        state["messages: List[BaseMessage]<br/>user_id: str"]
    end
    
    subgraph "Available Tools"
        T1[check_order_history]
        T2[verify_broken_item]
        T3[refund_api]
        T4[troubleshooting_knowledge_base]
        T5[audit_log]
        T6[route_query]
    end
    
    tools -.->|Invoke| T1
    tools -.->|Invoke| T2
    tools -.->|Invoke| T3
    tools -.->|Invoke| T4
    tools -.->|Invoke| T5
    tools -.->|Invoke| T6
    
    chatbot -.->|Read/Write| state
    tools -.->|Read/Write| state
    
    style chatbot fill:#e1ffe1
    style tools fill:#ffe1e1
    style state fill:#fff5e1
```

## Tool Interaction Flow

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent (Chatbot)
    participant T as Tool Node
    participant Q as Qdrant DB
    participant M as Mock APIs
    participant L as Audit Log
    
    U->>A: "My order arrived broken"
    A->>T: check_order_history(user_id)
    T->>M: Fetch mock orders
    M-->>T: [Canon G3000, Sony XM5, DJI Mini 3]
    T-->>A: Order list
    A->>U: "Here are your orders: 1) Canon G3000..."
    
    U->>A: "1"
    A->>T: verify_broken_item("broken.jpg", "ITEM_001")
    T->>M: Verify image
    M-->>T: "Verified: damaged"
    T-->>A: Verification result
    A->>U: "Verified. Price $200. How much refund?"
    
    U->>A: "200"
    A->>T: refund_api("ITEM_001", 200)
    T->>M: Process refund
    M-->>T: "Refund processed: REF-ITEM_001-12345"
    T-->>A: Transaction ID
    
    A->>T: audit_log("Refund processed", "Full refund $200...")
    T->>L: Log action
    L-->>T: "Action logged"
    T-->>A: Logged
    
    A->>U: "Refund of $200 processed. Is there anything else?"
```

## Troubleshooting Query Flow

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent (Chatbot)
    participant T as Tool Node
    participant Q as Qdrant DB
    participant E as Embedding Model<br/>(MiniLM-L6-v2)
    
    U->>A: "My Canon G3000 shows error 5B00"
    A->>T: troubleshooting_knowledge_base("Canon G3000 error 5B00")
    T->>E: Encode query
    E-->>T: [384-dim vector]
    T->>Q: query_points(vector, limit=3)
    Q-->>T: Top 3 similar chunks
    Note over Q,T: Cosine similarity search
    T-->>A: Formatted results with title, section, content
    A->>U: "Error 5B00 indicates ink absorber full.<br/>Here's how to reset: 1. Turn off..."
```

## Data Chunking Process

```mermaid
flowchart TD
    A[JSON Document] --> B{Parse Content}
    B --> C[Extract Title<br/># Header]
    B --> D[Split by Sections<br/>## Headers]
    
    D --> E[Section 1]
    D --> F[Section 2]
    D --> G[Section N]
    
    E --> H[Create Chunk 1<br/>Title + Section + Body]
    F --> I[Create Chunk 2<br/>Title + Section + Body]
    G --> J[Create Chunk N<br/>Title + Section + Body]
    
    H --> K[Save to chunks/DOC_001_CHUNK_001.txt]
    I --> L[Save to chunks/DOC_001_CHUNK_002.txt]
    J --> M[Save to chunks/DOC_001_CHUNK_00N.txt]
    
    K --> N[chunks_metadata.json]
    L --> N
    M --> N
    
    N --> O[Metadata Record:<br/>chunk_id, doc_id, title,<br/>section_title, text, etc.]
    
    style A fill:#e1f5ff
    style N fill:#ffe1f5
    style O fill:#fff5e1
```

## Refund Validation Logic

```mermaid
flowchart TD
    A[refund_api called] --> B{Item ID<br/>is numeric?}
    B -->|Yes| C[Convert to ITEM_00X]
    B -->|No| D[Use as-is]
    
    C --> E{Item exists<br/>in orders?}
    D --> E
    
    E -->|No| F[Return Error:<br/>Item not found]
    E -->|Yes| G[Get item price]
    
    G --> H{Same item as<br/>last attempt?}
    H -->|No| I[Reset context:<br/>attempts = 0]
    H -->|Yes| J[Keep context]
    
    I --> K{Amount valid?<br/>1 ≤ amt ≤ price}
    J --> K
    
    K -->|Yes| L[Process refund]
    K -->|No| M[Increment attempts]
    
    L --> N[Reset context]
    N --> O[Return success:<br/>Transaction ID]
    
    M --> P{Attempts > 3?}
    P -->|Yes| Q[Auto-select<br/>random amount]
    P -->|No| R[Return error:<br/>Invalid amount]
    
    Q --> L
    
    style L fill:#e1ffe1
    style F fill:#ffe1e1
    style R fill:#ffe1e1
    style O fill:#e1f5ff
```

## Component Architecture

```mermaid
graph TB
    subgraph "troubleshoot_agent.py"
        A[Main Loop] --> B[Graph Executor]
        B --> C[Chatbot Node]
        B --> D[Tool Node]
        
        C --> E[Gemini 2.0 Flash<br/>with Tools]
        
        D --> F[check_order_history]
        D --> G[verify_broken_item]
        D --> H[refund_api]
        D --> I[troubleshooting_knowledge_base]
        D --> J[audit_log]
        D --> K[route_query]
    end
    
    subgraph "State Management"
        L[MemorySaver<br/>Checkpointer]
        M[AgentState<br/>messages + user_id]
    end
    
    subgraph "External Dependencies"
        N[Qdrant Client]
        O[SentenceTransformer<br/>MiniLM-L6-v2]
        P[Google Gemini API]
    end
    
    B -.->|Save/Load| L
    C -.->|Update| M
    D -.->|Update| M
    
    I --> N
    I --> O
    E --> P
    
    style C fill:#e1ffe1
    style D fill:#ffe1e1
    style M fill:#fff5e1
```

## Knowledge Base Schema

```mermaid
erDiagram
    METADATA_JSON {
        string doc_id PK
        string file_name
        string title
        string category
        string doc_type
        string version
        string effective_date
        string summary
        array keywords
        string content
    }
    
    CHUNK {
        string chunk_id PK
        string doc_id FK
        string file_name
        string chunk_file
        string title
        string section_title
        int section_index
        string text
        string doc_type
        string version
        string effective_date
    }
    
    QDRANT_POINT {
        int id PK
        array vector
        object payload
    }
    
    METADATA_JSON ||--o{ CHUNK : "splits into"
    CHUNK ||--|| QDRANT_POINT : "embedded as"
    
    QDRANT_POINT ||--|| CHUNK : "payload contains"
```

## Conversation State Machine

```mermaid
stateDiagram-v2
    [*] --> Idle
    
    Idle --> Processing: User Input
    
    Processing --> ToolExecution: LLM requests tool
    Processing --> Responding: LLM has answer
    
    ToolExecution --> CheckOrderHistory: check_order_history
    ToolExecution --> VerifyBroken: verify_broken_item
    ToolExecution --> ProcessRefund: refund_api
    ToolExecution --> SearchKB: troubleshooting_knowledge_base
    ToolExecution --> LogAction: audit_log
    ToolExecution --> RouteQuery: route_query
    
    CheckOrderHistory --> Processing: Return results
    VerifyBroken --> Processing: Return verification
    ProcessRefund --> LogAction: Log refund
    SearchKB --> Processing: Return KB results
    LogAction --> Processing: Logged
    RouteQuery --> Processing: Return category
    
    Responding --> Idle: Display response
    Responding --> [*]: User exits
```
