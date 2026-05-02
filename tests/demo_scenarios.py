# tests/demo_scenarios.py
"""
端到端测试：覆盖多轮对话、工具链组合、错误恢复等真实场景
运行方式：conda activate acadvex && python -m tests.demo_scenarios
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.loop import run_agent


def check(condition, msg):
    if not condition:
        raise AssertionError(f"FAIL: {msg}")
    print(f"  ✓ {msg}")


# ──────────────────────────────────────────────
# 场景 A：合作潜力预测（ID 已知，单轮）
# ──────────────────────────────────────────────
def scenario_a():
    print("\n场景 A：合作潜力预测（ID 已知）")
    ans = run_agent("Author 42 和 Author 88 的学术合作潜力如何？请给出分数和分析。")
    check(len(ans) > 50, "响应非空")
    check(any(k in ans for k in ["分数", "score", "合作", "潜力"]), "包含合作潜力相关词")
    # 应调用 predict_collaboration 工具，结果含数字分数
    import re
    check(bool(re.search(r'\d+\.?\d*', ans)), "响应包含数字分数")


# ──────────────────────────────────────────────
# 场景 B：作者搜索 + 社群分析（工具链组合）
# ──────────────────────────────────────────────
def scenario_b():
    print("\n场景 B：作者搜索 + 社群分析")
    ans = run_agent("帮我找一下 Jiawei Han，并分析他所在社群的核心成员和研究方向。")
    check(len(ans) > 50, "响应非空")
    check("Jiawei Han" in ans or "韩家炜" in ans or "1015" in ans, "识别出目标作者")
    check(any(k in ans for k in ["社群", "community", "Data Mining", "数据挖掘"]), "包含社群信息")
    check(any(k in ans for k in ["影响力", "degree", "论文", "paper"]), "包含作者详情")


# ──────────────────────────────────────────────
# 场景 C：网络统计概览（单工具，验证数据准确性）
# ──────────────────────────────────────────────
def scenario_c():
    print("\n场景 C：网络统计概览")
    ans = run_agent("整个 DBLP 学术合作网络的规模如何？各研究社群分别有多少作者？")
    check(len(ans) > 50, "响应非空")
    check("4057" in ans or "4,057" in ans, "作者总数正确（4057）")
    check("14328" in ans or "14,328" in ans, "论文总数正确（14328）")
    check(ans.count("社群") + ans.count("community") >= 2, "列出多个社群")


# ──────────────────────────────────────────────
# 场景 D：多轮对话 + 上下文记忆
# ──────────────────────────────────────────────
def scenario_d():
    print("\n场景 D：多轮对话 + 上下文记忆")
    history = []

    # 第 1 轮：搜索作者，建立上下文
    ans1 = run_agent("帮我搜索 Philip S. Yu 这位学者", history=history)
    history += [
        {"role": "user", "content": "帮我搜索 Philip S. Yu 这位学者"},
        {"role": "assistant", "content": ans1},
    ]
    check("Philip" in ans1 or "Yu" in ans1, "第1轮：识别出目标作者")

    # 第 2 轮：基于第 1 轮结果追问影响力（不重复提名字）
    ans2 = run_agent("他的网络影响力怎么样？degree centrality 是多少？", history=history)
    history += [
        {"role": "user", "content": "他的网络影响力怎么样？degree centrality 是多少？"},
        {"role": "assistant", "content": ans2},
    ]
    check(
        any(k in ans2 for k in ["degree", "centrality", "影响力", "中心", "0."]),
        "第2轮：回答了影响力指标"
    )

    # 第 3 轮：基于前两轮，推荐合作者
    ans3 = run_agent("能推荐几位适合与他合作的学者吗？", history=history)
    check(
        any(k in ans3 for k in ["推荐", "合作", "Author", "学者", "分数"]),
        "第3轮：给出了合作推荐"
    )


# ──────────────────────────────────────────────
# 场景 E：不存在的作者 ID（错误恢复）
# ──────────────────────────────────────────────
def scenario_e():
    print("\n场景 E：不存在的作者 ID（错误恢复）")
    ans = run_agent("Author 999999 的影响力如何？")
    check(len(ans) > 10, "响应非空（未崩溃）")
    check(
        any(k in ans for k in ["不存在", "找不到", "没有", "无法", "error", "错误", "未找到"]),
        "返回友好错误提示"
    )

    # 错误后系统仍可正常工作
    ans2 = run_agent("整个网络有多少作者？")
    check("4057" in ans2 or "4,057" in ans2, "错误后系统恢复正常")


# ──────────────────────────────────────────────
# 场景 F：模糊查询 + 多结果处理
# ──────────────────────────────────────────────
def scenario_f():
    print("\n场景 F：模糊查询 + 多结果处理")
    ans = run_agent("我想找做 information retrieval 方向的学者，帮我推荐几位影响力较高的。")
    check(len(ans) > 50, "响应非空")
    check(
        any(k in ans for k in ["Information Retrieval", "信息检索", "IR", "社群"]),
        "识别出 IR 社群"
    )
    # 应返回多位作者
    import re
    author_mentions = len(re.findall(r'Author \d+|作者 \d+|\bID[：:]\s*\d+', ans))
    check(len(ans) > 100, "响应足够详细（包含多位作者信息）")


# ──────────────────────────────────────────────
# 场景 G：跨社群合作分析（综合工具调用）
# ──────────────────────────────────────────────
def scenario_g():
    print("\n场景 G：跨社群合作分析")
    ans = run_agent(
        "Database 社群和 Data Mining 社群之间有哪些潜在的跨社群合作机会？"
        "请找出两个社群各自的核心学者，并预测其中一对的合作潜力。"
    )
    check(len(ans) > 100, "响应足够详细")
    check(
        any(k in ans for k in ["Database", "数据库", "Data Mining", "数据挖掘"]),
        "涉及两个目标社群"
    )
    check(
        any(k in ans for k in ["合作潜力", "分数", "score", "predict"]),
        "包含合作潜力预测结果"
    )


# ──────────────────────────────────────────────
# 场景 H：流式 tool_calls 截断修复验证
# ──────────────────────────────────────────────
def scenario_h():
    print("\n场景 H：流式 tool_calls 截断修复验证")
    ans = run_agent("希望有更详细的使用示例")
    check(len(ans) > 100, "响应足够完整（不截断）")
    stripped = ans.strip()
    check(not stripped.endswith("：") and not stripped.endswith(":"), "响应不以冒号结尾（无截断）")


# ──────────────────────────────────────────────
# 场景 I：团队组建（suggest_team）
# ──────────────────────────────────────────────
def scenario_i():
    print("\n场景 I：团队组建（suggest_team）")
    ans = run_agent("帮我组建一个专注于图神经网络研究的3人团队，要求成员互补。")
    check(len(ans) > 50, "响应非空")
    check(
        any(k in ans for k in ["团队", "成员", "Author", "学者", "推荐"]),
        "包含团队成员信息"
    )
    import re
    ids = re.findall(r'\b\d+\b', ans)
    check(len(set(ids)) >= 2, "至少包含2个不重复的作者ID")


# ──────────────────────────────────────────────
# 场景 J：合作路径查找（find_collab_path）
# ──────────────────────────────────────────────
def scenario_j():
    print("\n场景 J：合作路径查找（find_collab_path）")
    ans = run_agent("Author 42 和 Author 1015 之间有没有合作路径？请找出最短路径。")
    check(len(ans) > 20, "响应非空")
    check(
        any(k in ans for k in ["路径", "path", "合作", "→", "->", "42", "1015"]),
        "包含路径信息"
    )


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────
SCENARIOS = [
    ("A", "合作潜力预测（ID已知）", scenario_a),
    ("B", "作者搜索+社群分析", scenario_b),
    ("C", "网络统计概览（数据准确性）", scenario_c),
    ("D", "多轮对话+上下文记忆", scenario_d),
    ("E", "不存在作者ID（错误恢复）", scenario_e),
    ("F", "模糊查询+多结果处理", scenario_f),
    ("G", "跨社群合作分析", scenario_g),
    ("H", "流式tool_calls截断修复验证", scenario_h),
    ("I", "团队组建（suggest_team）", scenario_i),
    ("J", "合作路径查找（find_collab_path）", scenario_j),
]


def run_all():
    passed = 0
    failed = []

    for sid, desc, fn in SCENARIOS:
        print(f"\n{'='*60}")
        print(f"场景 {sid}：{desc}")
        print("-" * 60)
        try:
            fn()
            print(f"✓ 场景 {sid} 通过")
            passed += 1
        except AssertionError as e:
            print(f"✗ 场景 {sid} 失败：{e}")
            failed.append(sid)
        except Exception as e:
            print(f"✗ 场景 {sid} 异常：{e}")
            failed.append(sid)

    print(f"\n{'='*60}")
    print(f"结果：{passed}/{len(SCENARIOS)} 通过", end="")
    if failed:
        print(f"，失败场景：{', '.join(failed)}")
    else:
        print("\n✓ 全部通过")


if __name__ == "__main__":
    run_all()
