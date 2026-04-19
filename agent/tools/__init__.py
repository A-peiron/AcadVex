"""
agent/tools/__init__.py
-----------------------
工具注册表。
- TOOL_REGISTRY：工具名 → 函数 的映射
- TOOL_SCHEMAS：工具的 OpenAI JSON Schema 定义列表
- dispatch_tool()：按名称执行工具，处理参数解析和异常
- get_openai_schemas()：返回发给 LLM 的 tools 参数
"""

import json
from agent.tools.collab_tools import (
    predict_collaboration,
    search_author,
    get_network_stats,
    analyze_community,
)
from agent.tools.rag_tools import search_knowledge



# ── 工具函数注册表（名称 → 函数）────────────────────────────────────────
TOOL_REGISTRY = {
    "predict_collaboration": predict_collaboration,
    "search_author":         search_author,
    "get_network_stats":     get_network_stats,
    "analyze_community":     analyze_community,
    "search_knowledge":      search_knowledge,
}


# ── 工具 JSON Schema（发给 LLM 的格式）──────────────────────────────────
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "predict_collaboration",
            "description": (
                "预测两位作者基于 GNN embedding 的学术合作潜力分数。"
                "分数越高表示合作可能性越大。当用户提供作者 ID 时使用此工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "author_a_id": {
                        "type": "integer",
                        "description": "第一位作者的数字 ID（0~4056）"
                    },
                    "author_b_id": {
                        "type": "integer",
                        "description": "第二位作者的数字 ID（0~4056）"
                    },
                },
                "required": ["author_a_id", "author_b_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_author",
            "description": (
                "按姓名关键词搜索作者，返回匹配的作者列表（含 ID、研究方向、论文数量）。"
                "当用户提供作者姓名而非 ID 时，先用此工具找到对应 ID。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如作者姓名或部分姓名，例如 'Tao Li' 或 'Li'"
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_network_stats",
            "description": (
                "获取学术合作网络的整体统计信息，包括作者数量、论文数量、"
                "各研究社群的规模。当用户询问网络概况时使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
        {
        "type": "function",
        "function": {
            "name": "analyze_community",
            "description": (
                "分析指定研究社群的详细信息，包括社群名称、规模和核心成员。"
                "当用户询问某个社群或研究方向的概况时使用。"
                "社群 ID 范围 0~3：0=Database, 1=Data Mining, 2=Artificial Intelligence, 3=Information Retrieval"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "community_id": {
                        "type": "integer",
                        "description": "社群 ID，范围 0~3"
                    }
                },
                "required": ["community_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": (
                "在 AcadVex 知识库中检索背景知识，包括系统介绍、模型原理、数据集说明、"
                "社群概况等。当用户询问系统架构、模型细节或领域背景知识时使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "检索关键词，如 'FPGCL 模型原理' 或 '数据挖掘社群'"
                    }
                },
                "required": ["query"],
            },
        },
    },
]


def get_openai_schemas() -> list:
    """返回完整的 tools 列表，直接传给 LLM 的 tools 参数。"""
    return TOOL_SCHEMAS


def dispatch_tool(name: str, arguments: str) -> str:
    """
    按工具名执行对应函数。

    参数：
        name      - 工具名（来自 tool_call.function.name）
        arguments - JSON 字符串（来自 tool_call.function.arguments）
    返回：
        工具执行结果的字符串，无论成功失败都返回字符串（供追加到 messages）
    """
    if name not in TOOL_REGISTRY:
        return (
            f"错误：工具 '{name}' 不存在。"
            f"可用工具：{list(TOOL_REGISTRY.keys())}"
        )

    try:
        args = json.loads(arguments)
    except json.JSONDecodeError as e:
        return f"错误：工具参数解析失败（{e}）。原始参数：{arguments}"

    try:
        result = TOOL_REGISTRY[name](**args)
        return str(result)
    except TypeError as e:
        return f"错误：工具参数不匹配（{e}）"
    except Exception as e:
        return f"错误：工具执行失败（{type(e).__name__}: {e}）"
