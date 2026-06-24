# 🔥 IraFire — AI Multi-Agent Fire Safety Engineering System

An automated fire safety compliance pipeline built with LangGraph, 
OpenAI, and QdrantDB for NBC India 2016 code analysis.

## Architecture
CAD/PDF Input → Fire & Safety Agent → Code Agent (RAG)

→ System Design Agent → Hydraulic Agent

→ Compliance Agent → Report Agent → Word Report

## Agents

| Agent | Role | LLM |
|-------|------|-----|
| Fire & Safety Agent | Occupancy & hazard classification | GPT-4o-mini |
| Code Agent | NBC rule lookup via RAG + Qdrant | GPT-4o-mini |
| System Design Agent | Detection & suppression system design | GPT-4o-mini |
| Hydraulic Agent | Pipe sizing, water demand, pressure calcs | Pure Python |
| Compliance Agent | Rule validation & scoring | Pure Python |
| Report Agent | Word document generation | python-docx |

## Tech Stack

- **Orchestration:** LangGraph
- **LLM:** OpenAI GPT-4o-mini
- **Vector DB:** QdrantDB (local Docker)
- **CAD Parsing:** ezdxf
- **PDF Parsing:** PyMuPDF
- **Report:** python-docx

## Setup

1. Clone the repo
2. Create virtual environment:
```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
```
3. Create `.env` file:
OPENAI_API_KEY=your_key_here
4. Start Qdrant:
```bash
   docker run -p 6333:6333 qdrant/qdrant
```
5. Embed NBC rules (one time only):
```bash
   python -m tools.qdrant_tools
```
6. Run pipeline:
```bash
   python main.py your_file.dxf dxf
   python main.py your_file.pdf pdf
```

## Output

- `output/fire_safety_report.docx` — Full compliance report
- `output/pipeline_output.json` — Raw pipeline data for debugging
