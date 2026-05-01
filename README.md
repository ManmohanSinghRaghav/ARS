# ARS - Autonomous Research Scientist (v3.1)

A high-fidelity, data-centric research engine that autonomously searches literature, generates novel hypotheses, and produces structured research papers. ARS has transitioned to a **Cloud-First Architecture**, leveraging the world's most powerful LLMs while ensuring stability via a proactive governance layer.

## 🚀 Key Innovations

- **JSON-as-Source**: The manuscript is a structured JSON object, enabling sub-second real-time PDF rendering in the browser. No more slow LaTeX recompilations.
- **Dual-Layer Rendering**:
    - **Instant Preview**: Browser-side rendering via `@react-pdf/renderer`.
    - **Pro PDF Engine**: Backend `ReportLab` generator for high-fidelity, academic-grade distribution.
- **Proactive Governor**: A sliding-window rate limiter that monitors RPM/TPM in real-time. It enforces "breathing space" between API calls, allowing the system to run indefinitely on Free Tier keys without triggering 429 rate limit errors.
- **Adversarial RefLens**: A verification layer that decomposes research claims into atomic facts and performs multi-hop tracing against grounded literature to eliminate hallucinations.
- **Theoretical Mode**: When empirical code execution is restricted, agents shift to formal logic and mathematical derivation to prove or disprove hypotheses.

## 🏗️ Architecture

### Multi-Agent Intelligence (CrewAI)
ARS uses a role-playing agentic architecture:
```
Researcher → Lead Scientist → ML Engineer ⇄ Code Critic → Academic Writer ⇄ Verifier
```

| Agent | Role | Supported Providers |
|-------|------|--------------------|
| **Heavy Engine** | Reasoning & Synthesis | Gemini 2.0 Pro, Claude 3.5 Sonnet, GPT-4o |
| **Light Engine** | Extraction & Discovery | Gemini 1.5 Flash, Llama 3 (via Groq) |

## 🛠️ Requirements

- **Python** 3.10+
- **Node.js** 18+
- **Search**: Tavily API key (Required for web-scale discovery).
- **LLMs**: One or more API keys from:
    - **Google Gemini** (Free tier supported!)
    - **Groq Cloud** (Llama 3/3.1)
    - **Anthropic Claude**
    - **OpenAI**

## 🏁 Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Set API keys in .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:3000`.

## 📊 Governance & Tiers

ARS intelligently routes tasks based on complexity:
- **Heavy Tier**: (High TPM) Handles writing and complex reasoning.
- **Light Tier**: (High RPM) Handles chat, criticism, and data extraction.

The **Settings** panel allows you to configure specific RPM/TPM limits per provider, ensuring the **Governor** never oversteps your API quotas.

## 🛡️ Security
- **Encrypted Vault**: API keys are AES-GCM encrypted in Firestore using your unique `SETTINGS_ENCRYPTION_KEY`.
- **Zero Local Execution**: Agentic code is executed exclusively in remote **Modal** sandboxes or via theoretical derivation, protecting your local machine from untrusted code.
