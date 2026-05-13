"""
AcadVex 性能基准测试脚本
运行方式：
    cd AcadVex
    uvicorn api.main:app --host 127.0.0.1 --port 8000   # 另开终端先启动服务
    python scripts/benchmark.py
"""

import time
import statistics
import requests

BASE_URL = "http://127.0.0.1:8000"
REPEATS = 3  # 每项指标重复次数


def measure(label: str, fn, repeats: int = REPEATS):
    """执行 fn() repeats 次，打印均值与各次结果。"""
    times = []
    for i in range(repeats):
        t0 = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - t0) * 1000  # ms
        times.append(elapsed)
        print(f"  [{i+1}/{repeats}] {elapsed:.1f} ms")
    avg = statistics.mean(times)
    print(f"  >>> {label} 均值: {avg:.1f} ms\n")
    return avg


# ── 1. FPGCL Top-20 合作推荐查询延迟 ──────────────────────────────────────
print("=" * 50)
print("1. FPGCL Top-20 合作推荐查询延迟")
print("=" * 50)

def fpgcl_query():
    r = requests.get(f"{BASE_URL}/api/authors/42/recommendations", timeout=10)
    assert r.status_code == 200, f"HTTP {r.status_code}"

fpgcl_avg = measure("FPGCL Top-20 推荐", fpgcl_query)


# ── 2. RAG 检索延迟（含 CrossEncoder 精排）────────────────────────────────
# 通过同步对话接口触发 search_knowledge 工具，隔离 LLM 调用耗时不现实，
# 因此直接调用 retriever 模块计时（需在脚本所在目录能 import）
print("=" * 50)
print("2. RAG 检索延迟（含 CrossEncoder 精排）")
print("=" * 50)

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from rag.retriever import retrieve  # 首次调用会加载模型

# 预热：加载模型（不计入结果）
print("  预热中（加载嵌入模型与 CrossEncoder）...")
retrieve("graph neural network", top_k=3)
print("  预热完成\n")

def rag_query():
    retrieve("学术合作推荐图神经网络", top_k=3)

rag_avg = measure("RAG 检索（含精排）", rag_query)


# ── 3. LLM 单轮响应延迟（含一次工具调用）────────────────────────────────
print("=" * 50)
print("3. LLM 单轮响应延迟（含工具调用，同步接口）")
print("=" * 50)
print("  注意：此项依赖网络延迟，结果受 DeepSeek API 响应速度影响\n")

def llm_query():
    payload = {
        "message": "Author 42 的合作潜力分数和 Author 88 相比如何？",
        "session_id": "benchmark_test"
    }
    r = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=30)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"

llm_avg = measure("LLM 单轮响应", llm_query)


# ── 汇总 ──────────────────────────────────────────────────────────────────
print("=" * 50)
print("汇总（填入论文表格）")
print("=" * 50)
print(f"  LLM 单轮响应延迟（含工具调用）：{llm_avg/1000:.2f} s")
print(f"  FPGCL Top-20 合作推荐查询延迟：{fpgcl_avg:.1f} ms")
print(f"  RAG 检索延迟（含 CrossEncoder）：{rag_avg:.1f} ms")
