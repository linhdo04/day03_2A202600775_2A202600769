# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: [Nguyễn Đức Kiên Trung]
- **Student ID**: [2A202600769]
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

### Modules đã implement

| File | Mô tả |
|------|-------|
| `chatbot.py` | Chatbot baseline — gọi Gemini trực tiếp, không có tool, dùng để so sánh với Agent |
| `src/agent/agent.py` | ReAct Agent v1 — vòng lặp Thought→Action→Observation, parse JSON action, gọi tool, log từng bước |
| `src/telemetry/metrics.py` | Nâng cấp telemetry — tính chi phí theo giá Gemini thực tế, in session summary cuối mỗi lần chạy |
| `src/core/gemini_provider.py` | Migration từ `google-generativeai` (deprecated) sang `google-genai` SDK mới, thêm retry tự động khi gặp lỗi 503 |
| `src/core/provider_factory.py` | Factory tạo Gemini provider từ `.env`, tách biệt config khỏi code |
| `run_agent.py` | Runner cho Agent — chạy interactive hoặc test cases, in session summary |

### Code Highlights

**ReAct Loop — `src/agent/agent.py` (dòng 57–137)**

Vòng lặp chính của agent:
```python
while steps < self.max_steps:
    # 1. Gọi LLM sinh ra Thought + Action (hoặc Final Answer)
    result = self.llm.generate(transcript, system_prompt=self.get_system_prompt())

    # 2. Nếu có Final Answer → trả về kết quả
    if "Final Answer:" in llm_output:
        return self._extract_final_answer(llm_output)

    # 3. Parse Action JSON → gọi tool → nhận Observation
    action = self._parse_action(llm_output)
    observation = self._execute_tool(action["tool"], action["args"])

    # 4. Gắn Observation vào transcript → LLM đọc ở vòng tiếp theo
    transcript += f"{llm_output}\nObservation: {observation}\n\n"
    steps += 1
```

**Telemetry Session Summary — `src/telemetry/metrics.py`**

Sau mỗi lần chạy test, in bảng tổng hợp dùng cho báo cáo nhóm:
```
Session Summary (4 lần gọi LLM)
  Prompt tokens    : 1,131
  Completion tokens: 211
  Tổng tokens      : 1,821
  Latency trung bình: 4,286 ms
  Chi phí ước tính : $0.000148 USD
```

### Cách code tương tác với ReAct loop

- `chatbot.py` gọi `llm.generate()` một lần duy nhất — không có vòng lặp, không có tool.
- `src/agent/agent.py` duy trì một `transcript` tăng dần, mỗi vòng lặp gắn thêm LLM output + Observation. LLM đọc toàn bộ lịch sử này để quyết định bước tiếp theo.
- `src/telemetry/metrics.py` ghi log JSON mỗi lần gọi LLM và tổng hợp ở cuối session.

---

## II. Debugging Case Study (10 Points)

### Failure 1 — Tool Hallucination (Tên tool sai)

**Mô tả vấn đề:**
Agent gọi tool `get_employee_information` thay vì `get_employee_info` đúng tên.

**Log thực tế** (`logs/2026-06-01.log`, dòng 11–12):
```json
{
  "event": "AGENT_STEP",
  "data": {
    "step": 1,
    "output_preview": "Action: {\"tool\": \"get_employee_information\", \"args\": {\"employee_id\": \"EMP003\"}}"
  }
}
{
  "event": "PARSE_ERROR",
  "data": {
    "step": 1,
    "raw_output": "Action: {\"tool\": \"get_employee_information\", \"args\": {\"employee_id\": \"EMP003\"}}"
  }
}
```

**Chẩn đoán:**
System prompt v1 chỉ liệt kê tên tool chứ không nhấn mạnh rằng phải dùng đúng tên chính xác. LLM tự sinh ra tên gần đúng (`get_employee_information`) thay vì tên thực (`get_employee_info`) — đây là hiện tượng **hallucination của tool name**.

**Giải pháp (Agent v2 — Person B):**
System prompt v2 thêm dòng nhắc rõ:
```
Tên tool phải là MỘT TRONG: ['get_employee_info', ...] — không được viết sai hoặc tự tạo tên mới.
```

---

### Failure 2 — Parse Error do Nested JSON (Bug trong Regex)

**Mô tả vấn đề:**
Agent gọi đúng tool `get_employee_info` nhưng vẫn bị PARSE_ERROR và lặp lại nhiều lần.

**Log thực tế** (`logs/2026-06-01.log`, dòng 52–68):
```json
{ "event": "AGENT_STEP", "data": { "step": 1, "output_preview": "Action: {\"tool\": \"get_employee_info\", \"args\": {\"employee_id\": \"EMP003\"}}" } }
{ "event": "PARSE_ERROR", "data": { "step": 1, ... } }
{ "event": "AGENT_STEP", "data": { "step": 2, "output_preview": "Action: {\"tool\": \"get_employee_info\", \"args\": {\"employee_id\": \"EMP003\"}}" } }
{ "event": "PARSE_ERROR", "data": { "step": 2, ... } }
{ "event": "AGENT_STEP", "data": { "step": 3, ... "Final Answer: Xin lỗi, không thể truy xuất..." } }
```

**Chẩn đoán:**
Regex dùng để parse action:
```python
match = re.search(r"Action:\s*(\{.*?\})", cleaned, re.DOTALL)
```
`.*?` là **non-greedy** — dừng tại dấu `}` đầu tiên gặp phải. Với JSON lồng nhau như `{"tool": "...", "args": {"employee_id": "EMP003"}}`, regex chỉ capture đến dấu `}` đóng của dict con (`args`), tạo ra JSON không hợp lệ → `json.loads` thất bại → PARSE_ERROR.

**Giải pháp:**
Đổi sang greedy match `.*` để capture đến dấu `}` cuối cùng:
```python
# Trước (v1 — bị lỗi):
match = re.search(r"Action:\s*(\{.*?\})", cleaned, re.DOTALL)

# Sau (đã fix):
match = re.search(r"Action:\s*(\{.*\})", cleaned, re.DOTALL)
```

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning — Khối Thought giúp gì?

Chatbot trả lời trực tiếp từ kiến thức chung của LLM. Với câu hỏi "Lê Thị Lan còn bao nhiêu ngày phép?", chatbot chỉ biết giải thích quy trình chung mà không tra cứu được số liệu thực tế.

Agent với `Thought:` buộc LLM phải **lập kế hoạch trước**: xác định cần biết thông tin gì, dùng tool nào, theo thứ tự nào. Nhờ vậy agent có thể giải quyết bài toán nhiều bước mà chatbot không thể.

### 2. Reliability — Khi nào Agent tệ hơn Chatbot?

Qua thực nghiệm, agent tệ hơn chatbot trong hai trường hợp:
- **Câu hỏi đơn giản**: Agent mất 2–4 bước và 4× token để trả lời câu hỏi mà chatbot trả lời trong 1 lượt. Latency cao hơn (~4,286ms/step so với ~4,882ms/toàn bộ chatbot).
- **Khi tools chưa đủ**: Nếu thông tin cần thiết không nằm trong tool nào, agent vẫn lặp lại vô ích trước khi thừa nhận thất bại — trong khi chatbot cho ra câu trả lời tổng quát ngay lập tức.

### 3. Observation — Feedback ảnh hưởng thế nào?

Mỗi `Observation` được gắn vào `transcript` và LLM đọc lại toàn bộ ở vòng tiếp theo. Điều này tạo ra **short-term memory** cho agent: nếu tool `check_leave_balance` trả về "còn 12 ngày", agent dùng thông tin này để quyết định duyệt đơn nghỉ 3 ngày mà không cần hỏi lại.

Tuy nhiên, transcript tăng dần cũng có nhược điểm: prompt tokens tăng theo từng bước, dẫn đến chi phí cao hơn trong các tác vụ nhiều bước.

---

## IV. Future Improvements (5 Points)

### Scalability
Thay vì truyền toàn bộ transcript vào mỗi lần gọi LLM, dùng **multi-turn conversation API** (Gemini hỗ trợ `history` parameter) để giảm token trùng lặp. Với nhiều tool (>20), dùng **vector search** để chỉ đưa vào prompt những tool liên quan nhất thay vì toàn bộ danh sách.

### Safety
Thêm **Supervisor LLM** — một LLM thứ hai đánh giá action trước khi thực thi, phát hiện các hành động bất thường (ví dụ: xóa dữ liệu nhân viên, duyệt nghỉ phép vượt hạn mức). Thêm **max_cost_usd** để tự dừng nếu chi phí vượt ngưỡng.

### Performance
Implement **tool result caching**: nếu cùng một tool với cùng tham số đã được gọi trong session, trả về kết quả cache thay vì gọi lại. Thêm **async tool execution** cho các tool độc lập để chạy song song, giảm latency.
