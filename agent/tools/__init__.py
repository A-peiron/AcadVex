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
from agent.tools.author_tools import (
    find_collab_opportunities,
    get_author_influence,
    find_rising_stars,
    compare_authors,
    get_collab_strength,
    get_author_papers,
)
from agent.tools.community_tools import (
    get_community_leaders,
    get_community_topics,
    get_inter_community_strength,
)
from agent.tools.network_tools import (
    find_collab_path,
    suggest_team,
    get_network_overview,
)


# ── 工具函数注册表（名称 → 函数）────────────────────────────────────────
TOOL_REGISTRY = {
    # 原有工具
    "predict_collaboration":      predict_collaboration,
    "search_author":              search_author,
    "get_network_stats":          get_network_stats,
    "analyze_community":          analyze_community,
    "search_knowledge":           search_knowledge,
    # 个人分析工具（6 个）
    "find_collab_opportunities":  find_collab_opportunities,
    "get_author_influence":       get_author_influence,
    "find_rising_stars":          find_rising_stars,
    "compare_authors":            compare_authors,
    "get_collab_strength":        get_collab_strength,
    "get_author_papers":          get_author_papers,
    # 社群分析工具（3 个）
    "get_community_leaders":      get_community_leaders,
    "get_community_topics":       get_community_topics,
    "get_inter_community_strength": get_inter_community_strength,
    # 全局/策略工具（3 个）
    "find_collab_path":           find_collab_path,
    "suggest_team":               suggest_team,
    "get_network_overview":       get_network_overview,
}


# ── 工具 JSON Schema（发给 LLM 的格式）──────────────────────────────────
TOOL_SCHEMAS = [
    # ── 原有工具 ─────────────────────────────────────────────────────────
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

    # ── 个人分析工具（6 个）──────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "find_collab_opportunities",
            "description": (
                "为指定作者推荐最有潜力的未合作学者（高 FPGCL 分数 - 已有合作边）。"
                "返回 Top-K 候选人列表，包含相似度分数和共同关键词。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "author_id": {
                        "type": "integer",
                        "description": "作者内部 ID（0~4056）"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回候选数量，默认 10",
                        "default": 10
                    }
                },
                "required": ["author_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_author_influence",
            "description": (
                "查询指定作者的网络影响力指标：度中心性（合作活跃度）、"
                "介数中心性（桥梁作用）、紧密中心性（网络核心程度）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "author_id": {
                        "type": "integer",
                        "description": "作者内部 ID（0~4056）"
                    }
                },
                "required": ["author_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_rising_stars",
            "description": (
                "在指定社群中找出新锐学者（高 FPGCL 相似度 + 低合作度），"
                "即有潜力但尚未充分建立合作网络的作者。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "community_id": {
                        "type": "integer",
                        "description": "社群 ID（0=Database, 1=Data Mining, 2=AI, 3=Info Retrieval）"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回数量，默认 5",
                        "default": 5
                    }
                },
                "required": ["community_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_authors",
            "description": (
                "对比两位作者的相似度和研究方向。"
                "返回：FPGCL 向量相似度、关键词交集（共同方向）、关键词差集（互补方向）、中心性对比。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "author_a_id": {
                        "type": "integer",
                        "description": "作者 A 的内部 ID（0~4056）"
                    },
                    "author_b_id": {
                        "type": "integer",
                        "description": "作者 B 的内部 ID（0~4056）"
                    }
                },
                "required": ["author_a_id", "author_b_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_collab_strength",
            "description": (
                "计算两位作者之间的多因子合作强度评分（0-1）。"
                "评分因子：FPGCL 向量相似度（50%）+ 关键词 Jaccard（30%）+ 同社群加成（20%）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "author_a_id": {
                        "type": "integer",
                        "description": "作者 A 的内部 ID（0~4056）"
                    },
                    "author_b_id": {
                        "type": "integer",
                        "description": "作者 B 的内部 ID（0~4056）"
                    }
                },
                "required": ["author_a_id", "author_b_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_author_papers",
            "description": (
                "获取指定作者的论文列表，包括论文标题、发表 venue、论文数量。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "author_id": {
                        "type": "integer",
                        "description": "作者内部 ID（0~4056）"
                    }
                },
                "required": ["author_id"],
            },
        },
    },

    # ── 社群分析工具（3 个）──────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_community_leaders",
            "description": (
                "返回指定社群中影响力最高的 Top-K 学者，"
                "按综合中心性指标（度中心性×60% + 介数中心性×40%）排名。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "community_id": {
                        "type": "integer",
                        "description": "社群 ID（0=Database, 1=Data Mining, 2=AI, 3=Info Retrieval）"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回数量，默认 5",
                        "default": 5
                    }
                },
                "required": ["community_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_community_topics",
            "description": (
                "返回指定社群的核心研究主题关键词（TF-IDF 预计算，Top-20）。"
                "用于了解某个研究社群的主要研究方向。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "community_id": {
                        "type": "integer",
                        "description": "社群 ID（0=Database, 1=Data Mining, 2=AI, 3=Info Retrieval）"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回关键词数量，默认 10，最多 20",
                        "default": 10
                    }
                },
                "required": ["community_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inter_community_strength",
            "description": (
                "统计两个社群之间的跨社群合作强度：合作边数量、平均权重、最活跃合作对。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "comm_a_id": {
                        "type": "integer",
                        "description": "社群 A 的 ID（0-3）"
                    },
                    "comm_b_id": {
                        "type": "integer",
                        "description": "社群 B 的 ID（0-3）"
                    }
                },
                "required": ["comm_a_id", "comm_b_id"],
            },
        },
    },

    # ── 全局/策略工具（3 个）──────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "find_collab_path",
            "description": (
                "用 BFS 算法找出两位作者之间的最短合作路径（类似六度分隔理论）。"
                "返回路径上每位中间人的姓名，最多搜索 6 跳。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "author_a_id": {
                        "type": "integer",
                        "description": "起点作者 ID（0~4056）"
                    },
                    "author_b_id": {
                        "type": "integer",
                        "description": "终点作者 ID（0~4056）"
                    }
                },
                "required": ["author_a_id", "author_b_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_team",
            "description": (
                "根据研究方向描述，用多样性贪心算法组建互补型研究团队。"
                "优先选择关键词覆盖最广的组合。建议使用英文关键词。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "研究方向描述，如 'graph neural network recommendation system'"
                    },
                    "size": {
                        "type": "integer",
                        "description": "团队人数，默认 3，建议 2-5",
                        "default": 3
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_network_overview",
            "description": (
                "获取整体学术合作网络的深度统计信息（get_network_stats 的扩展版）。"
                "包含：网络规模、度分布统计、全网影响力 Top-5 作者、各社群规模对比。"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
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
