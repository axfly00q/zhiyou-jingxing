"""延迟与稳定性测试报告脚本（P1 交付件）。

功能：
  - 对运行中的 Orchestrator 服务发 HTTP 请求
  - 统计 P50 / P95 / P99 / 最大值 / 成功率
  - 覆盖四条关键路径：
      POST /api/chat/text   文本对话主链路（含 TTS）
      POST /api/route/{park}/plan  路线规划
      GET  /api/analytics/overview  大屏总览
      GET  /api/route/{park}/graph  KG 图结构
  - 输出彩色控制台报告 + JSON 文件（docs/latency_report.json）

用法（先启动 orchestrator 再跑）：
    uvicorn app.main:app --port 8010 &
    python -m scripts.latency_report
    python -m scripts.latency_report --base-url http://127.0.0.1:8010 --rounds 30
    python -m scripts.latency_report --stub   # 不需要真实服务，用桩模式演示报告格式
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# ── 路径修正 ─────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ══════════════════════════════════════════════════════════════════════════════
# 数据类
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RequestResult:
    latency_ms: float
    status: int
    ok: bool
    error: Optional[str] = None


@dataclass
class EndpointReport:
    name: str
    method: str
    path: str
    total: int
    success: int
    latencies: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return round(self.success / self.total, 4) if self.total else 0.0

    @property
    def p50(self) -> float:
        return round(statistics.median(self.latencies), 1) if self.latencies else 0.0

    @property
    def p95(self) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        idx = max(0, int(len(s) * 0.95) - 1)
        return round(s[idx], 1)

    @property
    def p99(self) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        idx = max(0, int(len(s) * 0.99) - 1)
        return round(s[idx], 1)

    @property
    def avg(self) -> float:
        return round(statistics.mean(self.latencies), 1) if self.latencies else 0.0

    @property
    def max_ms(self) -> float:
        return round(max(self.latencies), 1) if self.latencies else 0.0

    @property
    def target_ms(self) -> Optional[float]:
        """首字延迟目标（仅 /chat/text 有硬性要求 3000ms）。"""
        if "chat" in self.path:
            return 3000.0
        return None

    @property
    def target_ok(self) -> Optional[bool]:
        if self.target_ms is None:
            return None
        return self.p95 <= self.target_ms


# ══════════════════════════════════════════════════════════════════════════════
# HTTP 请求工具（纯标准库，无需 httpx/requests）
# ══════════════════════════════════════════════════════════════════════════════

def _http(method: str, url: str, body: Optional[dict] = None,
          timeout: float = 15.0) -> RequestResult:
    t0 = time.perf_counter()
    try:
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"} if body else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            elapsed = (time.perf_counter() - t0) * 1000
            return RequestResult(elapsed, resp.status, True)
    except urllib.error.HTTPError as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return RequestResult(elapsed, e.code, False, str(e))
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return RequestResult(elapsed, 0, False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
# 端点定义
# ══════════════════════════════════════════════════════════════════════════════

def _make_endpoints(base: str) -> list:
    """返回测试端点描述列表，每项含 name/method/path/body_fn。"""
    _SESSION = "eval_latency_test"
    _SPOT_QUESTIONS = [
        "远香堂是什么意思",
        "小飞虹在哪里",
        "香洲的历史是什么",
        "介绍一下见山楼",
        "留听阁的名字出自哪首诗",
        "天泉亭有什么特别之处",
        "倒影楼在哪个区域",
        "兰雪堂是谁建的",
        "芙蓉榭最美的季节是什么",
        "灵山大佛什么时候建造的",
    ]

    return [
        {
            "name": "chat/text（文本对话）",
            "method": "POST",
            "path": "/api/chat/text",
            "body_fn": lambda i: {
                "session_id": f"{_SESSION}_{i}",
                "message": _SPOT_QUESTIONS[i % len(_SPOT_QUESTIONS)],
                "park_code": "lingshan",
            },
            "target_ms": 3000,
            "note": "含 Dify RAG + TTS，首字延迟目标 ≤ 3s",
        },
        {
            "name": "route/plan（路线规划）",
            "method": "POST",
            "path": "/api/route/lingshan/plan",
            "body_fn": lambda i: {
                "history": round(random.uniform(0.3, 1.0), 1),
                "nature": round(random.uniform(0.3, 1.0), 1),
                "architecture": round(random.uniform(0.3, 1.0), 1),
                "family": 0.5,
                "photo": 0.5,
                "duration_min": random.choice([60, 90, 120]),
            },
            "target_ms": 2000,
            "note": "含 LLM 开场白生成",
        },
        {
            "name": "analytics/overview（大屏总览）",
            "method": "GET",
            "path": "/api/analytics/overview",
            "body_fn": lambda i: None,
            "target_ms": 500,
            "note": "纯 SQL 聚合，目标 ≤ 500ms",
        },
        {
            "name": "route/graph（KG 图结构）",
            "method": "GET",
            "path": "/api/route/lingshan/graph",
            "body_fn": lambda i: None,
            "target_ms": 300,
            "note": "内存 JSON 加载，目标 ≤ 300ms",
        },
        {
            "name": "analytics/satisfaction-trend（满意度趋势）",
            "method": "GET",
            "path": "/api/analytics/satisfaction-trend",
            "body_fn": lambda i: None,
            "target_ms": 500,
            "note": "Review + sentiment 双源聚合",
        },
        {
            "name": "health（服务健康检查）",
            "method": "GET",
            "path": "/health",
            "body_fn": lambda i: None,
            "target_ms": 100,
            "note": "基准检测，目标 ≤ 100ms",
        },
    ]


# ══════════════════════════════════════════════════════════════════════════════
# 桩模式（演示报告格式，不依赖真实服务）
# ══════════════════════════════════════════════════════════════════════════════

def _gen_stub_latencies(p50: float, p95: float, n: int = 20) -> List[float]:
    """根据目标 P50/P95 生成模拟延迟分布（log-normal）。"""
    import math
    sigma = (math.log(p95) - math.log(p50)) / 1.645
    mu = math.log(p50)
    return [
        round(random.lognormvariate(mu, sigma), 1)
        for _ in range(n)
    ]

STUB_PROFILES = {
    "chat/text（文本对话）":              (1650, 2480),
    "route/plan（路线规划）":             (820,  1950),
    "analytics/overview（大屏总览）":     (42,   110),
    "route/graph（KG 图结构）":           (8,    22),
    "analytics/satisfaction-trend（满意度趋势）": (55, 140),
    "health（服务健康检查）":             (3,    9),
}


def run_stub(rounds: int, endpoints: list) -> List[EndpointReport]:
    reports = []
    for ep in endpoints:
        name = ep["name"]
        p50_stub, p95_stub = STUB_PROFILES.get(name, (100, 300))
        latencies = _gen_stub_latencies(p50_stub, p95_stub, rounds)
        n_fail = max(0, int(rounds * random.uniform(0, 0.02)))  # 0-2% 失败率
        report = EndpointReport(
            name=name,
            method=ep["method"],
            path=ep["path"],
            total=rounds,
            success=rounds - n_fail,
            latencies=latencies,
        )
        reports.append(report)
        dot = "." * min(rounds, 30)
        print(f"  [STUB] {name[:38]:<38} {dot}", flush=True)
    return reports


# ══════════════════════════════════════════════════════════════════════════════
# 真实测试
# ══════════════════════════════════════════════════════════════════════════════

def run_real(base: str, rounds: int, endpoints: list,
             timeout: float = 15.0) -> List[EndpointReport]:
    reports = []
    for ep in endpoints:
        report = EndpointReport(
            name=ep["name"], method=ep["method"], path=ep["path"],
            total=rounds, success=0,
        )
        print(f"  测试 {ep['name'][:38]:<38} ", end="", flush=True)
        for i in range(rounds):
            body = ep["body_fn"](i)
            url = f"{base.rstrip('/')}{ep['path']}"
            result = _http(ep["method"], url, body, timeout)
            if result.ok:
                report.success += 1
                report.latencies.append(result.latency_ms)
                print(".", end="", flush=True)
            else:
                print("F", end="", flush=True)
        print()
        reports.append(report)
    return reports


# ══════════════════════════════════════════════════════════════════════════════
# 报告输出
# ══════════════════════════════════════════════════════════════════════════════

_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"

def _c(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def print_report(reports: List[EndpointReport], mode: str) -> None:
    print()
    mode_tag = _c(f"[{mode}]", _YELLOW)
    print(_c("=" * 72, _BOLD))
    print(_c(f"  智游景行 · 延迟与稳定性测试报告  {mode_tag}", _BOLD))
    print(_c(f"  运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", _BOLD))
    print(_c("=" * 72, _BOLD))
    print()
    # 表头
    cols = f"  {'端点':<36}  {'成功率':>6}  {'P50':>7}  {'P95':>7}  {'P99':>7}  {'Max':>7}  {'目标':>8}  {'状态':>6}"
    print(_c(cols, _BOLD))
    print("  " + "─" * 68)

    all_pass = True
    for r in reports:
        rate_str = f"{r.success_rate*100:.0f}%"
        p50_str  = f"{r.p50:.0f}ms"
        p95_str  = f"{r.p95:.0f}ms"
        p99_str  = f"{r.p99:.0f}ms"
        max_str  = f"{r.max_ms:.0f}ms"

        if r.target_ok is True:
            tgt_str = f"<={int(r.target_ms)}ms"
            status = _c("PASS", _GREEN)
        elif r.target_ok is False:
            tgt_str = f"<={int(r.target_ms)}ms"
            status = _c("SLOW", _RED)
            all_pass = False
        else:
            tgt_str = "-"
            status = _c(" - ", _CYAN)

        if r.success_rate < 0.95:
            status = _c("FLAKY", _RED)
            all_pass = False

        print(f"  {r.name:<36}  {rate_str:>6}  {p50_str:>7}  {p95_str:>7}  "
              f"{p99_str:>7}  {max_str:>7}  {tgt_str:>10}  {status}")

    print("  " + "─" * 68)
    print()

    # 关键指标摘要
    chat = next((r for r in reports if "chat" in r.path), None)
    if chat:
        p95_chat = chat.p95
        target_ok = p95_chat <= 3000
        p95_label = _c(f"{p95_chat:.0f}ms", _GREEN if target_ok else _RED)
        print(f"  [KEY] 对话首字延迟 P95 = {p95_label}  (目标 <=3000ms, "
              f"{'OK' if target_ok else 'SLOW'})")

    rate = next((r for r in reports if "chat" in r.path), None)
    if rate:
        sr = rate.success_rate
        sr_label = _c(f"{sr*100:.1f}%", _GREEN if sr >= 0.95 else _RED)
        print(f"  [KEY] 对话接口成功率 = {sr_label}  (目标 >=95%, "
              f"{'OK' if sr >= 0.95 else 'FAIL'})")

    print()
    overall_label = _c("PASS", _GREEN) if all_pass else _c("FAIL", _RED)
    print(_c(f"  Summary: {overall_label}", _BOLD))
    print(_c("=" * 72, _BOLD))
    print()


def build_json_report(reports: List[EndpointReport], mode: str) -> dict:
    return {
        "generated_at": datetime.now().isoformat(),
        "mode": mode,
        "thresholds": {
            "chat_p95_ms": 3000,
            "success_rate_min": 0.95,
        },
        "endpoints": [
            {
                "name": r.name,
                "method": r.method,
                "path": r.path,
                "total": r.total,
                "success": r.success,
                "success_rate": r.success_rate,
                "latency": {
                    "avg_ms": r.avg,
                    "p50_ms": r.p50,
                    "p95_ms": r.p95,
                    "p99_ms": r.p99,
                    "max_ms": r.max_ms,
                },
                "target_ms": r.target_ms,
                "target_ok": r.target_ok,
            }
            for r in reports
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="智游景行 延迟与稳定性测试")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010",
                        help="Orchestrator 服务地址（默认 http://127.0.0.1:8010）")
    parser.add_argument("--rounds", type=int, default=20,
                        help="每端点测试轮次（默认 20）")
    parser.add_argument("--timeout", type=float, default=15.0,
                        help="单次请求超时秒数（默认 15s）")
    parser.add_argument("--stub", action="store_true",
                        help="桩模式：不需要真实服务，生成模拟数据演示报告格式")
    parser.add_argument("--json-out", default=None,
                        help="JSON 报告输出路径（默认 docs/latency_report.json）")
    args = parser.parse_args()

    endpoints = _make_endpoints(args.base_url)
    mode = "STUB" if args.stub else "REAL"

    if args.stub:
        print(f"  桩模式：模拟 {args.rounds} 轮延迟数据（不需要真实服务）")
        reports = run_stub(args.rounds, endpoints)
    else:
        print(f"  目标服务：{args.base_url}，轮次：{args.rounds}")
        # 先 health check
        health = _http("GET", f"{args.base_url}/health", timeout=5.0)
        if not health.ok:
            print(f"  ✗ 服务无响应（{args.base_url}/health → {health.error}）")
            print("    提示：先启动服务，或使用 --stub 桩模式生成演示报告")
            sys.exit(2)
        print(f"  ✓ 服务健康检查通过（{health.latency_ms:.0f}ms）")
        reports = run_real(args.base_url, args.rounds, endpoints, args.timeout)

    print_report(reports, mode)

    out_path = Path(args.json_out) if args.json_out else \
               Path(__file__).resolve().parents[2] / "docs" / "latency_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(build_json_report(reports, mode), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  JSON 报告已写入：{out_path}")


if __name__ == "__main__":
    main()
