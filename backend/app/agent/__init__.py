"""
智能体模块。

Day 8: 单 Agent + 检测工具。
Day 11: 升级为 LangGraph 多 Agent 编排。

架构：
  - detection_agent: 单 Agent（保留，用于降级和测试）
  - multi_agent_graph: 多 Agent 状态图（Supervisor + 3 子 Agent）
  - supervisor: 路由调度器
  - nodes: 各 Agent 节点函数
  - state: 共享状态定义
"""

from app.agent.detection_agent import detection_agent
from app.agent.graph import multi_agent_graph
from app.agent.supervisor import supervisor_route
from app.agent.nodes import (
    supervisor_node,
    detection_node,
    qa_node,
    analysis_node,
    general_node,
)
from app.agent.state import AgentState

__all__ = [
    "detection_agent",
    "multi_agent_graph",
    "supervisor_route",
    "supervisor_node",
    "detection_node",
    "qa_node",
    "analysis_node",
    "general_node",
    "AgentState",
]
