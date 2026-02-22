# Sonar

Conversational agent framework for querying structured data sources via natural language.

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