"""
Wrapper hỗ trợ gọi LLM (DeepSeek hoặc Groq API) cho 2 bước:
1. run_tool_loop: Lượt router chọn tool.
2. generate_answer: Lượt sinh câu trả lời cuối từ context.
"""
import json
from typing import Callable

import config
from llm.tool_definitions import TOOLS
from llm.prompt_templates import build_router_system_prompt


def get_llm_client_and_model(provider: str = "deepseek"):
    """Khởi tạo Client & Model tùy theo provider được chọn ('deepseek' hoặc 'groq')."""
    provider = (provider or "deepseek").lower()
    if provider == "groq":
        from groq import Groq
        return Groq(api_key=config.GROQ_API_KEY), config.GROQ_MODEL
    else:
        # Mặc định: DeepSeek (dùng OpenAI-compatible SDK)
        from openai import OpenAI
        api_key = config.DEEPSEEK_API_KEY or config.GROQ_API_KEY
        base_url = config.DEEPSEEK_BASE_URL or "https://api.deepseek.com"
        model = config.DEEPSEEK_MODEL or "deepseek-chat"
        return OpenAI(api_key=api_key, base_url=base_url), model


def run_tool_loop(
    query: str,
    chat_history: list[dict],
    dispatch_fn: Callable[[str, dict], dict],
    book_language: str,
    max_rounds: int = None,
    llm_provider: str = "deepseek",
) -> tuple[dict[str, list[dict]], list[str]]:
    """Vòng lặp Tool-Calling tương thích cả DeepSeek lẫn Groq."""
    client, model_name = get_llm_client_and_model(llm_provider)
    max_rounds = max_rounds or config.MAX_TOOL_CALL_ROUNDS

    router_prompt = build_router_system_prompt(book_language)
    messages = [{"role": "system", "content": router_prompt}]
    messages += chat_history
    messages.append({"role": "user", "content": query})

    tool_results_by_name: dict[str, list[dict]] = {}
    tools_used: list[str] = []

    for _ in range(max_rounds):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0,
            )
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None) or []

            if not tool_calls:
                break

            # Ghi lại lượt assistant đã gọi tool
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            for tc in tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}

                result = dispatch_fn(name, args)
                tool_results_by_name.setdefault(name, []).append(result)
                tools_used.append(name)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        except Exception as e:
            print(f"⚠️ Lỗi Tool-calling với provider '{llm_provider}': {e}")
            break

    if not tools_used:
        # Fallback: ép dùng hybrid search
        result = dispatch_fn("hybrid_fallback_search", {"query": query})
        tool_results_by_name["hybrid_fallback_search"] = [result]
        tools_used.append("hybrid_fallback_search")

    return tool_results_by_name, tools_used


def generate_answer(
    system_prompt: str,
    user_message: str,
    chat_history: list[dict],
    llm_provider: str = "deepseek",
) -> str:
    """Sinh câu trả lời cuối từ context với LLM được chọn."""
    client, model_name = get_llm_client_and_model(llm_provider)

    messages = [{"role": "system", "content": system_prompt}]
    messages += chat_history
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.3,
    )
    return response.choices[0].message.content
