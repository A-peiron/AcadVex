# tests/demo_scenarios.py
"""
Week 1 演示场景测试
运行方式：conda activate acadvex && python -m tests.demo_scenarios
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.loop import run_agent

SCENARIOS = [
    {
        "id": "A",
        "desc": "合作潜力预测（双 ID 已知）",
        "query": "Author 42 和 Author 88 的学术合作潜力如何？请给出分数和分析。",
    },
    {
        "id": "B",
        "desc": "作者搜索 + 社群分析",
        "query": "帮我找一下 Jiawei Han 这位作者，并分析他所在社群的核心成员和研究方向。",
    },
    {
        "id": "C",
        "desc": "网络统计概览",
        "query": "整个 DBLP 学术合作网络的规模如何？各研究社群分别有多少作者？",
    },
]


def run_all():
    passed = 0
    for s in SCENARIOS:
        print(f"\n{'='*60}")
        print(f"场景 {s['id']}：{s['desc']}")
        print(f"问题：{s['query']}")
        print("-" * 60)

        answer = run_agent(s['query'])

        assert answer and len(answer) > 10, f"场景 {s['id']} 响应为空或过短！"
        print(f"回答：{answer[:300]}{'...' if len(answer) > 300 else ''}")
        print(f"✓ 场景 {s['id']} 通过（响应长度 {len(answer)} 字符）")
        passed += 1

    print(f"\n{'='*60}")
    print(f"✓ 全部通过：{passed}/{len(SCENARIOS)} 个场景")


if __name__ == "__main__":
    run_all()
