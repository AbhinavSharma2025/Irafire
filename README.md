<div align="center">

# 🔥 IraFire
### AI Multi-Agent Fire Safety Engineering System

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-purple?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat-square&logo=openai)](https://openai.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-VectorDB-red?style=flat-square)](https://qdrant.tech)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Automated fire safety compliance analysis powered by a collaborative multi-agent AI pipeline.**  
Takes a building floor plan as input. Produces a fully cited, NBC India 2016 compliant fire safety report as output.

[Features](#-features) · [Architecture](#-architecture) · [Agents](#-agent-breakdown) · [Setup](#-setup) · [Usage](#-usage) · [Output](#-sample-output)

</div>

---

## 🎯 What is IraFire?

IraFire is an end-to-end automated fire safety design system built for real-world engineering workflows. Traditional fire safety compliance analysis requires multiple specialists — a fire engineer, a CAD draftsman, a hydraulics engineer, and a compliance checker — working sequentially over days or weeks.

IraFire replicates this entire workflow as a **LangGraph multi-agent pipeline** that runs in minutes. Each agent is a specialist: it receives structured input, performs its job, and hands a richer output to the next agent — exactly how a professional engineering office works.

> Built during an AI Engineer internship at **IraStrive Technologies** as a real production tool for fire safety consultants.

---

## ✨ Features

- 📐 **Dual input support** — DXF/DWG CAD files and PDF floor plans
- 🏢 **Automatic room classification** — occupancy group, zone type, hazard level
- 📚 **RAG-powered code lookup** — semantic search over NBC India 2016 & NFPA rules via QdrantDB
- 🚿 **Hydraulic calculations** — Hazen-Williams pressure equations, water demand, pump sizing
- ✅ **Compliance scoring** — automated violation detection with NBC clause references
- 📄 **Professional Word report** — cover page, room tables, hydraulic calcs, violation log
- 🔒 **Deterministic math** — hydraulic and compliance agents use pure Python (no LLM hallucinations)
- ⚡ **Fault-tolerant pipeline** — per-room error handling, pipeline never crashes on partial failures

---

## 🏗 Architecture

<div align="center">
  <img src="https://raw.githubusercontent.com/AbhinavSharma2025/Irafire/main/documents/irafire_system_architecture.png" alt="IraFire System Architecture" width="750"/>
</div>

<br/>

## 🔀 LangGraph Pipeline

<div align="center">
  <img src="https://raw.githubusercontent.com/AbhinavSharma2025/Irafire/main/documents/irafire_langgraph_pipeline.png" alt="IraFire LangGraph Pipeline" width="450"/>
</div>

**The shared state** (`FireSafetyState`) flows through every node — each agent reads what it needs and writes its output back, making the full context available downstream.

---

## 🤖 Agent Breakdown

| # | Agent | Type | Responsibility |
|---|-------|------|---------------|
| 1 | **CAD Parser** | Python tool | Reads DXF/PDF, extracts room geometry via shoelace formula |
| 2 | **Fire & Safety Agent** | GPT-4o-mini | Classifies occupancy group, risk level, required exits |
| 3 | **Code Agent** | GPT-4o-mini + Qdrant | RAG search on NBC rules → per-room fire requirements |
| 4 | **System Design Agent** | GPT-4o-mini | Specifies detectors, sprinklers, extinguishers per room |
| 5 | **Hydraulic Agent** | Pure Python | Hazen-Williams equations, water demand, pump sizing |
| 6 **Compliance Agent** | Pure Python | Violation detection, compliance score /100 |
| 7 | **Report Agent** | python-docx | Assembles professional Word document |

### Why two agents use pure Python instead of an LLM?

The Hydraulic and Compliance agents perform **exact mathematical calculations**. LLMs can hallucinate numbers, which in fire safety engineering could have serious consequences. Pure Python gives us deterministic, auditable, repeatable results every time.

---

## 🧠 The RAG Pipeline (Code Agent)

Room data (type + hazards)
│
▼
Build semantic query
e.g. "Mechanical room fire requirements NBC"
│
▼
Embed query → search QdrantDB
(NBC 2016 rules stored as vector embeddings)
│
▼
Top 3 matching rules retrieved with references
│
▼
GPT-4o-mini: room + rules → fire requirements JSON
with NBC clause citations + confidence score


Rules are embedded **once** at setup and reused across all runs — making ongoing costs negligible.

---

## 🗂 Project Structure

## 🗂 Project Structure

```
📦 fire_safety_agent
├── 🤖 agents/
│   ├── fire_safety_agent.py       # Occupancy & hazard classification
│   ├── code_agent.py              # RAG-powered NBC rule lookup
│   ├── system_design_agent.py     # Equipment specification per room
│   ├── hydraulic_agent.py         # Hydraulic calculations (pure Python)
│   ├── compliance_agent.py        # Violation detection (pure Python)
│   └── report_agent.py            # Word document generation
│
├── 🛠 tools/
│   ├── cad_parser.py              # DXF/PDF parsing & geometry extraction
│   ├── cad_parser_node.py         # LangGraph wrapper for CAD parser
│   └── qdrant_tools.py            # Vector DB embed + search utilities
│
├── 🔗 pipeline/
│   └── graph.py                   # LangGraph StateGraph definition
│
├── 📚 knowledge_base/
│   └── nbc_rules.json             # Curated NBC India 2016 fire code rules
│
├── 📁 output/                     # Generated reports land here
│
├── config.py                      # API keys & configuration
├── main.py                        # Pipeline entry point
└── requirements.txt
```

## ⚙️ Setup

### Prerequisites
- Python 3.11+
- Docker Desktop (for Qdrant)
- OpenAI API key

### 1. Clone & install

```bash
git clone https://github.com/AbhinavSharma2025/Irafire.git
cd Irafire/fire_safety_agent
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the project root:

OPENAI_API_KEY=your_key_here


### 3. Start Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 4. Embed NBC rules (one-time setup)

```bash
python -m tools.qdrant_tools
# ✅ Embedded and upserted 10 rules into collection 'nbc_fire_rules'
```

---

## 🚀 Usage

```bash
# DXF/CAD input
python main.py your_building.dxf dxf

# PDF floor plan input
python main.py your_floorplan.pdf pdf
```

### Expected output

🚀 Starting Fire Safety Pipeline
File: building.dxf
Type: dxf

✅ Pipeline complete!
Current agent : report_agent
Rooms processed : 49
Compliance score: 87
Report saved to : output/fire_safety_report.docx
Debug JSON : output/pipeline_output.json


---

## 📄 Sample Output

The generated Word report includes:

- **Cover page** — project title, date, input file
- **Executive summary** — occupancy group, risk level, compliance score
- **Room analysis table** — all rooms with hazard class, sprinkler, detector, confidence
- **Hydraulic design** — water demand, pressure calculations, pump/tank requirements  
- **Compliance report** — score /100, violations table with NBC references
- **Review notes** — engineering assumptions flagged for manual verification

---

## 🛠 Tech Stack

| Technology | Role |
|------------|------|
| [LangGraph](https://github.com/langchain-ai/langgraph) | Multi-agent orchestration & state management |
| [OpenAI GPT-4o-mini](https://openai.com) | LLM for classification & design agents |
| [QdrantDB](https://qdrant.tech) | Vector database for NBC rule embeddings |
| [ezdxf](https://ezdxf.readthedocs.io) | DXF/DWG CAD file parsing |
| [PyMuPDF](https://pymupdf.readthedocs.io) | PDF floor plan text extraction |
| [python-docx](https://python-docx.readthedocs.io) | Word document generation |

---

## 🔮 Roadmap

- [ ] Web UI for file upload and report download
- [ ] Support for multi-floor buildings with cross-floor egress analysis
- [ ] Annotated CAD output with equipment placement overlays
- [ ] NFPA 13 sprinkler layout generation
- [ ] BOQ (Bill of Quantities) cost estimation module

---

## 👨‍💻 Author

**Abhinav Sharma**  
AI Engineer Intern @ IraStrive Technologies  
B.Tech Computer Science (Data Science) · VIT Vellore  

[![GitHub](https://img.shields.io/badge/GitHub-AbhinavSharma2025-181717?style=flat-square&logo=github)](https://github.com/AbhinavSharma2025)

---

<div align="center">
Built with ❤️ for the fire safety engineering community
</div>
