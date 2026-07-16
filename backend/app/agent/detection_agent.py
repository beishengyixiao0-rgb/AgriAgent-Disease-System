"""
检测智能体（Day 11 升级版）— 多工具 Agent + 增强 SSE + 双语支持

升级内容（相比 Day 8）：
  1. Prompt 模板外置到 prompts.py（支持中英双语）
  2. 工具从 4 个扩展到 8 个（检测 4 + RAG 1 + 统计 2 + 用户 1）
  3. SSE 事件协议增强（thinking/tool_start/tool_end/done/error）
  4. 支持用户语言偏好，从数据库获取

架构：
  用户消息 → Agent（LLM + 8 工具）→ 调用工具 → SSE 流式返回
"""

import json
from typing import AsyncGenerator

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agent.prompts import (
    DETECTION_AGENT_SYSTEM_PROMPT_CN,
    DETECTION_AGENT_SYSTEM_PROMPT_EN,
)
from app.agent.tools.analysis_tool import ANALYSIS_TOOLS
from app.agent.tools.detection_tool import DETECTION_TOOLS
from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def create_llm():
    """
    根据配置创建 LLM 实例（与 Day 8 相同，此处不重复注释）
    """
    from langchain_openai import ChatOpenAI

    qwen_api_key = getattr(settings, "QWEN_API_KEY", "")
    if qwen_api_key and qwen_api_key != "sk-your-qwen-api-key":
        api_key = qwen_api_key
        base_url = getattr(
            settings, "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        model_name = getattr(settings, "QWEN_MODEL", "qwen3.7-plus")
    else:
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        base_url = getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_name = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.1,
    )


class DetectionAgent:
    """检测智能体（Day 11 升级版）"""

    def __init__(self):
        self.llm = create_llm()

        self.all_tools = DETECTION_TOOLS + ANALYSIS_TOOLS

        logger.info(
            "DetectionAgent 初始化完成，绑定 %d 个工具（检测 %d + 分析 %d）",
            len(self.all_tools),
            len(DETECTION_TOOLS),
            len(ANALYSIS_TOOLS),
        )

    async def chat_stream(
        self,
        message: str,
        user_id: int = 0,
        session_id: str = "default",
        image_path: str = None,
        language: str = "zh",
    ) -> AsyncGenerator:
        """
        流式处理对话消息（增强版 SSE）

        Args:
            message: 用户文本消息
            user_id: 用户 ID
            session_id: 会话 ID
            image_path: 附带的图片路径（可选）
            language: 用户语言偏好（zh/en）

        Yields:
            SSE 事件数据字典
        """
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        system_prompt = DETECTION_AGENT_SYSTEM_PROMPT_EN if language == "en" else DETECTION_AGENT_SYSTEM_PROMPT_CN

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.all_tools,
            prompt=prompt,
        )

        executor = AgentExecutor(
            agent=agent,
            tools=self.all_tools,
            verbose=True,
            max_iterations=8,
            return_intermediate_steps=True,
        )

        thinking_msg = "Analyzing your request..." if language == "en" else "正在分析您的请求..."
        yield {"type": "thinking", "content": thinking_msg}

        full_text = ""
        try:
            async for event in executor.astream_events(
                {"input": message, "chat_history": []},
                version="v2",
            ):
                event_kind = event["event"]

                if event_kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        full_text += chunk.content
                        yield {
                            "type": "text_chunk",
                            "content": chunk.content,
                        }

                elif event_kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    logger.info("工具调用: %s, 输入: %s", tool_name, str(tool_input)[:200])
                    yield {
                        "type": "tool_start",
                        "tool": tool_name,
                        "input": {k: str(v)[:100] for k, v in tool_input.items()},
                    }

                elif event_kind == "on_tool_end":
                    tool_data = event.get("data", {})
                    tool_output = tool_data.get("output", "")
                    tool_name = event.get("name", "")
                    summary = str(tool_output)[:100] if tool_output else ""
                    logger.info("工具完成: %s", tool_name)
                    yield {
                        "type": "tool_end",
                        "tool": tool_name,
                        "summary": summary,
                    }

        except Exception as e:
            logger.error("Agent 流式执行异常: %s", str(e), exc_info=True)
            error_msg = f"Processing error: {str(e)}" if language == "en" else f"处理出错：{str(e)}"
            yield {
                "type": "error",
                "content": error_msg,
            }

        yield {
            "type": "done",
            "full_text": full_text,
        }

    async def chat(self, message: str, image_path: str = None, language: str = "zh") -> dict:
        """非流式对话（兼容旧接口）"""
        if image_path:
            message = f"{message}\n[附件图片路径: {image_path}]"

        system_prompt = DETECTION_AGENT_SYSTEM_PROMPT_EN if language == "en" else DETECTION_AGENT_SYSTEM_PROMPT_CN

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.all_tools,
            prompt=prompt,
        )

        executor = AgentExecutor(
            agent=agent,
            tools=self.all_tools,
            verbose=True,
            max_iterations=8,
            return_intermediate_steps=True,
        )

        try:
            result = await executor.ainvoke({"input": message, "chat_history": []})
            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            logger.error("Agent 执行异常: %s", str(e), exc_info=True)
            error_msg = f"Sorry, an error occurred: {str(e)}" if language == "en" else f"抱歉，处理过程中出现错误：{str(e)}"
            return {
                "output": error_msg,
                "intermediate_steps": [],
            }


detection_agent = DetectionAgent()