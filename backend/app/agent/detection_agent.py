"""
检测智能体（Day 11 升级版）— 多工具 Agent + 增强 SSE + 双语支持

升级内容（相比 Day 8）：
  1. Prompt 模板外置到 prompts.py（支持中英双语）
  2. 工具从 4 个扩展到 8 个（检测 4 + RAG 1 + 统计 2 + 用户 1）
  3. SSE 事件协议增强（thinking/tool_start/tool_end/done/error）
  4. 支持用户语言偏好，从数据库获取
  5. 支持对话记忆和历史记录

架构：
  用户消息 → Agent（LLM + 8 工具）→ 调用工具 → SSE 流式返回
"""

import asyncio
import contextvars
import json
from pathlib import Path
from typing import AsyncGenerator

import httpx

from app.agent.memory import conversation_memory
from app.agent.prompts import get_detection_agent_prompt
from app.agent.tools.analysis_tool import (
    ANALYSIS_TOOLS,
    reset_tool_context,
    set_tool_context,
)
from app.agent.tools.detection_tool import (
    DETECTION_TOOLS,
    detect_batch_images,
    detect_single_image,
    detect_video_file,
    detect_zip_images_file,
    reset_detection_tool_context,
    set_detection_tool_context,
)
from app.agent.tools.knowledge_tool import KNOWLEDGE_TOOLS
from app.config.settings import settings
from app.core.logger import get_logger
from app.services.chat_history_service import chat_history_service
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

logger = get_logger(__name__)

_tool_user_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "tool_user_id", default=None
)
_tool_scene_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "tool_scene_id", default=None
)
_tool_display_language: contextvars.ContextVar[str] = contextvars.ContextVar(
    "tool_display_language", default="zh"
)

# 对外保留完整工具清单，测试和后续 Agent 扩展可使用同一份定义。
ALL_TOOLS = DETECTION_TOOLS + KNOWLEDGE_TOOLS + ANALYSIS_TOOLS

VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"}


def _is_video_path(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_SUFFIXES


def create_llm():
    qwen_api_key = getattr(settings, "QWEN_API_KEY", "")
    if qwen_api_key and not qwen_api_key.startswith("sk-your-"):
        api_key = qwen_api_key
        base_url = getattr(
            settings,
            "QWEN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        model_name = getattr(settings, "QWEN_MODEL", "qwen3.7-plus")
    else:
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if not api_key or api_key.startswith("sk-your-"):
            return None
        base_url = getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_name = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    from langchain_openai import ChatOpenAI

    proxy = getattr(settings, "QWEN_PROXY", "").strip() or None
    # 与 Embedding 客户端保持一致，忽略系统继承代理，避免兼容接口连接失败。
    http_client = httpx.Client(
        proxy=proxy,
        timeout=httpx.Timeout(60.0, connect=15.0),
        trust_env=False,
    )
    http_async_client = httpx.AsyncClient(
        proxy=proxy,
        timeout=httpx.Timeout(60.0, connect=15.0),
        trust_env=False,
    )
    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.1,
        http_client=http_client,
        http_async_client=http_async_client,
    )


class DetectionAgent:
    """检测智能体（Day 11 升级版）"""

    def __init__(self):
        self.llm = create_llm()
        self.all_tools = ALL_TOOLS
        self.executor = None
        if self.llm is None:
            logger.info("未配置 LLM API Key，DetectionAgent 使用本地检测降级模式")
            return

        prompt = ChatPromptTemplate.from_messages(
            [
                # 每轮请求按用户语言注入最终提示词，而不是固定使用中文提示词。
                ("system", "{system_prompt}"),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        try:
            agent = create_openai_tools_agent(
                llm=self.llm,
                tools=self.all_tools,
                prompt=prompt,
            )
            self.executor = AgentExecutor(
                agent=agent,
                tools=self.all_tools,
                verbose=True,
                max_iterations=8,
                return_intermediate_steps=True,
            )
        except Exception as e:
            logger.error("Agent 创建失败，降级为无 LLM 模式: %s", e)
            self.executor = None

        logger.info(
            "DetectionAgent 初始化完成，绑定 %d 个工具（检测 %d + 知识 %d + 分析 %d）",
            len(self.all_tools),
            len(DETECTION_TOOLS),
            len(KNOWLEDGE_TOOLS),
            len(ANALYSIS_TOOLS),
        )

    def _attachment_message(
        self,
        message: str,
        image_path: str | None = None,
        image_paths: list[str] | None = None,
    ) -> tuple[str, list[str]]:
        attachment_paths = image_paths or ([image_path] if image_path else [])
        if len(attachment_paths) == 1:
            label = "视频" if _is_video_path(attachment_paths[0]) else "图片"
            return (
                f"{message}\n[附件{label}路径: {attachment_paths[0]}]",
                attachment_paths,
            )
        if attachment_paths:
            paths_json = json.dumps(attachment_paths, ensure_ascii=False)
            label = (
                "视频"
                if all(_is_video_path(path) for path in attachment_paths)
                else "图片"
            )
            return f"{message}\n[附件{label}路径列表: {paths_json}]", attachment_paths
        return message, attachment_paths

    @staticmethod
    def _message_for_history(message: str, attachment_paths: list[str]) -> str:
        if not attachment_paths:
            return message
        if len(attachment_paths) == 1:
            attachment_label = "视频" if _is_video_path(attachment_paths[0]) else "图片"
            return f"{message}\n[本轮已上传{attachment_label}附件]"
        return f"{message}\n[本轮已上传 {len(attachment_paths)} 个图片附件]"

    @staticmethod
    def _to_langchain_messages(history: list[dict]) -> list:
        messages = []
        for item in history:
            content = item.get("content", "")
            if not content:
                continue
            if item.get("role") in ("assistant", "ai"):
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return messages

    @staticmethod
    def _tool_output_text(tool_output) -> str:
        if isinstance(tool_output, str):
            return tool_output
        content = getattr(tool_output, "content", None)
        if isinstance(content, str):
            return content
        return str(tool_output) if tool_output is not None else ""

    @staticmethod
    def _compact_tool_results(tool_results: list[str]) -> str | None:
        if not tool_results:
            return None

        latest_detection_result = None
        fallback_results = []
        for result in tool_results:
            try:
                data = json.loads(result)
                if not isinstance(data, dict):
                    continue
                for frame in data.get("key_frames", []):
                    if data.get("annotated_video_url"):
                        frame.pop("annotated_image_base64", None)
                        frame.pop("source_image_base64", None)
                if (
                    data.get("type") == "video"
                    or "detections" in data
                    or "annotated_image_base64" in data
                    or "annotated_images" in data
                ):
                    latest_detection_result = data
                else:
                    fallback_results.append(data)
            except (json.JSONDecodeError, AttributeError):
                fallback_results.append(str(result))

        if latest_detection_result is not None:
            return json.dumps(latest_detection_result, ensure_ascii=False)
        return (
            json.dumps(fallback_results[-1], ensure_ascii=False)
            if fallback_results
            else None
        )

    @staticmethod
    def _save_history_message(
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        tool_calls: list[dict] | None = None,
        tool_result: str | None = None,
    ):
        try:
            # 数据库保存完整会话，Redis 保存短期上下文，两者均使用现有服务接口。
            chat_history_service.append_message(
                user_id,
                session_id,
                role,
                content,
                tool_calls=tool_calls,
                tool_result=tool_result,
            )
            conversation_memory.save_message(user_id, session_id, role, content)
        except Exception as e:
            logger.error("保存历史消息失败: %s", e)

    async def chat(
        self,
        message: str,
        image_path: str = None,
        image_paths: list[str] | None = None,
        user_id: int | None = None,
        is_admin: bool = False,
        display_language: str = "zh",
    ) -> dict:
        message, _ = self._attachment_message(message, image_path, image_paths)
        if display_language == "en":
            message += "\n[System instruction: Respond in English.]"

        if self.executor is None:
            return {
                "output": self._fallback_reply(message, display_language),
                "intermediate_steps": [],
            }
        # 非流式调用也必须隔离检测、统计和用户列表工具的上下文。
        detection_context_tokens = set_detection_tool_context(user_id, None, display_language)
        analysis_context_tokens = set_tool_context(user_id, is_admin)
        try:
            result = await self.executor.ainvoke(
                {
                    "input": message,
                    "response_language": display_language,
                    "system_prompt": get_detection_agent_prompt(display_language),
                }
            )
            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
            }
        except Exception as e:
            logger.error("Agent 执行异常: %s", str(e), exc_info=True)
            return {
                "output": (
                    f"An error occurred while processing your request: {str(e)}"
                    if display_language == "en"
                    else f"抱歉，处理过程中出现错误：{str(e)}"
                ),
                "intermediate_steps": [],
            }
        finally:
            reset_detection_tool_context(detection_context_tokens)
            reset_tool_context(analysis_context_tokens)

    @staticmethod
    def _fallback_reply(message: str, display_language: str = "zh") -> str:
        """未配置外部 LLM 时仍提供可操作的基础回复。"""
        if display_language == "en":
            if any(
                keyword in message.lower()
                for keyword in ("prevention", "treatment", "pesticide")
            ):
                return (
                    "Please upload a leaf image for detection first. After the disease "
                    "is identified, follow locally registered pesticide labels and "
                    "agricultural-extension guidance."
                )
            return (
                "I am a fruit and vegetable disease detection assistant. Upload one "
                "or more leaf images, a video, or a ZIP package for analysis."
            )
        if any(keyword in message for keyword in ("防治", "治疗", "用药")):
            return (
                "请先上传叶片图片完成检测。确认病害类别后，再结合当地登记农药标签、"
                "作物生育期和农技部门建议制定防治方案。"
            )
        return (
            "我是果蔬病害检测助手。你可以上传一张或多张叶片图片、视频或 ZIP 图片包，"
            "我会识别病害并返回标注结果和统计信息。"
        )

    async def chat_stream(
        self,
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
        original_message = message
        message, attachment_paths = self._attachment_message(
            original_message, image_path, image_paths
        )
        if display_language == "en":
            message += "\n[System instruction: Respond in English.]"

        persisted_user_message = self._message_for_history(
            original_message, attachment_paths
        )
        chat_history = []
        if user_id is not None and session_id:
            history = conversation_memory.load_history(user_id, session_id)
            if not history:
                history = chat_history_service.get_recent_messages(
                    user_id, session_id, conversation_memory.max_messages
                )
                if history:
                    conversation_memory.replace_history(user_id, session_id, history)
            chat_history = self._to_langchain_messages(history)
            self._save_history_message(
                user_id,
                session_id,
                "user",
                persisted_user_message,
                tool_result=json.dumps(
                    {"attachments": attachment_urls or []}, ensure_ascii=False
                ),
            )

        user_token = _tool_user_id.set(user_id)
        scene_token = _tool_scene_id.set(scene_id)
        language_token = _tool_display_language.set(display_language)
        # 工具分别持有 ContextVar，必须在 Agent 开始前同步注入请求上下文。
        detection_context_tokens = set_detection_tool_context(
            user_id, scene_id, display_language
        )
        analysis_context_tokens = set_tool_context(user_id, is_admin)
        assistant_parts: list[str] = []
        tool_calls: list[dict] = []
        tool_results: list[str] = []

        thinking_msg = (
            "Analyzing your request..."
            if display_language == "en"
            else "正在分析您的请求..."
        )
        yield {"type": "thinking", "content": thinking_msg}

        try:
            if self.executor is None:
                async for event in self._local_stream(
                    message, attachment_paths, display_language
                ):
                    if event.get("type") == "text_chunk":
                        assistant_parts.append(event.get("content", ""))
                    elif event.get("type") in {"tool_call", "tool_start"}:
                        tool_calls.append(
                            {
                                "tool": event.get("tool"),
                                "input": event.get("input", {}),
                            }
                        )
                    elif event.get("type") in {"tool_result", "tool_end"}:
                        tool_results.append(event.get("result", ""))
                    yield event
                return

            async for event in self.executor.astream_events(
                {
                    "input": message,
                    "chat_history": chat_history,
                    "response_language": display_language,
                    "system_prompt": get_detection_agent_prompt(display_language),
                },
                version="v2",
            ):
                event_kind = event["event"]

                if event_kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        assistant_parts.append(chunk.content)
                        yield {"type": "text_chunk", "content": chunk.content}

                elif event_kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    logger.info(
                        "工具调用: %s, 输入: %s", tool_name, str(tool_input)[:200]
                    )
                    tool_calls.append({"tool": tool_name, "input": tool_input})
                    yield {"type": "tool_start", "tool": tool_name, "input": tool_input}

                elif event_kind == "on_tool_end":
                    tool_data = event.get("data", {})
                    tool_output = tool_data.get("output", "")
                    tool_name = event.get("name", "")
                    logger.info(
                        "工具完成: %s, output类型=%s, output长度=%d",
                        tool_name,
                        type(tool_output).__name__,
                        len(str(tool_output)) if tool_output else 0,
                    )
                    logger.debug("on_tool_end data keys: %s", list(tool_data.keys()))
                    serialized_output = self._tool_output_text(tool_output)
                    tool_results.append(serialized_output)
                    # 返回完整工具 JSON，前端检测卡片和知识库来源均依赖该数据。
                    yield {
                        "type": "tool_end",
                        "tool": tool_name,
                        "summary": serialized_output[:100] if serialized_output else "",
                        "result": serialized_output,
                    }

        except Exception as e:
            logger.error("Agent 流式执行异常: %s", str(e), exc_info=True)
            # LLM 临时不可用时，有附件的请求仍可直接执行本地检测并返回结果卡片。
            if attachment_paths:
                async for event in self._local_stream(
                    message, attachment_paths, display_language
                ):
                    if event.get("type") == "text_chunk":
                        assistant_parts.append(event.get("content", ""))
                    elif event.get("type") in {"tool_call", "tool_start"}:
                        tool_calls.append(
                            {
                                "tool": event.get("tool"),
                                "input": event.get("input", {}),
                            }
                        )
                    elif event.get("type") in {"tool_result", "tool_end"}:
                        tool_results.append(event.get("result", ""))
                    yield event
                return
            error_message = (
                f"Processing failed: {str(e)}"
                if display_language == "en"
                else f"处理出错：{str(e)}"
            )
            assistant_parts.append(error_message)
            yield {"type": "error", "content": error_message}
        finally:
            if user_id is not None and session_id and assistant_parts:
                self._save_history_message(
                    user_id,
                    session_id,
                    "assistant",
                    "".join(assistant_parts),
                    tool_calls=tool_calls or None,
                    tool_result=self._compact_tool_results(tool_results),
                )
            _tool_user_id.reset(user_token)
            _tool_scene_id.reset(scene_token)
            _tool_display_language.reset(language_token)
            reset_detection_tool_context(detection_context_tokens)
            reset_tool_context(analysis_context_tokens)

        yield {
            "type": "done",
            "full_text": "".join(assistant_parts),
        }

    async def _local_stream(
        self, message: str, attachment_paths: list[str], display_language: str
    ):
        if not attachment_paths:
            for chunk in self._text_chunks(
                self._fallback_reply(message, display_language)
            ):
                yield {"type": "text_chunk", "content": chunk}
            return

        video_paths = [path for path in attachment_paths if _is_video_path(path)]
        if video_paths and len(attachment_paths) > 1:
            reply = (
                "Only one video can be uploaded at a time, and it cannot be mixed "
                "with images or other videos."
                if display_language == "en"
                else "一次只能上传一个视频附件，视频不能和图片或其他视频混合上传。"
            )
            for chunk in self._text_chunks(reply):
                yield {"type": "text_chunk", "content": chunk}
            return

        if len(attachment_paths) == 1 and video_paths:
            tool_function = detect_video_file
            tool_name = "detect_video_file"
            tool_input = {"video_path": attachment_paths[0]}
        elif len(attachment_paths) > 1:
            tool_function = detect_batch_images
            tool_name = "detect_batch_images"
            tool_input = {"image_paths": attachment_paths}
        elif attachment_paths[0].lower().endswith(".zip"):
            tool_function = detect_zip_images_file
            tool_name = "detect_zip_images_file"
            tool_input = {"zip_path": attachment_paths[0]}
        else:
            tool_function = detect_single_image
            tool_name = "detect_single_image"
            tool_input = {"image_path": attachment_paths[0]}

        yield {"type": "tool_start", "tool": tool_name, "input": tool_input}
        try:
            tool_output = await asyncio.to_thread(tool_function.invoke, tool_input)
        except Exception as exc:
            yield {"type": "error", "content": str(exc)}
            return

        yield {
            "type": "tool_end",
            "tool": tool_name,
            "result": tool_output,
        }
        result = json.loads(tool_output)
        if result.get("error"):
            reply = (
                f"Detection did not finish: {result['error']}"
                if display_language == "en"
                else f"检测未完成：{result['error']}"
            )
        else:
            display_counts = result.get("class_counts_display") or result.get(
                "class_counts", {}
            )
            if display_language == "en":
                summary = ", ".join(
                    f"{name}: {count}" for name, count in display_counts.items()
                )
                reply = (
                    f"Detection complete. Found {result.get('total_objects', 0)} objects"
                )
                reply += f", including {summary}" if summary else ""
                reply += ". Annotated results and detailed statistics are ready."
            else:
                summary = "、".join(
                    f"{name} {count} 个" for name, count in display_counts.items()
                )
                reply = f"检测完成，共发现 {result.get('total_objects', 0)} 个目标"
                reply += f"，包括 {summary}" if summary else ""
                reply += "。标注结果和详细统计已生成。"
        for chunk in self._text_chunks(reply):
            yield {"type": "text_chunk", "content": chunk}

    @staticmethod
    def _text_chunks(text: str, width: int = 12) -> list[str]:
        return [text[index : index + width] for index in range(0, len(text), width)]


detection_agent = DetectionAgent()
