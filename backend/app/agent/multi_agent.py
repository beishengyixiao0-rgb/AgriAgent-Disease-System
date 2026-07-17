"""
多 Agent 混合调度器 — Supervisor 路由 + 现有 SSE 流式引擎

设计思路：
  - LangGraph 的 ainvoke 是阻塞调用，不适合 SSE 流式输出
  - 采用混合方案：Supervisor 先路由 → 再调用现有的 chat_stream
  - 完全保留现有 SSE 事件协议（thinking/tool_call/tool_result/text_chunk/done）
  - 前端无需任何修改

流程：
  用户消息 → Supervisor 路由 → 选择子 Agent → 调用 chat_stream → SSE 流式返回

阶段一（当前）：
  - Supervisor 负责意图分类
  - detection/qa/analysis 路由 → 复用现有 detection_agent.chat_stream()
  - general 路由 → 直接 LLM 回复（不调用工具）

阶段二（未来）：
  - 每个子 Agent 拥有独立的工具集
  - 真正的 LangGraph 状态图编排
"""

from typing import AsyncGenerator

from app.agent.detection_agent import detection_agent, create_llm
from app.agent.prompts import get_multi_agent_prompt
from app.agent.supervisor import supervisor_route
from app.core.logger import get_logger

logger = get_logger(__name__)


async def multi_agent_chat_stream(
    message: str,
    image_path: str = None,
    image_paths: list[str] | None = None,
    user_id: int | None = None,
    scene_id: int | None = None,
    session_id: str | None = None,
    display_language: str = "zh",
    attachment_urls: list[str] | None = None,
    is_admin: bool = False,
) -> AsyncGenerator:
    """
    多 Agent 流式对话入口。

    1. Supervisor 分析用户意图，决定路由
    2. 根据路由选择处理方式：
       - detection/qa/analysis → 复用现有 detection_agent.chat_stream()
       - general → 直接 LLM 回复（不调用工具）
    3. 完全保留现有 SSE 事件协议，前端无需修改
    """
    # ── 第 1 步：Supervisor 路由 ──
    route = await supervisor_route(message, display_language)
    logger.info("多 Agent 路由: %s -> %s", message[:50], route)

    # ── 第 2 步：根据路由分发 ──
    if route == "general":
        # 通用对话：直接 LLM 回复，不走工具
        async for event in _general_stream(
            message, display_language, user_id, session_id
        ):
            yield event
    else:
        # 检测/问答/分析：复用现有 detection_agent.chat_stream()
        # 现有 Agent 已绑定所有工具，能正确处理各类请求
        async for event in detection_agent.chat_stream(
            message=message,
            image_path=image_path,
            image_paths=image_paths,
            user_id=user_id,
            scene_id=scene_id,
            session_id=session_id,
            display_language=display_language,
            attachment_urls=attachment_urls,
            is_admin=is_admin,
        ):
            yield event


async def _general_stream(
    message: str,
    display_language: str,
    user_id: int | None,
    session_id: str | None,
) -> AsyncGenerator:
    """通用对话流式输出（不调用工具，直接 LLM 回复）。"""
    system_prompt = get_multi_agent_prompt("general", display_language)

    assistant_parts: list[str] = []

    try:
        llm = create_llm()
        async for chunk in llm.astream([
            ("system", system_prompt),
            ("human", message),
        ]):
            if hasattr(chunk, "content") and chunk.content:
                assistant_parts.append(chunk.content)
                yield {"type": "text_chunk", "content": chunk.content}
    except Exception as e:
        logger.error("General 流式回复失败: %s", str(e))
        error_msg = (
            f"回复失败：{str(e)}"
            if display_language == "zh"
            else f"Reply failed: {str(e)}"
        )
        yield {"type": "error", "content": error_msg}
        return

    # 保存历史消息（与 detection_agent.chat_stream 保持一致）
    if user_id is not None and session_id and assistant_parts:
        try:
            from app.agent.memory import conversation_memory
            from app.services.chat_history_service import chat_history_service

            chat_history_service.append_message(
                user_id, session_id, "assistant", "".join(assistant_parts)
            )
            conversation_memory.save_message(
                user_id, session_id, "assistant", "".join(assistant_parts)
            )
        except Exception as e:
            logger.error("保存历史消息失败: %s", e)

    yield {"type": "done", "full_text": "".join(assistant_parts)}
