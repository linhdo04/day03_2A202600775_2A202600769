"""
HR Assistant — Lab 3 Demo UI (v2)
Run: streamlit run app.py
"""

import sys
import os
import time
import json
import re
from typing import Optional, Dict, Any, List
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv(override=True)

from src.core.provider_factory import create_provider
from src.agent.agent import ReActAgent
from src.tools.hr_tools import TOOLS, _EMPLOYEES, _DEPARTMENTS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HR Assistant — Lab 3",
    page_icon="🏢",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.thought-box {
    background: #EEF4FF;
    border-left: 4px solid #4A6CF7;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    margin: 6px 0;
    font-size: 0.875em;
}
.action-box {
    background: #FFF8EC;
    border-left: 4px solid #F59E0B;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    margin: 6px 0;
    font-size: 0.875em;
    font-family: monospace;
    white-space: pre-wrap;
    word-break: break-all;
}
.obs-box {
    background: #ECFDF5;
    border-left: 4px solid #10B981;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    margin: 6px 0;
    font-size: 0.875em;
    white-space: pre-wrap;
}
.kpi-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8em;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers: ReAct loop for UI ────────────────────────────────────────────────

def _extract_thought(text: str) -> str:
    m = re.search(r"Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|$)", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""

def _extract_final_answer(text: str) -> str:
    m = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else text.strip()

def _parse_action(text: str) -> Optional[Dict]:
    """Extract Action JSON with balanced-brace matching to handle nested objects."""
    cleaned = re.sub(r"```(?:json)?|```", "", text)
    m = re.search(r"Action:\s*(\{)", cleaned)
    if not m:
        return None
    start = m.start(1)
    depth, in_str, esc = 0, False, False
    for i, c in enumerate(cleaned[start:], start):
        if esc:
            esc = False; continue
        if c == "\\" and in_str:
            esc = True; continue
        if c == '"':
            in_str = not in_str; continue
        if not in_str:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[start : i + 1])
                    except json.JSONDecodeError:
                        return None
    return None

def _execute_tool(tools: List[Dict], name: str, args: Dict) -> str:
    for t in tools:
        if t["name"] == name:
            try:
                return str(t["function"](**args))
            except TypeError as e:
                return f"[Lỗi tham số: {e}]"
            except Exception as e:
                return f"[Lỗi thực thi: {e}]"
    return f"[Lỗi: Không tìm thấy tool '{name}'. Có sẵn: {[t['name'] for t in tools]}]"


def run_agent_with_trace(llm, tools: List[Dict], user_input: str, max_steps: int = 8):
    """
    Run the ReAct loop with Streamlit live-trace.
    Returns (answer, trace_steps, total_usage, elapsed_ms).
    """
    _agent = ReActAgent(llm=llm, tools=tools, max_steps=max_steps)
    system_prompt = _agent.get_system_prompt()

    transcript = f"User: {user_input}\n\n"
    trace_steps: List[Dict] = []
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    wall_start = time.time()

    with st.status("🤔 Agent đang suy nghĩ...", expanded=True) as status:
        for step_num in range(max_steps):
            result = llm.generate(transcript, system_prompt=system_prompt)
            usage = result.get("usage", {})
            for k in total_usage:
                total_usage[k] += usage.get(k, 0)

            llm_output = result["content"].strip()

            # ── Final Answer ────────────────────────────────────────────────
            if "Final Answer:" in llm_output:
                answer = _extract_final_answer(llm_output)
                status.update(label=f"✅ Hoàn thành sau {step_num + 1} bước", state="complete")
                elapsed_ms = int((time.time() - wall_start) * 1000)
                return answer, trace_steps, total_usage, elapsed_ms

            # ── Parse Action ────────────────────────────────────────────────
            thought = _extract_thought(llm_output)
            action = _parse_action(llm_output)

            if action is None:
                observation = (
                    '[Lỗi: Không đọc được Action. '
                    'Hãy viết đúng định dạng JSON: {"tool": "<tên>", "args": {...}}]'
                )
                tool_name, tool_args = "", {}
            else:
                tool_name = action.get("tool", "")
                tool_args = action.get("args", {})
                observation = _execute_tool(tools, tool_name, tool_args)

            step_info = {
                "step": step_num + 1,
                "thought": thought,
                "tool": tool_name,
                "args": tool_args,
                "observation": observation,
            }
            trace_steps.append(step_info)

            # Live display inside st.status
            st.markdown(f"**Bước {step_num + 1}**")
            if thought:
                st.markdown(
                    f'<div class="thought-box">💭 <b>Thought:</b> {thought}</div>',
                    unsafe_allow_html=True,
                )
            if tool_name:
                args_str = json.dumps(tool_args, ensure_ascii=False, indent=2)
                st.markdown(
                    f'<div class="action-box">🔧 <b>Action:</b> {tool_name}\n{args_str}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown(
                f'<div class="obs-box">📋 <b>Observation:</b>\n{observation}</div>',
                unsafe_allow_html=True,
            )

            transcript += f"{llm_output}\nObservation: {observation}\n\n"

        status.update(label=f"⚠️ Đã hết {max_steps} bước", state="error")

    elapsed_ms = int((time.time() - wall_start) * 1000)
    return (
        f"Agent đã thực hiện {max_steps} bước nhưng chưa tìm được câu trả lời. "
        "Vui lòng thử lại với câu hỏi cụ thể hơn.",
        trace_steps,
        total_usage,
        elapsed_ms,
    )


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role, content, trace?, metrics?}]


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Cấu hình")

    mode = st.radio(
        "Chế độ",
        ["🤖 ReAct Agent", "💬 Chatbot"],
        help=(
            "**ReAct Agent** tra cứu dữ liệu thực qua tools.\n\n"
            "**Chatbot** chỉ dùng kiến thức chung của LLM."
        ),
    )
    is_agent = mode == "🤖 ReAct Agent"

    st.divider()

    # Employee directory
    with st.expander("👥 Danh sách nhân viên", expanded=False):
        for eid, emp in _EMPLOYEES.items():
            st.markdown(
                f"**{eid}** — {emp['name']}  \n"
                f"📂 {emp['department']} · 💼 {emp['position']}"
            )
            st.caption(
                f"KPI: {emp['performance_rating']} · "
                f"Phép: {emp['leave_balance']} ngày · "
                f"Thâm niên: {emp['years_of_service']} năm"
            )
            st.divider()

    # Department overview
    with st.expander("🏬 Phòng ban", expanded=False):
        for dname, dept in _DEPARTMENTS.items():
            mgr = _EMPLOYEES.get(dept["manager"], {})
            st.markdown(f"**{dname}**")
            st.caption(
                f"Trưởng phòng: {mgr.get('name', '?')}  \n"
                f"Nhân viên: {dept['headcount']} · "
                f"Ngân sách: {dept['budget_monthly']:,} VND"
            )

    st.divider()

    # Tools list
    st.markdown("**🔧 Tools (Agent):**")
    for t in TOOLS:
        st.markdown(f"- `{t['name']}`")

    st.divider()

    model_name = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
    st.caption(f"Model: `{model_name}`")

    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏢 HR Assistant — Quản lý Nhân sự")

col_badge, col_desc = st.columns([1, 4])
with col_badge:
    if is_agent:
        st.success("🤖 ReAct Agent")
    else:
        st.info("💬 Chatbot")
with col_desc:
    if is_agent:
        st.caption("Tra cứu dữ liệu thực qua tools — hiển thị từng bước suy luận")
    else:
        st.caption("Trả lời dựa trên kiến thức chung của LLM, không có tools")

# ── Last-message metrics ───────────────────────────────────────────────────────
last_metrics = next(
    (m["metrics"] for m in reversed(st.session_state.messages) if "metrics" in m),
    None,
)
if last_metrics:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tokens", last_metrics.get("total_tokens", "—"))
    c2.metric("Latency", f"{last_metrics.get('latency_ms', 0):,} ms")
    c3.metric("Bước", last_metrics.get("steps", 1))
    c4.metric("Chi phí", f"${last_metrics.get('cost_usd', 0):.5f}")

st.divider()

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Show stored agent trace as a collapsed expander
        if msg.get("trace"):
            with st.expander(f"🔍 Xem chi tiết {len(msg['trace'])} bước suy luận", expanded=False):
                for step in msg["trace"]:
                    st.markdown(f"**Bước {step['step']}**")
                    if step.get("thought"):
                        st.markdown(
                            f'<div class="thought-box">💭 <b>Thought:</b> {step["thought"]}</div>',
                            unsafe_allow_html=True,
                        )
                    if step.get("tool"):
                        args_str = json.dumps(step.get("args", {}), ensure_ascii=False, indent=2)
                        st.markdown(
                            f'<div class="action-box">🔧 <b>Action:</b> {step["tool"]}\n{args_str}</div>',
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        f'<div class="obs-box">📋 <b>Observation:</b>\n{step["observation"]}</div>',
                        unsafe_allow_html=True,
                    )


# ── Suggestion buttons (shown when chat is empty) ─────────────────────────────
SUGGESTIONS = [
    "Cho tôi biết thông tin của nhân viên EMP003.",
    "EMP003 muốn xin nghỉ 3 ngày — kiểm tra phép và duyệt đơn.",
    "Phòng IT có bao nhiêu nhân viên và ngân sách tháng?",
    "Tính lương tháng này của EMP004.",
]

user_input: Optional[str] = None

if not st.session_state.messages:
    st.markdown("**Gợi ý câu hỏi:**")
    cols = st.columns(2)
    for i, s in enumerate(SUGGESTIONS):
        if cols[i % 2].button(s, key=f"sug_{i}", use_container_width=True):
            user_input = s

# ── Chat input ────────────────────────────────────────────────────────────────
typed = st.chat_input("Nhập câu hỏi về nhân sự...")
if typed:
    user_input = typed

# ── Process user input ────────────────────────────────────────────────────────
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            llm = create_provider()

            # ── Agent mode ────────────────────────────────────────────────────
            if is_agent:
                answer, trace_steps, total_usage, elapsed_ms = run_agent_with_trace(
                    llm, TOOLS, user_input, max_steps=8
                )
                st.markdown(answer)

                total_tokens = total_usage.get("total_tokens", 0)
                metrics = {
                    "total_tokens": total_tokens,
                    "latency_ms": elapsed_ms,
                    "steps": len(trace_steps),
                    "cost_usd": (total_tokens / 1_000_000) * 0.075,
                    "mode": "agent",
                }

                if trace_steps:
                    with st.expander(f"🔍 Xem chi tiết {len(trace_steps)} bước suy luận", expanded=False):
                        for step in trace_steps:
                            st.markdown(f"**Bước {step['step']}**")
                            if step.get("thought"):
                                st.markdown(
                                    f'<div class="thought-box">💭 <b>Thought:</b> {step["thought"]}</div>',
                                    unsafe_allow_html=True,
                                )
                            if step.get("tool"):
                                args_str = json.dumps(step.get("args", {}), ensure_ascii=False, indent=2)
                                st.markdown(
                                    f'<div class="action-box">🔧 <b>Action:</b> {step["tool"]}\n{args_str}</div>',
                                    unsafe_allow_html=True,
                                )
                            st.markdown(
                                f'<div class="obs-box">📋 <b>Observation:</b>\n{step["observation"]}</div>',
                                unsafe_allow_html=True,
                            )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "trace": trace_steps,
                    "metrics": metrics,
                })

            # ── Chatbot mode (streaming) ───────────────────────────────────
            else:
                SYSTEM_PROMPT = (
                    "Bạn là trợ lý nhân sự (HR Assistant) của một công ty Việt Nam. "
                    "Trả lời ngắn gọn, rõ ràng bằng tiếng Việt. "
                    "Bạn KHÔNG có công cụ tra cứu — chỉ trả lời dựa trên kiến thức chung."
                )
                start = time.time()

                # Try streaming; fall back to non-streaming
                try:
                    chunks = list(llm.stream(user_input, system_prompt=SYSTEM_PROMPT))
                    answer = st.write_stream(iter(chunks))
                    elapsed_ms = int((time.time() - start) * 1000)
                    total_tokens = 0  # stream doesn't return token count easily
                except Exception:
                    result = llm.generate(user_input, system_prompt=SYSTEM_PROMPT)
                    answer = result["content"]
                    st.markdown(answer)
                    elapsed_ms = result["latency_ms"]
                    total_tokens = result["usage"].get("total_tokens", 0)

                metrics = {
                    "total_tokens": total_tokens or "~",
                    "latency_ms": elapsed_ms,
                    "steps": 1,
                    "cost_usd": (total_tokens / 1_000_000) * 0.075 if isinstance(total_tokens, int) else 0,
                    "mode": "chatbot",
                }
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "metrics": metrics,
                })

        except Exception as e:
            err = f"❌ Lỗi: {str(e)[:300]}"
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err})

    st.rerun()
