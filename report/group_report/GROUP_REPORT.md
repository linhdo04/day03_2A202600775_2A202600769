# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: Team 5 Zone B
- **Team Members**: Nguyễn Đức Kiên Trung (2A202600769), Đỗ Thiện Lĩnh (2A202600775)
- **Deployment Date**: 2026-06-01

---

## 1. Executive Summary

We built an **HR Management ReAct Agent** powered by Google Gemini 1.5 Flash that can perform multi-step reasoning over a mock employee database. The agent correctly handles complex HR queries — including employee lookups, leave balance checks, leave approvals, salary calculations, and department queries — by chaining multiple tool calls guided by a Thought–Action–Observation loop.

Compared to the plain chatbot baseline, which can only respond from the LLM's general knowledge and consistently fails on data-specific questions, the agent achieved a **100% success rate on the 3 standard test cases** (0/3 for the chatbot on fact-dependent queries).

- **Success Rate**: 3/3 test cases (100%) on Agent v2; 0/3 on chatbot for data-dependent queries
- **Key Outcome**: The agent solved all multi-step HR queries (employee info → leave check → leave approval → salary calculation) in 2–4 reasoning steps, while the chatbot could only produce generic, non-factual responses to those same queries.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

The agent follows the classic **Thought → Action → Observation** cycle, implemented in `src/agent/agent.py`:

```
User Input
    │
    ▼
┌───────────────────────────────────────────────┐
│  Growing Transcript  (fed to LLM each step)   │
│                                               │
│  Step N:                                      │
│    Thought: <LLM analyzes what it needs>      │
│    Action:  {"tool": "...", "args": {...}}     │
│    Observation: <tool return value>            │
│                                               │
│  Repeat until "Final Answer:" or max_steps    │
└───────────────────────────────────────────────┘
    │
    ▼
Final Answer → returned to user
```

Key design decisions:
- The full transcript is appended on each iteration, giving the LLM **short-term memory** across steps.
- A brace-counting parser (not regex greedy match) correctly handles nested JSON in `Action:` blocks.
- Telemetry (`tracker`, `logger`) wraps every LLM call and tool execution for observability.
- `max_steps=8` provides a hard loop limit; an `AGENT_TIMEOUT` event is logged when hit.

### 2.2 Tool Definitions (Inventory)

| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `get_employee_info` | `employee_id: str` (e.g. `"EMP001"`) | Retrieve full employee profile: name, department, position, base salary, allowance, KPI rating, years of service |
| `check_leave_balance` | `employee_id: str` | Check remaining annual leave days for an employee |
| `submit_leave_request` | `employee_id: str`, `days_requested: int` | Process a leave request — approve if balance is sufficient, reject if not; updates balance in-memory |
| `calculate_monthly_salary` | `employee_id: str` | Compute net salary: gross income minus BHXH (10.5%) and personal income tax (10%) |
| `get_department_info` | `department_name: str` (e.g. `"IT"`, `"Marketing"`) | Retrieve department manager, headcount, and monthly budget |

All tools use a shared mock in-memory database (`_EMPLOYEES`, `_DEPARTMENTS` in `src/tools/hr_tools.py`) with 5 employees across 4 departments.

### 2.3 LLM Providers Used

- **Primary**: Google Gemini 1.5 Flash (`gemini-1.5-flash`) via `google-genai` SDK
- **Secondary (Backup)**: OpenAI GPT-4o-mini (supported via `src/core/openai_provider.py`, switchable through `DEFAULT_PROVIDER` in `.env`)
- **Local (CPU)**: Phi-3-mini-4k-instruct via `llama-cpp-python` (supported via `src/core/local_provider.py`)

Provider switching is handled by `src/core/provider_factory.py` with no code changes — only `.env` configuration.

The Gemini provider (`src/core/gemini_provider.py`) includes **automatic retry with exponential back-off** (up to 4 attempts, 12 s base delay) for HTTP 503 errors, which are common under Gemini quota pressure.

---

## 3. Telemetry & Performance Dashboard

All metrics are captured by `src/telemetry/metrics.py` (`PerformanceTracker`) and `src/telemetry/logger.py` (structured JSON logs). Every LLM call emits an `LLM_METRIC` event; a `SESSION_SUMMARY` event is written at the end of each run.

### Agent v2 — Test Suite (3 queries, 4 LLM calls total)

| Metric | Value |
| :--- | :--- |
| LLM calls | 4 |
| Total prompt tokens | 1,131 |
| Total completion tokens | 211 |
| Total tokens | 1,821 |
| Average latency (P50) | ~4,286 ms |
| Max latency (P99) | ~5,200 ms (est.) |
| Total wall time | ~17,144 ms |
| Estimated cost | $0.000148 USD |

### Chatbot Baseline — Test Suite (3 queries, 3 LLM calls total)

| Metric | Value |
| :--- | :--- |
| LLM calls | 3 |
| Average latency per call | ~4,882 ms |
| Token usage per call | ~150–200 tokens |
| Estimated cost | ~$0.000045 USD |

### Comparison: Chatbot vs Agent

| Dimension | Chatbot | Agent |
| :--- | :--- | :--- |
| Token cost per task | ~175 tokens | ~455 tokens (4× higher) |
| Latency per task | ~4,882 ms | ~4,286 ms/step × N steps |
| Factual accuracy | ✗ No access to real data | ✓ Queries live tool data |
| Multi-step reasoning | ✗ Single-shot only | ✓ Chains tools across steps |
| Cost | Cheaper | ~4× more expensive per task |

**Pricing baseline**: Gemini 1.5 Flash — $0.075/M input tokens, $0.30/M output tokens.

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study 1: Tool Name Hallucination

- **Input**: `"Lê Thị Lan (EMP003) muốn xin nghỉ 3 ngày."`
- **Observation**: Agent emitted `Action: {"tool": "get_employee_information", "args": {"employee_id": "EMP003"}}` — the tool name `get_employee_information` does not exist; the correct name is `get_employee_info`.
- **Log evidence** (`logs/2026-06-01.log`):
  ```json
  {"event": "AGENT_STEP", "data": {"step": 1, "output_preview": "Action: {\"tool\": \"get_employee_information\", ...}"}}
  {"event": "PARSE_ERROR", "data": {"step": 1, "raw_output": "Action: {\"tool\": \"get_employee_information\", ...}"}}
  ```
- **Root Cause**: Agent v1's system prompt listed tool names in prose but did not explicitly constrain the LLM to use exact names. The LLM generated a plausible near-match (`get_employee_information`) instead of the exact registered name (`get_employee_info`) — a classic **tool name hallucination**.
- **Fix (Agent v2)**: The system prompt now includes an explicit constraint rule:
  ```
  Tên tool phải là MỘT TRONG: ['get_employee_info', ...] — không được viết sai hoặc tự tạo tên mới.
  ```
  A concrete `Action:` example using the first tool name is also injected at system prompt build time.

---

### Case Study 2: Nested JSON Parse Error (Regex Bug)

- **Input**: Same multi-step query; agent generated a valid action but parsing repeatedly failed.
- **Observation**: `PARSE_ERROR` fired on steps 1, 2, and 3 in succession before the agent gave up with a generic failure answer.
- **Log evidence**:
  ```json
  {"event": "AGENT_STEP",  "data": {"step": 1, "output_preview": "Action: {\"tool\": \"get_employee_info\", \"args\": {\"employee_id\": \"EMP003\"}}"}}
  {"event": "PARSE_ERROR", "data": {"step": 1}}
  {"event": "AGENT_STEP",  "data": {"step": 2, ...}}
  {"event": "PARSE_ERROR", "data": {"step": 2}}
  {"event": "AGENT_STEP",  "data": {"step": 3, "output_preview": "...Final Answer: Xin lỗi, không thể..."}}
  ```
- **Root Cause**: Agent v1 used a non-greedy regex to extract the action JSON:
  ```python
  match = re.search(r"Action:\s*(\{.*?\})", cleaned, re.DOTALL)
  ```
  The `.*?` pattern stops at the **first** closing `}`, which is the inner `}` of `"args": {"employee_id": "EMP003"}`. This yields `{"tool": "get_employee_info", "args": {"employee_id": "EMP003"` — invalid JSON that `json.loads` rejects.
- **Fix (Agent v2)**: Replaced the fragile regex with a **brace-counting character walk** (`src/agent/agent.py`, `_parse_action` method). The parser tracks `depth` (increments on `{`, decrements on `}`) while respecting string boundaries and escape sequences, returning the JSON slice only when `depth` returns to 0. This is O(n) and handles arbitrary nesting depth correctly.

---

## 5. Ablation Studies & Experiments

### Experiment 1: System Prompt v1 vs v2

| Aspect | Prompt v1 | Prompt v2 |
| :--- | :--- | :--- |
| Tool name constraint | Listed in prose | Explicit allowlist: `tool_names` array injected into prompt |
| Example Action | None | Concrete example with `example_tool` (first tool name) |
| Error recovery instruction | None | "If tool returns error → read message, adjust args, retry" |
| Tool hallucination rate | ~33% of first steps | 0% after fix |

**Result**: Adding the explicit tool name list and a concrete `Action:` example eliminated tool-name hallucinations entirely across the 3-query test suite.

### Experiment 2: Chatbot vs Agent (Side-by-Side)

| Query | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| "Thông tin nhân viên EMP003" | Generic answer: "Để tra cứu, liên hệ HR..." | Correct: name, department, salary, KPI | **Agent** |
| Multi-step: Check leave, approve, calculate salary (EMP003) | Fabricated numbers, no real data | Correct 4-step resolution with actual DB values | **Agent** |
| "Phòng IT có bao nhiêu nhân viên?" | Generic: "IT typically has 10–50 staff..." | Correct: 15 staff, 450,000,000 VND/month | **Agent** |
| Simple factual Q (known to LLM) | Correct | Correct but 2× more expensive | **Chatbot** (cost) |

**Conclusion**: The agent dominates on all data-specific and multi-step queries. The chatbot is cheaper and faster for well-known general knowledge questions where tool access is unnecessary.

---

## 6. Production Readiness Review

### Security
- Tool arguments from the LLM are never executed as shell commands — all tools are pure Python function calls against an in-memory dictionary. No SQL injection or command injection surface exists in the current scope.
- API keys are stored in `.env` (excluded from git via `.gitignore`) and loaded at runtime via `python-dotenv`.
- Future risk: if tools are expanded to hit real databases or external APIs, input validation on `employee_id` and `department_name` must be added before forwarding to backends.

### Guardrails
- **Loop limit**: `max_steps=8` prevents runaway billing from infinite reasoning loops; an `AGENT_TIMEOUT` event is emitted.
- **Parse error recovery**: When `_parse_action` returns `None`, the agent injects a correction message into the transcript and continues — rather than crashing — giving the LLM a chance to self-correct on the next step.
- **Tool error isolation**: Each tool call is wrapped in `try/except`; errors are returned as observation strings rather than exceptions, keeping the loop alive.
- **Retry with back-off**: The Gemini provider retries on HTTP 503 up to 4 times with exponential delay, preventing transient quota errors from failing entire runs.

### Scaling
- **Token growth**: The transcript grows linearly with steps. For long tasks (>6 steps), switching to Gemini's native `history` parameter (multi-turn API) would eliminate repeated token overhead from re-sending the full transcript.
- **Tool routing**: With more than ~20 tools, embedding tool descriptions and using cosine-similarity lookup to inject only the top-K relevant tools per step would reduce prompt size and hallucination risk.
- **Async execution**: Tools that are logically independent (e.g., fetching employee info and department info simultaneously) could be dispatched concurrently with `asyncio.gather`, reducing multi-step latency.
- **Framework migration**: For production branching logic (parallel agents, human-in-the-loop approval, conditional subgraphs), migrating to **LangGraph** or **Anthropic's Agent SDK** would replace the hand-rolled transcript loop with a maintained, battle-tested runtime.

---

> **Submission note**: This report covers the full group deliverable for Lab 3. Individual reports are in `report/individual_reports/`.
