"""
Chatbot Baseline — Lab 3 (Person A)
=====================================
A plain LLM chatbot with NO tools and NO reasoning loop.
Demonstrates limitations on multi-step HR queries.
Compare output against run_agent.py to see the difference.

Usage:
  python chatbot.py            # interactive mode
  python chatbot.py test       # run predefined test cases
"""

import os
import sys
import time
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from src.core.provider_factory import create_provider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

SYSTEM_PROMPT = """Bạn là trợ lý nhân sự (HR Assistant) của một công ty Việt Nam.
Hãy trả lời các câu hỏi về nhân viên, nghỉ phép và lương.
Trả lời ngắn gọn, rõ ràng bằng tiếng Việt.
Lưu ý: Bạn KHÔNG có công cụ tra cứu — chỉ trả lời dựa trên kiến thức chung."""

# Same queries used in run_agent.py — for side-by-side comparison
TEST_CASES = [
    "Cho tôi biết thông tin của nhân viên EMP003.",
    (
        "Nhân viên Lê Thị Lan (EMP003) muốn xin nghỉ 3 ngày. "
        "Kiểm tra số ngày phép còn lại và tính lương tháng này sau khi duyệt nghỉ phép."
    ),
    "Phòng IT có bao nhiêu nhân viên và ngân sách tháng là bao nhiêu?",
]


def run_interactive():
    llm = create_provider()
    print("=" * 60)
    print("  HR Chatbot Baseline (Gemini) — gõ 'quit' để thoát")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nBạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        result = llm.generate(user_input, system_prompt=SYSTEM_PROMPT)
        tracker.track_request("google", llm.model_name, result["usage"], result["latency_ms"])
        logger.log_event("CHATBOT_RESPONSE", {
            "input": user_input,
            "latency_ms": result["latency_ms"],
            "total_tokens": result["usage"].get("total_tokens", 0),
        })
        print(f"\nChatbot: {result['content']}")
        print(f"  [Tokens: {result['usage'].get('total_tokens', '?')} | Latency: {result['latency_ms']}ms]")


def run_test_cases():
    llm = create_provider()
    print("=" * 60)
    print("  Chatbot Baseline — Test Cases")
    print("=" * 60)

    for i, query in enumerate(TEST_CASES, 1):
        print(f"\n[Test {i}] {query}")
        print("-" * 40)
        result = llm.generate(query, system_prompt=SYSTEM_PROMPT)
        tracker.track_request("google", llm.model_name, result["usage"], result["latency_ms"])
        logger.log_event("CHATBOT_TEST", {
            "test": i,
            "input": query,
            "latency_ms": result["latency_ms"],
            "total_tokens": result["usage"].get("total_tokens", 0),
        })
        print(f"Chatbot: {result['content']}")
        print(f"  [Tokens: {result['usage'].get('total_tokens', '?')} | Latency: {result['latency_ms']}ms]")
        time.sleep(3)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"
    if mode == "test":
        run_test_cases()
    else:
        run_interactive()
