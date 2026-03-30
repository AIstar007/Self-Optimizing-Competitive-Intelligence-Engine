# Self-Optimizing Competitive Intelligence Engine

An autonomous multi-agent system for market research, competitor analysis, strategic forecasting, and intelligence reporting.

## Architecture

This project follows Clean Architecture principles with strict layer separation:

```
core/
├── domain/          # Domain entities, value objects, interfaces (no dependencies)
├── application/     # Use cases, services, agents, orchestrators
├── infrastructure/  # Database, browser, LLM, vector store, knowledge graph
└── interfaces/      # API, CLI
```

## Features

- **Multi-Agent System**: Specialized agents for research, analysis, strategy, reporting, and critique
- **Knowledge Graph**: Graph-RAG for enhanced intelligence retrieval
- **Three-Tier Memory**: Working context, vector storage, and structured knowledge
- **Multi-LLM Routing**: Selects optimal models based on task requirements
- **Auto-Learning**: Agents improve over time through feedback loops
- **Autonomous Loop**: Continuous competitive intelligence monitoring

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure your API keys.

## Usage

### API Server

```bash
uvicorn core.interfaces.api.main:app --reload
```

### CLI

```bash
python -m core.interfaces.cli research "Analyze OpenAI competitors"
```

## Development

Run tests:

```bash
pytest
```

## License

MIT