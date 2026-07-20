"""
多Agent架构升级测试（Supervisor路由 + 子Agent独立工具集）

测试目标：
  - 验证Supervisor路由正确识别用户意图并分发到对应子Agent
  - 验证DetectionAgent精简为4个检测工具
  - 验证QAAgent只持有search_knowledge工具（1个）
  - 验证AnalysisAgent持有3个分析工具
  - 验证SSE流式事件完整链路
  - 验证各子Agent独立工具集隔离
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.agent.analysis_agent import AnalysisAgent
from app.agent.base_agent import BaseAgent
from app.agent.detection_agent import DetectionAgent
from app.agent.graph import _build_graph, multi_agent_graph
from app.agent.multi_agent import multi_agent_chat_stream
from app.agent.nodes import should_continue
from app.agent.qa_agent import QAAgent
from app.agent.state import AgentState

# ============================================================
# 测试类1：Agent工具集验证
# ============================================================


class TestAgentTools:
    """验证各子Agent独立工具集"""

    def test_detection_agent_has_four_tools(self):
        """DetectionAgent 持有4个检测工具（不含知识库和分析工具）"""
        agent = DetectionAgent()
        tool_names = {tool.name for tool in agent.TOOLS}

        assert len(agent.TOOLS) == 4
        assert tool_names == {
            "detect_single_image",
            "detect_batch_images",
            "detect_zip_images_file",
            "detect_video_file",
        }
        assert "search_knowledge" not in tool_names
        assert "query_detection_stats" not in tool_names
        assert "query_detection_history" not in tool_names
        assert "query_user_list" not in tool_names

    def test_qa_agent_has_one_tool(self):
        """QAAgent 只持有 search_knowledge 工具（1个）"""
        agent = QAAgent()
        tool_names = {tool.name for tool in agent.TOOLS}

        assert len(agent.TOOLS) == 1
        assert tool_names == {"search_knowledge"}

    def test_analysis_agent_has_three_tools(self):
        """AnalysisAgent 持有3个分析工具（不含检测和知识库工具）"""
        agent = AnalysisAgent()
        tool_names = {tool.name for tool in agent.TOOLS}

        assert len(agent.TOOLS) == 3
        assert tool_names == {
            "query_detection_stats",
            "query_detection_history",
            "query_user_list",
        }
        assert "detect_single_image" not in tool_names
        assert "search_knowledge" not in tool_names

    def test_all_agents_inherit_from_base_agent(self):
        """所有子Agent都继承自BaseAgent"""
        assert issubclass(DetectionAgent, BaseAgent)
        assert issubclass(QAAgent, BaseAgent)
        assert issubclass(AnalysisAgent, BaseAgent)

    def test_agent_initialization_logging(self, caplog):
        """Agent初始化日志验证"""
        import logging

        caplog.set_level(logging.INFO)

        DetectionAgent()
        QAAgent()
        AnalysisAgent()

        assert "[detection] 初始化完成，绑定 4 个工具" in caplog.text
        assert "[qa] 初始化完成，绑定 1 个工具" in caplog.text
        assert "[analysis] 初始化完成，绑定 3 个工具" in caplog.text


# ============================================================
# 测试类2：状态图验证
# ============================================================


class TestGraph:
    """验证LangGraph状态图"""

    def test_build_graph_returns_state_graph(self):
        """_build_graph 返回 StateGraph 实例"""
        graph = _build_graph()
        assert graph is not None
        assert hasattr(graph, "add_node")
        assert hasattr(graph, "add_edge")

    def test_multi_agent_graph_is_compiled(self):
        """multi_agent_graph 是编译后的图"""
        assert multi_agent_graph is not None
        assert hasattr(multi_agent_graph, "invoke")
        assert hasattr(multi_agent_graph, "ainvoke")

    def test_should_continue_returns_agent_target(self):
        """should_continue 返回对应的Agent目标"""
        state = AgentState(
            messages=[],
            next_agent="detection",
            final_answer="",
            events=[],
            user_input="",
            attachment_paths=[],
            user_id=1,
            session_id="test",
            display_language="zh",
            is_admin=False,
            scene_id=None,
            max_iterations=5,
            current_iteration=1,
        )
        result = should_continue(state)
        assert result == "detection"


# ============================================================
# 测试类3：多Agent混合调度器验证
# ============================================================


class TestMultiAgent:
    """验证多Agent混合调度器"""

    def test_multi_agent_routes_detection(self):
        """检测消息路由到DetectionAgent"""
        import app.agent.multi_agent as multi_agent_module

        with patch.object(multi_agent_module, "supervisor_route") as mock_route:
            mock_route.return_value = "detection"

            with patch.object(
                multi_agent_module.detection_agent, "chat_stream"
            ) as mock_chat:
                mock_chat.return_value = AsyncMock()
                mock_chat.return_value.__aiter__.return_value = [
                    {"type": "text_chunk", "content": "检测完成"}
                ]

                async def collect():
                    events = []
                    async for event in multi_agent_chat_stream(
                        message="检测这张图片",
                        user_id=1,
                        session_id="session_1",
                    ):
                        events.append(event)
                    return events

                import asyncio

                events = asyncio.run(collect())
                assert len(events) >= 1

    def test_multi_agent_routes_qa(self):
        """问答消息路由到QAAgent"""
        import app.agent.multi_agent as multi_agent_module

        with patch.object(multi_agent_module, "supervisor_route") as mock_route:
            mock_route.return_value = "qa"

            with patch.object(multi_agent_module.qa_agent, "chat_stream") as mock_chat:
                mock_chat.return_value = AsyncMock()
                mock_chat.return_value.__aiter__.return_value = [
                    {"type": "text_chunk", "content": "知识库回答"}
                ]

                async def collect():
                    events = []
                    async for event in multi_agent_chat_stream(
                        message="什么是炭疽病",
                        user_id=1,
                        session_id="session_1",
                    ):
                        events.append(event)
                    return events

                import asyncio

                events = asyncio.run(collect())
                assert len(events) >= 1

    def test_multi_agent_routes_analysis(self):
        """分析消息路由到AnalysisAgent"""
        import app.agent.multi_agent as multi_agent_module

        with patch.object(multi_agent_module, "supervisor_route") as mock_route:
            mock_route.return_value = "analysis"

            with patch.object(
                multi_agent_module.analysis_agent, "chat_stream"
            ) as mock_chat:
                mock_chat.return_value = AsyncMock()
                mock_chat.return_value.__aiter__.return_value = [
                    {"type": "text_chunk", "content": "统计结果"}
                ]

                async def collect():
                    events = []
                    async for event in multi_agent_chat_stream(
                        message="今天检测了多少次",
                        user_id=1,
                        session_id="session_1",
                    ):
                        events.append(event)
                    return events

                import asyncio

                events = asyncio.run(collect())
                assert len(events) >= 1

    def test_multi_agent_routes_general(self):
        """通用消息直接LLM回复"""
        import app.agent.multi_agent as multi_agent_module

        with patch.object(multi_agent_module, "supervisor_route") as mock_route:
            mock_route.return_value = "general"

            with patch.object(multi_agent_module, "_general_stream") as mock_general:
                mock_general.return_value = AsyncMock()
                mock_general.return_value.__aiter__.return_value = [
                    {"type": "text_chunk", "content": "通用回复"}
                ]

                async def collect():
                    events = []
                    async for event in multi_agent_chat_stream(
                        message="你好",
                        user_id=1,
                        session_id="session_1",
                    ):
                        events.append(event)
                    return events

                import asyncio

                events = asyncio.run(collect())
                assert len(events) >= 1
                mock_general.assert_called_once()


# ============================================================
# 测试类4：SSE事件流验证
# ============================================================


class TestSSEEvents:
    """验证SSE流式事件完整链路"""

    def test_sse_event_sequence_includes_session_event(self):
        """SSE流包含session事件"""
        import app.agent.multi_agent as multi_agent_module

        with patch.object(multi_agent_module, "supervisor_route") as mock_route:
            mock_route.return_value = "general"

            with patch.object(multi_agent_module, "_general_stream") as mock_general:
                mock_general.return_value = AsyncMock()
                mock_general.return_value.__aiter__.return_value = [
                    {"type": "session", "session_id": "test_session"},
                    {"type": "thinking", "content": "正在思考..."},
                    {"type": "text_chunk", "content": "回复"},
                    {"type": "done", "full_text": "回复"},
                ]

                async def collect():
                    events = []
                    async for event in multi_agent_chat_stream(
                        message="你好",
                        user_id=1,
                        session_id="session_1",
                    ):
                        events.append(event)
                    return events

                import asyncio

                events = asyncio.run(collect())

                session_events = [e for e in events if e.get("type") == "session"]
                assert len(session_events) >= 1

    def test_sse_event_sequence_includes_thinking_event(self):
        """SSE流包含thinking事件"""
        import app.agent.multi_agent as multi_agent_module

        with patch.object(multi_agent_module, "supervisor_route") as mock_route:
            mock_route.return_value = "general"

            with patch.object(multi_agent_module, "_general_stream") as mock_general:
                mock_general.return_value = AsyncMock()
                mock_general.return_value.__aiter__.return_value = [
                    {"type": "session", "session_id": "test_session"},
                    {"type": "thinking", "content": "正在思考..."},
                    {"type": "text_chunk", "content": "回复"},
                    {"type": "done", "full_text": "回复"},
                ]

                async def collect():
                    events = []
                    async for event in multi_agent_chat_stream(
                        message="你好",
                        user_id=1,
                        session_id="session_1",
                    ):
                        events.append(event)
                    return events

                import asyncio

                events = asyncio.run(collect())

                thinking_events = [e for e in events if e.get("type") == "thinking"]
                assert len(thinking_events) >= 1


# ============================================================
# 测试类5：AgentState验证
# ============================================================


class TestAgentState:
    """验证AgentState数据结构"""

    def test_agent_state_initialization(self):
        """AgentState正常初始化"""
        state = AgentState(
            messages=[],
            next_agent="",
            final_answer="",
            events=[],
            user_input="测试",
            attachment_paths=[],
            user_id=1,
            session_id="session_1",
            display_language="zh",
            is_admin=False,
            scene_id=None,
            max_iterations=5,
            current_iteration=0,
        )
        assert state["user_input"] == "测试"
        assert state["user_id"] == 1
        assert state["session_id"] == "session_1"
        assert state["display_language"] == "zh"
        assert state["is_admin"] is False
        assert state["max_iterations"] == 5
        assert state["current_iteration"] == 0
        assert state["next_agent"] == ""
        assert state["final_answer"] == ""


# ============================================================
# 测试类6：BaseAgent基类验证
# ============================================================


class TestBaseAgent:
    """验证BaseAgent基类通用逻辑"""

    def test_base_agent_has_class_attributes(self):
        """BaseAgent 有类属性定义"""
        # 验证子类定义了必要的属性
        assert hasattr(DetectionAgent, "AGENT_NAME")
        assert hasattr(DetectionAgent, "PROMPT_KEY")
        assert hasattr(DetectionAgent, "TOOLS")

        assert hasattr(QAAgent, "AGENT_NAME")
        assert hasattr(QAAgent, "PROMPT_KEY")
        assert hasattr(QAAgent, "TOOLS")

        assert hasattr(AnalysisAgent, "AGENT_NAME")
        assert hasattr(AnalysisAgent, "PROMPT_KEY")
        assert hasattr(AnalysisAgent, "TOOLS")

    def test_subclass_has_tools_attribute(self):
        """子类有TOOLS属性"""
        agent = DetectionAgent()
        assert hasattr(agent, "TOOLS")
        assert isinstance(agent.TOOLS, list)


# ============================================================
# 测试类7：集成测试 - 完整对话流程
# ============================================================


class TestIntegration:
    """集成测试 - 完整对话流程"""

    def test_full_chat_stream_detection_flow(self):
        """完整检测对话流程"""
        import app.agent.multi_agent as multi_agent_module

        with patch.object(multi_agent_module, "supervisor_route") as mock_route:
            mock_route.return_value = "detection"

            with patch.object(
                multi_agent_module.detection_agent, "chat_stream"
            ) as mock_chat:
                mock_chat.return_value = AsyncMock()
                mock_chat.return_value.__aiter__.return_value = [
                    {"type": "session", "session_id": "test_session"},
                    {"type": "thinking", "content": "正在检测..."},
                    {"type": "tool_call", "tool": "detect_single_image"},
                    {"type": "tool_result", "result": {"total_objects": 5}},
                    {"type": "text_chunk", "content": "检测到5个目标"},
                    {"type": "done", "full_text": "检测到5个目标"},
                ]

                async def collect():
                    events = []
                    async for event in multi_agent_chat_stream(
                        message="检测这张图片",
                        user_id=1,
                        session_id="session_1",
                    ):
                        events.append(event)
                    return events

                import asyncio

                events = asyncio.run(collect())

                event_types = [e["type"] for e in events]
                assert "session" in event_types
                assert "thinking" in event_types
                assert "tool_call" in event_types
                assert "tool_result" in event_types
                assert "text_chunk" in event_types
                assert "done" in event_types

    def test_full_chat_stream_qa_flow(self):
        """完整问答对话流程"""
        import app.agent.multi_agent as multi_agent_module

        with patch.object(multi_agent_module, "supervisor_route") as mock_route:
            mock_route.return_value = "qa"

            with patch.object(multi_agent_module.qa_agent, "chat_stream") as mock_chat:
                mock_chat.return_value = AsyncMock()
                mock_chat.return_value.__aiter__.return_value = [
                    {"type": "session", "session_id": "test_session"},
                    {"type": "thinking", "content": "正在搜索知识库..."},
                    {"type": "tool_call", "tool": "search_knowledge"},
                    {"type": "tool_result", "result": {"content": "知识片段"}},
                    {"type": "text_chunk", "content": "根据知识库..."},
                    {"type": "done", "full_text": "根据知识库..."},
                ]

                async def collect():
                    events = []
                    async for event in multi_agent_chat_stream(
                        message="什么是炭疽病",
                        user_id=1,
                        session_id="session_1",
                    ):
                        events.append(event)
                    return events

                import asyncio

                events = asyncio.run(collect())

                event_types = [e["type"] for e in events]
                assert "session" in event_types
                assert "tool_call" in event_types
                assert "tool_result" in event_types
                assert "text_chunk" in event_types
                assert "done" in event_types

    def test_full_chat_stream_analysis_flow(self):
        """完整分析对话流程"""
        import app.agent.multi_agent as multi_agent_module

        with patch.object(multi_agent_module, "supervisor_route") as mock_route:
            mock_route.return_value = "analysis"

            with patch.object(
                multi_agent_module.analysis_agent, "chat_stream"
            ) as mock_chat:
                mock_chat.return_value = AsyncMock()
                mock_chat.return_value.__aiter__.return_value = [
                    {"type": "session", "session_id": "test_session"},
                    {"type": "thinking", "content": "正在统计..."},
                    {"type": "tool_call", "tool": "query_detection_stats"},
                    {"type": "tool_result", "result": {"total_tasks": 10}},
                    {"type": "text_chunk", "content": "今天检测了10次"},
                    {"type": "done", "full_text": "今天检测了10次"},
                ]

                async def collect():
                    events = []
                    async for event in multi_agent_chat_stream(
                        message="今天检测了多少次",
                        user_id=1,
                        session_id="session_1",
                    ):
                        events.append(event)
                    return events

                import asyncio

                events = asyncio.run(collect())

                event_types = [e["type"] for e in events]
                assert "session" in event_types
                assert "tool_call" in event_types
                assert "tool_result" in event_types
                assert "text_chunk" in event_types
                assert "done" in event_types

    def test_full_chat_stream_general_flow(self):
        """完整通用对话流程"""
        import app.agent.multi_agent as multi_agent_module

        with patch.object(multi_agent_module, "supervisor_route") as mock_route:
            mock_route.return_value = "general"

            with patch.object(multi_agent_module, "_general_stream") as mock_general:
                mock_general.return_value = AsyncMock()
                mock_general.return_value.__aiter__.return_value = [
                    {"type": "session", "session_id": "test_session"},
                    {"type": "thinking", "content": "正在思考..."},
                    {"type": "text_chunk", "content": "你好！"},
                    {"type": "done", "full_text": "你好！"},
                ]

                async def collect():
                    events = []
                    async for event in multi_agent_chat_stream(
                        message="你好",
                        user_id=1,
                        session_id="session_1",
                    ):
                        events.append(event)
                    return events

                import asyncio

                events = asyncio.run(collect())

                event_types = [e["type"] for e in events]
                assert "session" in event_types
                assert "thinking" in event_types
                assert "text_chunk" in event_types
                assert "done" in event_types
