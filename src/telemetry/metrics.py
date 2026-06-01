from typing import Dict, Any, List
from src.telemetry.logger import logger

# Gemini 1.5 Flash pricing (USD / 1M tokens, 2025)
_PRICE_PER_M_INPUT = 0.075
_PRICE_PER_M_OUTPUT = 0.30


class PerformanceTracker:
    """
    Tracks token usage, latency, and estimated cost for every LLM call.
    Provides a session summary for comparing Chatbot vs Agent.
    """

    def __init__(self):
        self.session_metrics: List[Dict[str, Any]] = []

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        """Log one LLM call to the session and to the structured log file."""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency_ms": latency_ms,
            "cost_usd": self._calculate_cost(prompt_tokens, completion_tokens),
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost using Gemini 1.5 Flash pricing."""
        input_cost = (prompt_tokens / 1_000_000) * _PRICE_PER_M_INPUT
        output_cost = (completion_tokens / 1_000_000) * _PRICE_PER_M_OUTPUT
        return round(input_cost + output_cost, 6)

    def print_session_summary(self, label: str = "Session"):
        """
        Print aggregate metrics for the current session.
        Call this after a test run to get data for the group report.
        """
        if not self.session_metrics:
            print(f"[{label}] Chưa có metric nào được ghi lại.")
            return

        calls = len(self.session_metrics)
        total_prompt = sum(m["prompt_tokens"] for m in self.session_metrics)
        total_completion = sum(m["completion_tokens"] for m in self.session_metrics)
        total_tokens = sum(m["total_tokens"] for m in self.session_metrics)
        total_latency = sum(m["latency_ms"] for m in self.session_metrics)
        total_cost = sum(m["cost_usd"] for m in self.session_metrics)
        avg_latency = total_latency / calls

        print(f"\n{'=' * 50}")
        print(f"  {label} — Tổng kết ({calls} lần gọi LLM)")
        print(f"{'=' * 50}")
        print(f"  Prompt tokens    : {total_prompt:,}")
        print(f"  Completion tokens: {total_completion:,}")
        print(f"  Tổng tokens      : {total_tokens:,}")
        print(f"  Latency trung bình: {avg_latency:.0f} ms")
        print(f"  Tổng thời gian   : {total_latency:,} ms")
        print(f"  Chi phí ước tính : ${total_cost:.6f} USD")
        print(f"{'=' * 50}\n")

        logger.log_event("SESSION_SUMMARY", {
            "label": label,
            "llm_calls": calls,
            "total_tokens": total_tokens,
            "avg_latency_ms": round(avg_latency, 1),
            "total_cost_usd": total_cost,
        })


# Global tracker instance — imported by chatbot.py, agent.py, run_agent.py
tracker = PerformanceTracker()
