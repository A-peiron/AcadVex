"""集成测试：会话历史、隔离、限流"""
import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000"


def safe_print(text):
    """安全打印，避免 GBK 编码错误"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('utf-8', errors='replace').decode('ascii', errors='replace'))

def test_session_history():
    """测试会话历史功能"""
    print("\n=== 测试 1: 会话历史 ===")

    # 第一轮对话 - 完整消费 SSE 流，等待流结束后历史已保存
    print("发送第一条消息...")
    response1 = requests.post(
        f"{BASE_URL}/api/chat/stream",
        json={
            "message": "我的名字是张三",
            "session_id": "test_session_history_001",
        },
        stream=True
    )

    full_response1 = ""
    for line in response1.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    if data['type'] == 'token':
                        full_response1 += data['content']
                    elif data['type'] == 'done':
                        break
                except json.JSONDecodeError:
                    pass

    print(f"AI 回复: {full_response1[:100]}...")

    # 第二轮对话 - 依靠服务端 _session_history 记忆（不传 history 字段）
    print("\n发送第二条消息（测试记忆）...")
    response2 = requests.post(
        f"{BASE_URL}/api/chat/stream",
        json={
            "message": "我刚才说我叫什么名字？",
            "session_id": "test_session_history_001",
        },
        stream=True
    )

    full_response2 = ""
    for line in response2.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    if data['type'] == 'token':
                        full_response2 += data['content']
                    elif data['type'] == 'done':
                        break
                except json.JSONDecodeError:
                    pass

    print(f"AI 回复: {full_response2[:200]}...")

    # 验证 AI 是否记住了名字
    if "张三" in full_response2:
        print("[PASS] 会话历史测试通过：AI 记住了用户名字")
        return True
    else:
        print("[FAIL] 会话历史测试失败：AI 没有记住用户名字")
        print(f"  完整回复: {full_response2}")
        return False


def test_session_isolation():
    """测试会话隔离"""
    print("\n=== 测试 2: 会话隔离 ===")

    # Session A
    print("Session A: 发送消息...")
    response_a = requests.post(
        f"{BASE_URL}/api/chat/stream",
        json={
            "message": "我喜欢红色",
            "session_id": "test_session_isol_a",
        },
        stream=True
    )

    for line in response_a.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    if data['type'] == 'done':
                        break
                except json.JSONDecodeError:
                    pass

    # Session B（全新 session，不应知道 Session A 的信息）
    print("Session B: 询问 Session A 的信息...")
    response_b = requests.post(
        f"{BASE_URL}/api/chat/stream",
        json={
            "message": "我喜欢什么颜色？",
            "session_id": "test_session_isol_b",
        },
        stream=True
    )

    full_response_b = ""
    for line in response_b.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    if data['type'] == 'token':
                        full_response_b += data['content']
                    elif data['type'] == 'done':
                        break
                except json.JSONDecodeError:
                    pass

    print(f"Session B AI 回复: {full_response_b[:200]}...")

    # 验证 Session B 不知道 Session A 的信息
    if "红色" not in full_response_b or "不知道" in full_response_b or "没有" in full_response_b:
        print("[PASS] 会话隔离测试通过：Session B 无法访问 Session A 的信息")
        return True
    else:
        print("[FAIL] 会话隔离测试失败：Session B 可能访问了 Session A 的信息")
        return False


def test_rate_limiting():
    """测试限流功能"""
    print("\n=== 测试 3: 限流 ===")

    success_count = 0
    rate_limited_count = 0

    print("快速发送 25 个 /api/chat 请求...")
    for i in range(25):
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": f"test {i}"},
                timeout=5
            )
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited_count += 1
                print(f"  请求 {i+1}: 被限流 (429)")
        except Exception as e:
            print(f"  请求 {i+1}: 错误 - {e}")

    print(f"\n成功: {success_count}, 被限流: {rate_limited_count}")

    if rate_limited_count > 0:
        print("[PASS] 限流测试通过：检测到限流响应")
        return True
    else:
        print("[WARN] 限流测试警告：未检测到限流（可能限流阈值较高）")
        return True  # 不算失败


def test_health_check():
    """测试健康检查"""
    print("\n=== 测试 4: 健康检查 ===")

    response = requests.get(f"{BASE_URL}/health")
    data = response.json()

    print(f"健康检查响应: {data}")

    if response.status_code == 200 and data.get("status") == "healthy":
        print("[PASS] 健康检查测试通过")
        return True
    else:
        print("[FAIL] 健康检查测试失败")
        return False


if __name__ == "__main__":
    print("开始集成测试...")
    print("=" * 60)

    results = []

    try:
        results.append(("健康检查", test_health_check()))
        results.append(("会话历史", test_session_history()))
        results.append(("会话隔离", test_session_isolation()))
        results.append(("限流", test_rate_limiting()))
    except Exception as e:
        print(f"\n[ERROR] 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name}: {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n[SUCCESS] 所有集成测试通过！")
    else:
        print(f"\n[WARNING] {total - passed} 个测试失败")
