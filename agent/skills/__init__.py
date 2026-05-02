# agent/skills/__init__.py
from agent.skills.collab      import SKILL as COLLAB_SKILL
from agent.skills.community   import SKILL as COMMUNITY_SKILL
from agent.skills.general     import SKILL as GENERAL_SKILL
from agent.skills.collab_search      import SKILL as COLLAB_SEARCH_SKILL
from agent.skills.author_analysis    import SKILL as AUTHOR_ANALYSIS_SKILL
from agent.skills.research_landscape import SKILL as RESEARCH_LANDSCAPE_SKILL
from agent.skills.team_formation     import SKILL as TEAM_FORMATION_SKILL
from agent.tools import get_openai_schemas

SKILL_REGISTRY: dict[str, dict] = {
    "collab":             COLLAB_SKILL,
    "community":          COMMUNITY_SKILL,
    "general":            GENERAL_SKILL,
    "collab_search":      COLLAB_SEARCH_SKILL,
    "author_analysis":    AUTHOR_ANALYSIS_SKILL,
    "research_landscape": RESEARCH_LANDSCAPE_SKILL,
    "team_formation":     TEAM_FORMATION_SKILL,
}

# ── 意图路由（关键词匹配，按优先级排序）────────────────────────────────────

_SKILL_KEYWORDS: list[tuple[str, list[str]]] = [
    # 精确 Skill 优先，general 兜底放最后
    ("team_formation",     ["组队", "团队", "组建", "搭档", "合作团队", "研究团队", "路径", "六度", "怎么认识"]),
    ("author_analysis",    ["影响力", "地位", "新锐", "排名", "对比", "比较", "中心性", "潜力学者"]),
    ("research_landscape", ["全局", "整体", "概览", "趋势", "统计", "网络规模", "研究主题", "社群主题", "跨社群"]),
    ("collab_search",      ["找学者", "搜索", "谁研究", "查找", "推荐合作者", "潜力合作者", "候选人"]),
    ("community",          ["社群", "community", "社区", "研究方向", "核心成员", "分析社群"]),
    ("collab",             ["合作", "collab", "合作潜力", "合作概率", "协作", "预测"]),
]


def route_skill(message: str) -> str:
    """根据用户消息关键词返回最匹配的 Skill 名称。"""
    msg = message.lower()
    best_skill = "general"
    best_score = 0

    for skill_name, keywords in _SKILL_KEYWORDS:
        score = sum(1 for kw in keywords if kw in msg)
        if score > best_score:
            best_score = score
            best_skill = skill_name

    return best_skill


# ── 获取 Skill 的工具 schema 子集 ────────────────────────────────────────

def get_skill_tools(skill_name: str) -> list:
    """只返回该 Skill 允许的工具 schema，节省 token。"""
    skill = SKILL_REGISTRY.get(skill_name, GENERAL_SKILL)
    allowed = set(skill["allowed_tools"])
    return [s for s in get_openai_schemas() if s["function"]["name"] in allowed]


def get_skill_prompt(skill_name: str) -> str:
    """返回该 Skill 专属的 system prompt。"""
    skill = SKILL_REGISTRY.get(skill_name, GENERAL_SKILL)
    return skill["system_prompt"]
