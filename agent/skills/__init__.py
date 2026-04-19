# agent/skills/__init__.py
from agent.skills.collab    import SKILL as COLLAB_SKILL
from agent.skills.community import SKILL as COMMUNITY_SKILL
from agent.skills.general   import SKILL as GENERAL_SKILL
from agent.tools import get_openai_schemas

SKILL_REGISTRY: dict[str, dict] = {
    "collab":    COLLAB_SKILL,
    "community": COMMUNITY_SKILL,
    "general":   GENERAL_SKILL,
}

# ── 意图路由（关键词匹配）────────────────────────────────────────────────

_COLLAB_KEYWORDS    = ["合作", "collab", "合作潜力", "合作概率", "协作", "预测"]
_COMMUNITY_KEYWORDS = ["社群", "community", "社区", "研究方向", "核心成员", "分析社群"]

def route_skill(message: str) -> str:
    """根据用户消息关键词返回 Skill 名称。"""
    msg = message.lower()
    for kw in _COLLAB_KEYWORDS:
        if kw in msg:
            return "collab"
    for kw in _COMMUNITY_KEYWORDS:
        if kw in msg:
            return "community"
    return "general"

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
