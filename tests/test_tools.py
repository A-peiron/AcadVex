# tests/test_tools.py
"""
L1-A 单元测试：工具函数正确性（直接调用真实实现，依赖真实数据文件）
运行方式：conda run -n acadvex pytest tests/test_tools.py -v --tb=short
"""
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tools.collab_tools import predict_collaboration, search_author, get_network_stats, analyze_community
from agent.tools.author_tools import find_collab_opportunities, get_author_influence, compare_authors, get_collab_strength, get_author_papers
from agent.tools.network_tools import find_collab_path, suggest_team, get_network_overview
from agent.tools.community_tools import get_community_leaders, get_community_topics, get_inter_community_strength
from agent.tools import dispatch_tool


# ─── predict_collaboration ────────────────────────────────────────────────────

class TestPredictCollaboration:
    def test_normal_returns_score(self):
        result = predict_collaboration(42, 88)
        assert isinstance(result, str) and len(result) > 0
        assert "工具执行失败" not in result
        # 应包含数字分数
        import re
        assert re.search(r'\d+\.\d+', result), f"应包含数字分数: {result[:100]}"

    def test_self_comparison(self):
        result = predict_collaboration(42, 42)
        assert isinstance(result, str)
        # 不崩溃即可

    def test_nonexistent_author(self):
        result = predict_collaboration(999999, 42)
        assert isinstance(result, str)
        assert "错误" in result or "工具执行失败" in result, f"应返回错误提示: {result[:100]}"

    def test_negative_id(self):
        result = predict_collaboration(-1, 42)
        assert isinstance(result, str)
        assert "错误" in result or "工具执行失败" in result


# ─── search_author ────────────────────────────────────────────────────────────

class TestSearchAuthor:
    def test_exact_match(self):
        result = search_author("Jiawei Han")
        assert isinstance(result, str)
        assert "Jiawei" in result or "Han" in result, f"精确搜索应找到结果: {result[:100]}"

    def test_partial_match(self):
        result = search_author("Han")
        assert isinstance(result, str)
        assert "未找到" not in result, "部分匹配应有结果"

    def test_case_insensitive(self):
        r1 = search_author("jiawei han")
        r2 = search_author("JIAWEI HAN")
        assert isinstance(r1, str) and isinstance(r2, str)

    def test_not_found(self):
        result = search_author("ZZZZNOTEXIST_XYZ_12345")
        assert isinstance(result, str)
        assert "未找到" in result, f"无结果应提示未找到: {result[:100]}"

    def test_empty_query(self):
        result = search_author("")
        assert isinstance(result, str)  # 不崩溃

    def test_special_chars(self):
        result = search_author("Han; DROP TABLE")
        assert isinstance(result, str)  # 安全处理，不崩溃


# ─── get_network_stats ────────────────────────────────────────────────────────

class TestNetworkStats:
    def test_author_count(self):
        result = get_network_stats()
        assert "4057" in result, f"应包含4057位作者: {result[:200]}"

    def test_paper_count(self):
        result = get_network_stats()
        assert "14328" in result, f"应包含14328篇论文: {result[:200]}"

    def test_communities_present(self):
        result = get_network_stats()
        assert any(c in result for c in ["Database", "Data Mining", "AI", "Information"]), \
            f"应包含社群信息: {result[:200]}"

    def test_network_overview(self):
        result = get_network_overview()
        assert "4057" in result or "4,057" in result, f"overview应包含作者数: {result[:200]}"
        assert "工具执行失败" not in result


# ─── analyze_community ────────────────────────────────────────────────────────

class TestAnalyzeCommunity:
    @pytest.mark.parametrize("cid", [0, 1, 2, 3])
    def test_valid_community(self, cid):
        result = analyze_community(cid)
        assert isinstance(result, str)
        assert "错误" not in result and "工具执行失败" not in result, \
            f"社群{cid}应正常返回: {result[:100]}"

    def test_invalid_community(self):
        result = analyze_community(99)
        assert "错误" in result, f"无效社群应返回错误: {result[:100]}"

    def test_negative_community(self):
        result = analyze_community(-1)
        assert "错误" in result, f"负数社群ID应返回错误: {result[:100]}"


# ─── get_author_influence ─────────────────────────────────────────────────────

class TestGetAuthorInfluence:
    def test_normal(self):
        result = get_author_influence(42)
        assert isinstance(result, str)
        assert "错误" not in result and "工具执行失败" not in result
        assert "Degree" in result or "degree" in result or "度中心性" in result, \
            f"应包含中心性指标: {result[:200]}"

    def test_contains_three_metrics(self):
        result = get_author_influence(42)
        assert "Degree" in result or "度中心性" in result
        assert "Betweenness" in result or "介数" in result
        assert "Closeness" in result or "紧密" in result

    def test_nonexistent_author(self):
        result = get_author_influence(999999)
        assert "错误" in result, f"不存在的作者应返回错误: {result[:100]}"


# ─── find_collab_path ─────────────────────────────────────────────────────────

class TestFindCollabPath:
    def test_normal(self):
        result = find_collab_path(42, 88)
        assert isinstance(result, str) and len(result) > 0
        assert "工具执行失败" not in result

    def test_same_author(self):
        result = find_collab_path(42, 42)
        assert isinstance(result, str)
        assert "错误" in result, "相同作者应返回错误提示"

    def test_nonexistent_author(self):
        result = find_collab_path(42, 999999)
        assert isinstance(result, str)
        assert "错误" in result or "不存在" in result


# ─── suggest_team ─────────────────────────────────────────────────────────────

class TestSuggestTeam:
    def test_normal(self):
        result = suggest_team("machine learning", 3)
        assert isinstance(result, str) and len(result) > 0
        assert "工具执行失败" not in result

    def test_no_match(self):
        result = suggest_team("ZZNOTEXISTTOPIC999", 3)
        assert isinstance(result, str)
        assert "未找到" in result or "无法" in result, f"无匹配应提示: {result[:100]}"

    def test_size_one(self):
        result = suggest_team("data mining", 1)
        assert isinstance(result, str)
        assert "工具执行失败" not in result


# ─── get_collab_strength ──────────────────────────────────────────────────────

class TestGetCollabStrength:
    def test_normal(self):
        result = get_collab_strength(42, 88)
        assert isinstance(result, str)
        assert "错误" not in result and "工具执行失败" not in result
        import re
        assert re.search(r'0\.\d+', result), f"应包含0-1之间的分数: {result[:200]}"

    def test_nonexistent_author(self):
        result = get_collab_strength(42, 999999)
        assert "错误" in result, f"不存在的作者应返回错误: {result[:100]}"


# ─── compare_authors ──────────────────────────────────────────────────────────

class TestCompareAuthors:
    def test_normal(self):
        result = compare_authors(42, 88)
        assert isinstance(result, str)
        assert "错误" not in result and "工具执行失败" not in result

    def test_nonexistent_author(self):
        result = compare_authors(42, 999999)
        assert "错误" in result, f"不存在的作者应返回错误: {result[:100]}"


# ─── get_community_leaders ────────────────────────────────────────────────────

class TestGetCommunityLeaders:
    @pytest.mark.parametrize("cid", [0, 1, 2, 3])
    def test_valid_community(self, cid):
        result = get_community_leaders(cid, 5)
        assert isinstance(result, str)
        assert "错误" not in result and "工具执行失败" not in result

    def test_invalid_community(self):
        result = get_community_leaders(99, 5)
        assert "错误" in result, f"无效社群应返回错误: {result[:100]}"

    def test_top_k_zero(self):
        result = get_community_leaders(0, 0)
        assert isinstance(result, str)  # 不崩溃


# ─── get_community_topics ─────────────────────────────────────────────────────

class TestGetCommunityTopics:
    def test_normal(self):
        result = get_community_topics(0, 5)
        assert isinstance(result, str)
        assert "工具执行失败" not in result

    def test_invalid_community(self):
        result = get_community_topics(99, 5)
        assert isinstance(result, str)  # 不崩溃


# ─── get_inter_community_strength ────────────────────────────────────────────

class TestGetInterCommunityStrength:
    def test_normal(self):
        result = get_inter_community_strength(0, 1)
        assert isinstance(result, str)
        assert "工具执行失败" not in result

    def test_same_community(self):
        result = get_inter_community_strength(0, 0)
        assert isinstance(result, str)  # 不崩溃

    def test_invalid_community(self):
        result = get_inter_community_strength(0, 99)
        assert isinstance(result, str)  # 不崩溃


# ─── dispatch_tool ────────────────────────────────────────────────────────────

class TestDispatchTool:
    def test_valid_tool(self):
        result = dispatch_tool("get_network_overview", "{}")
        assert isinstance(result, str) and len(result) > 0
        assert "4057" in result

    def test_unknown_tool(self):
        result = dispatch_tool("nonexistent_tool_xyz", "{}")
        assert isinstance(result, str)
        assert "错误" in result or "不存在" in result

    def test_invalid_json_args(self):
        result = dispatch_tool("get_network_overview", "NOT_VALID_JSON{{{")
        assert isinstance(result, str)
        assert "错误" in result

    def test_search_author_via_dispatch(self):
        import json
        result = dispatch_tool("search_author", json.dumps({"query": "Han"}))
        assert isinstance(result, str) and len(result) > 0

    def test_missing_required_param(self):
        result = dispatch_tool("predict_collaboration", "{}")
        assert isinstance(result, str)
        assert "错误" in result  # 参数不匹配


# ─── find_collab_opportunities + get_author_papers ───────────────────────────

class TestAdditionalAuthorTools:
    def test_find_collab_opportunities_normal(self):
        result = find_collab_opportunities(42, 5)
        assert isinstance(result, str)
        assert "工具执行失败" not in result

    def test_find_collab_opportunities_nonexistent(self):
        result = find_collab_opportunities(999999, 5)
        assert "错误" in result

    def test_get_author_papers_normal(self):
        result = get_author_papers(42)
        assert isinstance(result, str)
        assert "工具执行失败" not in result

    def test_get_author_papers_nonexistent(self):
        result = get_author_papers(999999)
        assert "错误" in result
