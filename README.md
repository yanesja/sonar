# Sonar

Conversational agent framework for querying structured data sources via natural language.

## Setup

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Configure environment
cp .env.example .env
# Edit .env and add your credentials
```

## Run

```bash
python scripts/chat.py
```

## Structure

```
sonar/
├── .env                        # secrets (gitignored)
├── .env.example                # env var template
├── .gitignore
├── pyproject.toml              # deps + project metadata
├── README.md
│
├── src/
│   └── sonar/
│       ├── __init__.py
│       ├── agent.py            # agent class + create_agent logic
│       ├── config.py           # Config model + loaders
│       ├── tools.py            # tool functions
│       └── prompts/
│           └── system.yaml     # system prompt
│
├── scripts/
│   └── chat.py                 # chat loop entrypoint
│
└── tests/
    └── __init__.py
```