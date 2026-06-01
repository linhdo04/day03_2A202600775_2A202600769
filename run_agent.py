"""
ReAct Agent Runner — Lab 3 (Person A)
======================================
Usage:
  python run_agent.py          # interactive mode
  python run_agent.py test     # run predefined test cases

NOTE: This file imports TOOLS from Person B's module.
      Run only after Person B has implemented src/tools/hr_tools.py.
"""

import os
import sys
import time
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from src.core.provider_factory import create_provider
from src.agent.agent import ReActAgent
from src.telemetry.metrics import tracker

from src.tools.hr_tools import TOOLS

# Same queries as chatbot.py — run both scripts to compare results
TEST_CASES = [
    "Cho tôi biết thông tin của nhân viên EMP003.",
    (
        "Nhân viên Lê Thị Lan (EMP003) muốn xin nghỉ 3 ngày. "
        "Kiểm tra thông tin nhân viên, số ngày phép còn lại, "
        "xử lý đơn nghỉ phép và tính lương tháng này."
    ),
    "Phòng IT có bao nhiêu nhân viên và ngân sách tháng là bao nhiêu?",
]


def run_interactive():
    llm = create_provider()
    agent = ReActAgent(llm=llm, tools=TOOLS, max_steps=8)

    print("=" * 60)
    print("  HR ReAct Agent v1 (Gemini)")
    print(f"  Model : {llm.model_name}")
    print(f"  Tools : {[t['name'] for t in TOOLS] or 'None yet — waiting for Person B'}")
    print("  Gõ 'quit' để thoát")
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

        print("\n[Agent đang xử lý...]\n")
        answer = agent.run(user_input)
        print(f"\nAgent: {answer}")

    tracker.print_session_summary("Agent v1 Interactive")


def run_test_cases():
    llm = create_provider()
    agent = ReActAgent(llm=llm, tools=TOOLS, max_steps=8)

    print("=" * 60)
    print("  ReAct Agent v1 — Test Cases")
    print("=" * 60)

    for i, query in enumerate(TEST_CASES, 1):
        print(f"\n[Test {i}] {query}")
        print("-" * 40)
        answer = agent.run(query)
        print(f"\nFinal Answer:\n{answer}")
        print("=" * 60)
        time.sleep(5)

    tracker.print_session_summary("Agent v1 Test")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"
    if mode == "test":
        run_test_cases()
    else:
        run_interactive()
