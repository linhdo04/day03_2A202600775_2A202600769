import json
import re
from typing import List, Dict, Any, Optional

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class ReActAgent:
    """
    Agent v1 — ReAct (Reasoning + Acting) loop.
    Cycle: Thought -> Action -> Observation -> repeat -> Final Answer.

    Person A implements: the loop, parsing, and telemetry.
    Person B provides: the tools list passed into __init__.
    """

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 8):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps

    # ── System Prompt (v1) ────────────────────────────────────────────────────

    def get_system_prompt(self) -> str:
        tool_docs = "\n".join(
            f"  - {t['name']}: {t['description']}" for t in self.tools
        )
        tool_names = [t["name"] for t in self.tools]
        return f"""Bạn là trợ lý quản lý nhân sự (HR Assistant) thông minh của một công ty Việt Nam.
Trả lời bằng ngôn ngữ người dùng dùng (tiếng Việt hoặc tiếng Anh).

Bạn có thể sử dụng các công cụ sau:
{tool_docs}

Hãy làm theo định dạng CHÍNH XÁC sau đây ở mỗi bước:

Thought: <lý do / suy nghĩ của bạn>
Action: {{"tool": "<tên_công_cụ>", "args": {{<tham_số>}}}}

Sau khi nhận được Observation, tiếp tục với Thought tiếp theo hoặc kết luận:

Final Answer: <câu trả lời đầy đủ cho người dùng>

QUY TẮC:
1. Luôn bắt đầu bằng Thought.
2. Viết Action dưới dạng JSON thuần (không dùng markdown, không thêm ký tự thừa).
3. Tên công cụ phải là một trong: {tool_names}
4. KHÔNG tự viết "Observation:" — hệ thống sẽ cung cấp.
5. Mỗi lượt chỉ được ra một Action HOẶC một Final Answer.
6. Nếu công cụ trả về lỗi, hãy suy nghĩ và thử cách khác.
"""

    # ── Main ReAct Loop ───────────────────────────────────────────────────────

    def run(self, user_input: str) -> str:
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name,
            "max_steps": self.max_steps,
        })

        # Growing transcript fed back to the LLM each iteration
        transcript = f"User: {user_input}\n\n"
        steps = 0
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        while steps < self.max_steps:

            # 1. Generate next Thought + Action (or Final Answer)
            result = self.llm.generate(transcript, system_prompt=self.get_system_prompt())

            usage = result.get("usage", {})
            for k in total_usage:
                total_usage[k] += usage.get(k, 0)

            tracker.track_request(
                provider=result.get("provider", "google"),
                model=self.llm.model_name,
                usage=usage,
                latency_ms=result.get("latency_ms", 0),
            )

            llm_output = result["content"].strip()
            logger.log_event("AGENT_STEP", {
                "step": steps + 1,
                "output_preview": llm_output[:300],
                "latency_ms": result.get("latency_ms", 0),
            })

            # 2. Check for Final Answer
            if "Final Answer:" in llm_output:
                answer = self._extract_final_answer(llm_output)
                transcript += llm_output + "\n"
                logger.log_event("AGENT_END", {
                    "steps": steps + 1,
                    "total_tokens": total_usage["total_tokens"],
                })
                return answer

            # 3. Parse Action from LLM output
            action = self._parse_action(llm_output)
            if action is None:
                logger.log_event("PARSE_ERROR", {
                    "step": steps + 1,
                    "raw_output": llm_output,
                })
                observation = (
                    '[Lỗi hệ thống: Không đọc được Action. '
                    'Hãy viết đúng định dạng JSON: {"tool": "<tên>", "args": {...}}]'
                )
            else:
                # 4. Execute the tool
                tool_name = action.get("tool", "")
                tool_args = action.get("args", {})
                observation = self._execute_tool(tool_name, tool_args)
                logger.log_event("TOOL_CALL", {
                    "step": steps + 1,
                    "tool": tool_name,
                    "args": tool_args,
                    "observation": observation[:300],
                })

            # 5. Append Observation and continue
            transcript += f"{llm_output}\nObservation: {observation}\n\n"
            steps += 1

        # Reached max_steps without Final Answer
        logger.log_event("AGENT_TIMEOUT", {
            "steps": steps,
            "total_tokens": total_usage["total_tokens"],
        })
        return (
            f"Agent đã thực hiện {self.max_steps} bước nhưng chưa tìm được câu trả lời. "
            "Vui lòng thử lại với câu hỏi cụ thể hơn."
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_final_answer(self, text: str) -> str:
        match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else text.strip()

    def _parse_action(self, text: str) -> Optional[Dict]:
        """Extract JSON from 'Action: {...}', robust to markdown backticks."""
        cleaned = re.sub(r"```(?:json)?|```", "", text)
        match = re.search(r"Action:\s*(\{.*?\})", cleaned, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        for tool in self.tools:
            if tool["name"] == tool_name:
                try:
                    return str(tool["function"](**args))
                except TypeError as e:
                    return f"[Lỗi tham số cho '{tool_name}': {e}]"
                except Exception as e:
                    return f"[Lỗi thực thi '{tool_name}': {e}]"
        available = [t["name"] for t in self.tools]
        return f"[Lỗi: Không tìm thấy công cụ '{tool_name}'. Có sẵn: {available}]"
