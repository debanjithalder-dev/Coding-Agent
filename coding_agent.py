import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq


# ----------------------------- Configuration -----------------------------

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "openai/gpt-oss-120b"

# This is the folder in which main.py is located.
PROJECT_ROOT = Path(__file__).resolve().parent

MAX_ATTEMPTS = 3
MAX_TOOL_ROUNDS_PER_ATTEMPT = 10

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".idea", ".vscode", "build", "dist"
}
ALLOWED_EXTENSIONS = {
    ".cpp", ".cc", ".cxx", ".h", ".hpp", ".c", ".py", ".txt"
}

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY was not found. Add it to the .env file."
    )

client = Groq(api_key=GROQ_API_KEY)


# ----------------------------- Helper functions -----------------------------

def safe_project_path(relative_path: str) -> Path:
    """Resolve a path and prevent access outside PROJECT_ROOT."""
    candidate = (PROJECT_ROOT / relative_path).resolve()

    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError:
        raise ValueError("Access denied: path is outside the project folder.")

    if not candidate.is_file():
        raise FileNotFoundError(f"File does not exist: {relative_path}")

    return candidate


def query_words(query: str) -> list[str]:
    """Extract useful words from a natural-language search query."""
    ignored = {
        "the", "and", "for", "with", "that", "this", "from", "into",
        "when", "what", "where", "which", "does", "give", "show",
        "function", "code", "bug", "error", "incorrect", "wrong"
    }
    words = re.findall(r"[A-Za-z_][A-Za-z_0-9]*", query.lower())
    return [word for word in words if word not in ignored and len(word) > 1]


# ----------------------------- TOOL 1: File search -----------------------------

def search_files(query: str) -> str:
    """
    Search project files and rank them by matching query words against
    filenames and file contents.
    """
    print("\n[TOOL 1 CALLED] search_files")
    print(f"[TOOL 1 INPUT] Query: {query}")

    words = query_words(query)
    matches = []

    for current_dir, dir_names, file_names in os.walk(PROJECT_ROOT):
        dir_names[:] = [
            name for name in dir_names if name not in EXCLUDED_DIRS
        ]

        for file_name in file_names:
            path = Path(current_dir) / file_name

            if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            searchable = (file_name + "\n" + content).lower()
            score = sum(searchable.count(word) for word in words)

            if not words:
                score = 1

            if score > 0:
                relative_path = path.relative_to(PROJECT_ROOT).as_posix()
                matches.append((score, relative_path))

    matches.sort(key=lambda item: item[0], reverse=True)
    results = matches[:10]

    if not results:
        message = "No matching source files were found."
    else:
        message = "\n".join(
            f"- {relative_path} (relevance score: {score})"
            for score, relative_path in results
        )

    print("[TOOL 1 RESULT]")
    print(message)
    return message


# ----------------------------- TOOL 2: Search inside a file -----------------------------

def search_in_file(
    path: str,
    query: str = None,
    line_start: int = None,
    line_end: int = None
) -> str:

    print("\n[TOOL 2 CALLED] search_in_file")
    print(f"[TOOL 2 INPUT] File: {path}")

    try:
        file_path = safe_project_path(path)
        lines = file_path.read_text(
            encoding="utf-8"
        ).splitlines()

    except Exception as error:
        return f"ERROR: {error}"

    # Option 1: Search using a line range
    if line_start is not None and line_end is not None:

        if line_start < 1 or line_end < line_start:
            return "ERROR: Invalid line range."

        selected_lines = []

        for i in range(line_start - 1, min(line_end, len(lines))):
            selected_lines.append(
                f"{i + 1}: {lines[i]}"
            )

        result = "\n".join(selected_lines)

    # Option 2: Search using keywords
    elif query:

        words = query_words(query)
        selected_lines = []

        for i, line in enumerate(lines):
            if any(word in line.lower() for word in words):
                selected_lines.append(
                    f"{i + 1}: {line}"
                )

        result = "\n".join(selected_lines)

        if not result:
            result = "No matching lines found."

    else:
        result = "ERROR: Provide either a query or a line range."

    print("[TOOL 2 RESULT]")
    print(result)

    return result


# ----------------------------- TOOL 3: Replace a line -----------------------------

def replace_line(
    path: str,
    line_number: int,
    old_line: str,
    new_line: str
) -> str:
    """
    Replace exactly one specified line. A .bak backup is created before
    the first modification to that file.
    """
    print("\n[TOOL 3 CALLED] replace_line")
    print(
        f"[TOOL 3 INPUT] File: {path} | Line: {line_number}\n"
        f"Old: {old_line}\nNew: {new_line}"
    )

    try:
        file_path = safe_project_path(path)
        lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)

        if line_number < 1 or line_number > len(lines):
            raise ValueError(
                f"Line number {line_number} is outside the file "
                f"(1-{len(lines)})."
            )

        current_line = lines[line_number - 1].rstrip("\r\n")

        if current_line != old_line:
            raise ValueError(
                "The current line does not exactly match old_line. "
                f"Current content: {current_line!r}"
            )

        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        if not backup_path.exists():
            shutil.copy2(file_path, backup_path)
            print(f"[TOOL 3] Backup created: {backup_path.name}")

        ending = ""
        if lines[line_number - 1].endswith("\r\n"):
            ending = "\r\n"
        elif lines[line_number - 1].endswith("\n"):
            ending = "\n"

        lines[line_number - 1] = new_line + ending
        file_path.write_text("".join(lines), encoding="utf-8")

        result = (
            f"SUCCESS: Replaced line {line_number} in {path}.\n"
            f"New line: {new_line}\n"
            f"Backup: {backup_path.name}"
        )
        print("[TOOL 3 RESULT]")
        print(result)
        return result

    except Exception as error:
        result = f"ERROR: Replacement failed: {error}"
        print("[TOOL 3 RESULT]")
        print(result)
        return result


# ----------------------------- Tool definitions for Groq -----------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": (
                "Search the project for files relevant to the user's bug. "
                "Call this first to identify the relevant source file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Bug description and relevant code concepts."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_file",
            "description": (
                "Search inside a file using either keywords "
                "or a specific line range. "
                "You can provide query OR line_start and line_end."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project-relative file path."
                    },
                    "query": {
                        "type": "string",
                        "description": "Keyword or function name to search."
                    },
                    "line_start": {
                        "type": "integer",
                        "description": "Starting line number."
                    },
                    "line_end": {
                        "type": "integer",
                        "description": "Ending line number."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_line",
            "description": (
                "Replace one exact line in a project file. You must first "
                "inspect the line and provide its exact current contents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Project-relative file path."
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "1-based line number."
                    },
                    "old_line": {
                        "type": "string",
                        "description": "Exact existing line, without newline."
                    },
                    "new_line": {
                        "type": "string",
                        "description": "Corrected replacement line."
                    }
                },
                "required": ["path", "line_number", "old_line", "new_line"]
            }
        }
    }
]


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute only the tools exposed to the LLM."""
    if name == "search_files":
        return search_files(**arguments)
    if name == "search_in_file":
        return search_in_file(**arguments)
    if name == "replace_line":
        return replace_line(**arguments)

    return f"ERROR: Unknown tool: {name}"


# ----------------------------- Agent instructions -----------------------------

SYSTEM_PROMPT = """
You are a careful C++ coding/debugging agent.

The user describes a bug in simple English. Your job is to locate and fix
that bug using ONLY the three available tools.

MANDATORY WORKFLOW:
1. Call search_files to identify relevant source files.
2. Call search_in_file on the most relevant file to inspect the actual code
   and line numbers.
3. Understand the cause before changing anything.
4. Call replace_line with the exact current line and the corrected line.
5. Call search_in_file again to inspect and verify the changed code.
6. Do not claim that a change was made unless replace_line returned SUCCESS.
7. Never invent file paths, line numbers, or existing code.
8. Do not modify unrelated code.
9. Do not create test cases or introduce bugs.
10. If the information is insufficient, explain what is missing instead of
    making a speculative edit.
11. Make the smallest reasonable correction. If a fix needs multiple line
    changes, inspect and replace them one at a time.
12. Do not run shell commands or claim that the program was compiled or tested.

At the end of each attempt, finish with exactly one status line:
STATUS: FIXED
or
STATUS: NOT_FIXED

Use STATUS: FIXED only after a successful replacement and a follow-up
inspection of the modified code. Explain what was changed briefly.
"""


# ----------------------------- Main agent loop -----------------------------

def run_agent() -> None:
    print("=" * 65)
    print("          SIMPLE GROQ-POWERED C++ CODING AGENT")
    print("=" * 65)
    print(f"Model: {MODEL}")
    print(f"Project folder: {PROJECT_ROOT}")
    print(f"Maximum attempts: {MAX_ATTEMPTS}")
    print("=" * 65)

    bug_description = input("\nDescribe the bug in simple English: ").strip()

    if not bug_description:
        print("No bug description provided. Exiting.")
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Please solve this bug:\n"
                f"{bug_description}\n\n"
                "Start by searching for the relevant files. "
                "Do not assume which file contains the bug."
            )
        }
    ]

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print("\n" + "=" * 65)
        print(f"                 ATTEMPT {attempt}/{MAX_ATTEMPTS}")
        print("=" * 65)

        # Keep these across attempts: a replacement made in one attempt
        # may be verified during the next attempt.
        if attempt == 1:
            replacement_succeeded = False
            verification_succeeded = False
            replacement_details: list[tuple[str, str]] = []

        for tool_round in range(1, MAX_TOOL_ROUNDS_PER_ATTEMPT + 1):
            print(f"\n[LLM] Calling Groq (tool round {tool_round})...")

            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.1,
                    max_tokens=4096
                )
            except Exception as error:
                print(f"[LLM ERROR] {error}")
                break

            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls

            assistant_payload = {
                "role": "assistant",
                "content": assistant_message.content
            }
            if tool_calls:
                assistant_payload["tool_calls"] = [
                    call.model_dump(exclude_none=True) for call in tool_calls
                ]
            messages.append(assistant_payload)

            if not tool_calls:
                final_text = assistant_message.content or ""
                print("\n[LLM RESPONSE]")
                print(final_text)

                status_fixed = "STATUS: FIXED" in final_text

                if (
                    status_fixed
                    and replacement_succeeded
                    and verification_succeeded
                ):
                    print("\n[SUCCESS] Bug correction was applied and inspected.")
                    return

                print("\n[ATTEMPT RESULT] The agent has not verified a successful fix.")
                break

            for tool_call in tool_calls:
                tool_name = tool_call.function.name

                try:
                    arguments = json.loads(tool_call.function.arguments)
                    tool_result = execute_tool(tool_name, arguments)
                except Exception as error:
                    tool_result = f"ERROR: Invalid tool call: {error}"
                    print(f"[TOOL ERROR] {tool_result}")

                if tool_name == "replace_line" and tool_result.startswith("SUCCESS:"):
                    replacement_succeeded = True
                    new_line = arguments.get("new_line", "")
                    path = arguments.get("path", "")
                    replacement_details.append((path, new_line))
                    verification_succeeded = False

                elif tool_name == "search_in_file" and replacement_details:
                    path = arguments.get("path", "")
                    searched_text = tool_result
                    for changed_path, changed_line in replacement_details:
                        if path == changed_path and changed_line in searched_text:
                            verification_succeeded = True

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })

        if attempt < MAX_ATTEMPTS:
            messages.append({
                "role": "user",
                "content": (
                    f"Attempt {attempt} did not produce a verified fix. "
                    "Review the previous tool results, correct any mistake, "
                    "and continue. Do not repeat a successful replacement. "
                    "Inspect the current file before making another edit."
                )
            })

    print("\n" + "=" * 65)
    print("[FAILED] The agent could not solve the bug within 3 attempts.")
    print("=" * 65)


if __name__ == "__main__":
    run_agent()
