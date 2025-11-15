# Super-Prompt: AI Code Agent

This project provides a powerful, AI-driven code agent capable of understanding and executing complex coding tasks. It can read, write, and refactor code, run shell commands, and follow a structured, plan-based workflow to ensure reliability and safety.

## 🚀 Quickstart

Get the recommended agent (`ModernAIAgent`) running in 3 simple steps.

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your_openai_api_key_here
```

### 3. Run the Agent
Execute the main script to start the agent in interactive mode:
```bash
python -m src.super_prompt.main
```
This will launch an interactive menu where you can chat with the agent or run pre-defined tasks.

## ✨ Example Usage

Once the agent is running, you can give it complex tasks in natural language:

> "Refactor the `app.py` file. Improve the variable names, add type hints to all functions, and include docstrings."

> "Create a new file named `utils.py` with a function that validates an email address and another that formats a CPF number. Then, create a `tests/test_utils.py` file with pytest tests for both functions."

> "Run the test suite using `pytest` and report the results. If any tests fail, read the failing test file, identify the bug in the source code, and fix it."

## 🤖 Available Agents

This project includes multiple agent implementations:

*   **`ModernAIAgent` (Recommended)**: A robust and production-ready agent using native OpenAI Function Calling and a ReAct (Reason-Act) architecture. It follows a strict plan-and-execute workflow, making it reliable for complex tasks.
*   **`CodeAgent`**: A non-AI base class that provides the core file manipulation and safety features (backups, diffs, etc.).

## 🏗️ Project Structure

The project is organized as a standard Python package:

```
.
├── src/
│   └── super_prompt/
│       ├── __init__.py
│       ├── main.py               # Entry point for the interactive demo
│       ├── modern_ai_agent.py    # ⭐ Core agent logic
│       ├── tools.py              # Agent's tool implementations
│       ├── tool_decorator.py     # Decorator for tool registration
│       ├── config.py             # Pydantic configuration model
│       └── code_agent.py         # Base file manipulation class
├── tests/                        # Unit and integration tests
├── .env                          # API key configuration
├── requirements.txt              # Project dependencies
└── README.md                     # This file
```

## 🔧 Customization

You can easily customize the agent's behavior by modifying the `config.py` file or by passing a custom `AgentConfig` object during instantiation. This allows you to change the AI model, set the maximum number of iterations, and more.

```python
from src.super_prompt.modern_ai_agent import ModernAIAgent
from src.super_prompt.config import AgentConfig

# Use a more powerful model for higher quality results
config = AgentConfig(complex_model="gpt-4o")
agent = ModernAIAgent(config=config)

# Or a faster, cheaper model for simple tasks
config_mini = AgentConfig(simple_model="gpt-4o-mini")
agent_mini = ModernAIAgent(config=config_mini)
```

## 🛡️ Safety

The agent is designed with safety as a priority:

-   **File Backups:** Automatic backups are created in the `.code_agent_backups/` directory before any file is modified.
-   **Path Validation:** The agent cannot access files outside of its designated workspace.
-   **Iteration Limit:** A maximum number of iterations prevents infinite loops.
-   **Dangerous Command Blocking:** The `run_command` tool blocks potentially harmful shell commands.

---
*This project is an exploration of advanced AI agent architectures and is intended for educational and experimental purposes.*
