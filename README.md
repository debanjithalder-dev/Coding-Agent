# Groq-Powered Coding Agent

A simple Python-based AI coding agent that helps identify and fix straightforward bugs in C++ source files using Groq's `openai/gpt-oss-120b` model and native tool calling.

The project uses a small tool-calling loop without LangGraph.

## Features

- Accepts bug descriptions in plain English.
- Searches the project directory for relevant source files.
- Searches inside a selected file using keywords or a line range.
- Replaces an exact line after checking that the current content matches.
- Creates a `.bak` backup before modifying a file.
- Prints tool calls, inputs, and results to make the agent's workflow visible.
- Limits the agent to a maximum of three attempts.

## Tools

| Tool | Purpose |
|---|---|
| `search_files` | Finds project files relevant to the bug description. |
| `search_in_file` | Finds relevant code and line numbers using keywords or a line range. |
| `replace_line` | Replaces one exact line after validating the existing content. |

## Project structure

A suggested project layout is:

```text
Groq-Coding-Agent/
├── coding_agent.py
├── boiler_plate.cpp
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore
```

Do not upload your real `.env` file or your virtual environment (`.venv/`).

## Requirements

- Python 3.10 or later
- A Groq API key
- The Python packages listed in `requirements.txt`

## Setup

### 1. Download the repository

Download the repository ZIP from GitHub and extract it, or clone it using Git.

### 2. Create and activate a virtual environment (recommended)

Windows PowerShell:

```powershell
uv venv
.venv\Scripts\activate
```

Alternatively:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

Using `uv`:

```powershell
uv pip install -r requirements.txt
```

Or using pip:

```powershell
pip install -r requirements.txt
```

You can also add the packages to a uv-managed project with:

```powershell
uv add groq python-dotenv
```

### 4. Configure the Groq API key

Create a file named `.env` in the project root and add:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Replace the placeholder with your own API key. Never commit or share this file.

The repository includes `.env.example` as a template. Copy it to `.env` and add your key.

### 5. Run the agent

```powershell
python coding_agent.py
```

Or:

```powershell
uv run coding_agent.py
```

When prompted, describe the bug in simple English.

## How it works

1. The user describes a bug.
2. The agent sends the request and available tool definitions to Groq.
3. The model can call `search_files` to find relevant files.
4. The model can call `search_in_file` to inspect code and line numbers.
5. The model can call `replace_line` to make a targeted source-code change.
6. The agent inspects the modified source and reports the result.

## Safety and limitations

- The replacement tool checks that the existing line exactly matches the supplied old line before editing.
- A `.bak` backup is created before the first modification to a file.
- The current verification checks the edited source text. It does **not** compile or execute the C++ program, so a reported fix is not proof of runtime correctness.
- The agent is intended for simple debugging tasks, not large refactoring or security-critical code changes.
- Review all AI-generated changes before using them.
- Keep API keys private. If a key is accidentally exposed, revoke it and generate a new one.

## Technology stack

- Python
- Groq API
- `openai/gpt-oss-120b`
- `groq` Python SDK
- `python-dotenv`

## License

No license has been specified yet. Add a license file if you want to define how others may use, modify, and distribute this project.
