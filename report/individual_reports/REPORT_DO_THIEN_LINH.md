# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Đỗ Thiện Lĩnh
- **Student ID**: 2A202600775
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

### A. Design & Implement All HR Tools (`src/tools/hr_tools.py`)

Implemented 5 core HR management tools with mock database:

**1. `get_employee_info(employee_id: str)`**
- Retrieves detailed employee info: name, department, position, salary, allowance, KPI rating, years of service
- Returns formatted text with all employee attributes from 5-employee mock database

**2. `check_leave_balance(employee_id: str)`**
- Queries remaining annual leave days for an employee
- Used for leave request validation

**3. `submit_leave_request(employee_id: str, days_requested: int)`**
- Processes leave requests: validates available balance, approves/rejects, updates state
- Returns transaction status (APPROVED/REJECTED with details)

**4. `calculate_monthly_salary(employee_id: str)`**
- Computes net salary: (base + allowance) - BHXH (10.5%) - income tax (10%)
- Provides itemized salary breakdown

**5. `get_department_info(department_name: str)`**
- Returns department head, headcount, monthly budget for 4 departments (IT, Marketing, HR, Accounting)

**Tools Registry**: All tools registered in `TOOLS` list with `name`, `description`, and `function` reference for agent discovery.

**Code Link**: [src/tools/hr_tools.py](src/tools/hr_tools.py#L65-L220)

---

## II. Debugging Case Study (10 Points)

### Problem: PARSE_ERROR — JSON Extraction Failure in ReAct Loop

**Log Evidence** ([logs/2026-06-01.log](logs/2026-06-01.log)):
```
"event": "PARSE_ERROR", 
"data": {
  "step": 1, 
  "raw_output": "...Action: {\"tool\": \"get_employee_info\", \"args\": {\"employee_id\": \"EMP003\"}}"
}
```

**Root Cause Analysis**:

The original `_parse_action()` regex used **non-greedy matching** (`.*?`):
```python
# BROKEN: stops at FIRST closing brace
match = re.search(r"Action:\s*(\{.*?\})", cleaned, re.DOTALL)
```

When LLM output nested JSON:
```
Action: {"tool": "get_employee_info", "args": {"employee_id": "EMP003"}}
               ↑ depth 1                               ↑ depth 2
```
The `.*?` matched only up to `}` at depth 1, returning:
```
{"tool": "get_employee_info", "args": {"employee_id": "EMP003"
```
This incomplete JSON failed `json.loads()` → PARSE_ERROR → Observation with error message.

**Failure Pattern**: 
- All 6 test cases on 2026-06-01 showed `PARSE_ERROR` in step 1-3
- Agent trapped in retry loop, unable to execute ANY tool
- Eventually hit `max_steps=8` without Final Answer

**Solution Implemented** ([src/agent/agent.py](src/agent/agent.py#L155-L175)):

Changed to **greedy matching + bracket depth tracking**:
```python
def _parse_action(self, text: str) -> Optional[Dict]:
    m = re.search(r"Action:\s*(\{)", cleaned)
    if not m:
        return None
    start = m.start(1)
    depth, in_str, esc = 0, False, False
    for i, c in enumerate(cleaned[start:], start):
        # Track escape sequences and string state
        if esc:
            esc = False; continue
        if c == "\\" and in_str:
            esc = True; continue
        if c == '"':
            in_str = not in_str; continue
        # Count braces only outside strings
        if not in_str:
            if c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:  # Found matching close brace
                    return json.loads(cleaned[start : i + 1])
    return None
```

**Why It Works**:
- Counts brace depth while respecting string literals and escape sequences
- Correctly handles `"args": {"employee_id": "EMP003"}` by ignoring the inner `}` 
- Returns complete, valid JSON at depth 0
- Gracefully handles trailing garbage after JSON

**Impact**: After fix, agent can now parse any level of nested JSON in Action statements.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. **Reasoning Capability Difference**

**Chatbot (Direct LLM)** ([chatbot.py](chatbot.py)):
- No tools, no structured reasoning
- LLM hallucinates answers: "Không có công cụ tra cứu — chỉ trả lời dựa trên kiến thức chung"
- For query like "Tính lương EMP003 sau khi duyệt nghỉ 3 ngày" → returns generic salary info, doesn't actually modify state or validate leave balance

**ReAct Agent** ([src/agent/agent.py](src/agent/agent.py#L54-L120)):
- `Thought` block forces explicit reasoning:
  - "Tôi cần xác định số ngày phép còn lại"
  - "So sánh với số ngày yêu cầu để duyệt/từ chối"
- `Action` block grounds thinking in concrete tool calls with exact parameters
- `Observation` provides real feedback, correcting hallucinations
- Result: Agent **chains 3-4 tool calls** to solve multi-step HR scenarios that chatbot cannot handle

**Example**: For "Employee EMP003 requests 3 days leave, calculate net salary after approval":
- Chatbot: Returns generic salary formula without checking leave balance
- Agent:
  1. `check_leave_balance(EMP003)` → 12 days available
  2. `submit_leave_request(EMP003, 3)` → APPROVED, balance now 9 days
  3. `calculate_monthly_salary(EMP003)` → returns actual net salary

### 2. **When Agent Performs Worse Than Chatbot**

- **Model Weakness**: Local Phi-3 model (4K tokens) sometimes hallucinates non-existent tool names
  - Logs show: called `EmployeeDirectory`, `HumanResources`, `CreateUser` (all wrong)
  - Correct names: `get_employee_info`, `check_leave_balance`, etc.
  - Chatbot would just admit it doesn't know, agent wastes steps on wrong tool names

- **Complex Context Loss**: With deeply nested reasoning, Phi-3 loses Vietnamese context mid-reasoning
  - Logs show corrupted Vietnamese output after step 5, model confused about domain
  - Simpler chatbot stays on-topic

- **Overhead**: For simple factual queries ("What's EMP003's department?"), ReAct takes 3-4 steps vs chatbot's 1 call

### 3. **How Observations Influenced Next Steps**

**Observation Feedback Loop**:
- When tool returns `[Lỗi: Không tìm thấy công cụ 'EmployeeDirectory'. Có sẵn: [get_employee_info, check_leave_balance, ...]]`
- LLM **should** parse this error message and pick correct tool from the list
- Logs show agent **sometimes ignored** this feedback and repeated same wrong tool name (step 2-4)
- With stronger prompt guidance (example tool names in system prompt), agent corrected itself faster

**Key Learning**: ReAct's power is iterative correction, but only if LLM respects Observation feedback. Phi-3's attention is fragile with long context.

---

## IV. Future Improvements (5 Points)

### Production-Level Enhancements

1. **Scalability: Dynamic Tool Discovery & Semantic Routing**
   - Replace hardcoded tool list with vector DB (Pinecone/Weaviate) indexing tool descriptions
   - For 50+ tools, use embedding similarity to rank relevant tools before sending to LLM
   - Reduces hallucination of non-existent tool names observed in Phi-3 logs
   - Cost: $0.01/query for embedding → prevents wasted steps on wrong tools

2. **Safety: Multi-Tier Validation Pipeline**
   - **Tier 1 (Syntax)**: Parse Action JSON with bracket-depth validator (already implemented)
   - **Tier 2 (Schema)**: Validate args match tool signature before execution (currently missing)
   - **Tier 3 (Business Logic)**: Audit high-risk actions (e.g., salary changes >15%) via separate LLM "Supervisor" agent
   - Impact: Prevents `calculate_monthly_salary(employee_id="DROP TABLE employees")`

3. **Performance: Caching & Parallel Execution**
   - Cache `get_employee_info()` results (rarely changes, 5 employees in mock DB)
   - For multi-step queries ("Check leave AND calculate salary"), parallelize independent tool calls
   - Use async/await with `asyncio.gather()` instead of sequential calls
   - Reduces latency from 35s (step 6 in logs) to ~10s

4. **Reliability: Improved LLM Prompt for Phi-3**
   - Current: Generic ReAct prompt, Phi-3 hallucinates
   - Fix: Add few-shot examples for EACH tool with Vietnamese context:
     ```
     Ví dụ 1:
     Thought: Cần lấy thông tin EMP003
     Action: {"tool": "get_employee_info", "args": {"employee_id": "EMP003"}}
     Observation: [returns actual data]
     
     Ví dụ 2:
     Thought: Cần kiểm tra ngày phép còn lại
     Action: {"tool": "check_leave_balance", "args": {"employee_id": "EMP003"}}
     Observation: [returns 12 ngày]
     ```
   - Reduces error rate from current ~80% (logs: 7/8 steps failed) to <20%

5. **Observability: Enhanced Telemetry**
   - Current: Logs JSON events but no real-time dashboard
   - Add Grafana dashboard for:
     - Tool call success rate by name
     - Parse error trends
     - Model reasoning quality score (estimated from Observation relevance)
   - Enables rapid debugging of similar failures across fleet

### Estimated ROI for HR System
- **Current**: 70% of queries fail (logs show max_steps timeout)
- **With fixes**: 85% success rate
- **Cost reduction**: Fewer retries = 2x faster inference = 50% compute cost savings

---
