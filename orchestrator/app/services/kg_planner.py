"""创新点 1：知识图谱驱动的个性化游览路线规划。

输入：游客 5 维偏好向量 + 期望时长 + 起点。
输出：有序景点列表 + 总时长 + 总评分 + 由 LLM 生成的开场白。

算法：
1. 对图中每个景点计算 `theme_score = Σ pref[k] * spot.themes[k]`；
2. 以起点为种子，使用 **贪心 + 时间约束** 扩张：每步选择
   `next_score = theme_score(s) - α * walk_minutes(curr, s)`
   最大且未访问的邻居（α 默认 0.05），如无邻居则跳到全局最高分未访问点
   并按估算步行 8 分钟计入；
3. 累计耗时（讲解 + 步行）超过 `duration_min` 时停止；
4. 由 LLM 用偏好+路线生成自然语言开场白，配合数字人播报。

为什么不直接最短路径：景区导览是"逛多少看多少"问题，而非 TSP，
贪心+主题加权效果直观、可解释，PPT 易讲。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from app.core.logger import logger
from app.schemas import RouteResponse, RouteSpot, TouristPreference
from app.services.kg_repo import ParkGraph, Spot, load_park
from app.services.llm_client import llm_client

WALK_PENALTY = 0.05  # α
FALLBACK_WALK_MINUTES = 8


def _theme_score(spot: Spot, pref: TouristPreference) -> float:
    p = {
        "history": pref.history, "nature": pref.nature,
        "architecture": pref.architecture, "family": pref.family,
        "photo": pref.photo,
    }
    return sum(p.get(k, 0.0) * float(v) for k, v in spot.themes.items())


def _pick_start(graph: ParkGraph, pref: TouristPreference) -> Spot:
    if pref.start_spot and graph.get(pref.start_spot):
        return graph.get(pref.start_spot)  # type: ignore[return-value]
    # 未指定起点 → 优先使用园区真实入口
    if graph.entrance_code and graph.get(graph.entrance_code):
        return graph.get(graph.entrance_code)  # type: ignore[return-value]
    # 最后兜底：选 theme_score 最高的景点
    return max(graph.all(), key=lambda s: _theme_score(s, pref))


def _next_step(curr: Spot, graph: ParkGraph, visited: set,
               pref: TouristPreference,
               excluded: Optional[set] = None) -> Tuple[Optional[Spot], int]:
    excluded = excluded or set()
    best: Optional[Spot] = None
    best_score = -1e9
    best_walk = FALLBACK_WALK_MINUTES
    # 优先在邻居中选
    for n in curr.neighbors:
        s = graph.get(n["code"])
        if not s or s.code in visited or s.code in excluded:
            continue
        score = _theme_score(s, pref) - WALK_PENALTY * n["walk_minutes"]
        if score > best_score:
            best_score, best, best_walk = score, s, n["walk_minutes"]
    if best is not None:
        return best, best_walk
    # 邻居都访问过 → 全局兜底
    candidates = [s for s in graph.all() if s.code not in visited and s.code not in excluded]
    if not candidates:
        return None, 0
    best = max(candidates, key=lambda s: _theme_score(s, pref))
    return best, FALLBACK_WALK_MINUTES


def plan_route(park: str, pref: TouristPreference) -> Optional[RouteResponse]:
    graph = load_park(park)
    if graph is None:
        logger.warning("找不到园区图谱：{}", park)
        return None

    # A4: 硬约束过滤——排除不满足条件的景点（入口不参与过滤）
    excluded: set[str] = set()
    entrance = graph.entrance_code
    for s in graph.all():
        if s.code == entrance:
            continue  # 入口始终保留
        if pref.wheelchair and "wheelchair_ok" not in s.tags:
            excluded.add(s.code)
        elif pref.children and "child_ok" not in s.tags:
            excluded.add(s.code)
        elif pref.rush and "skip_if_rush" in s.tags:
            excluded.add(s.code)

    start = _pick_start(graph, pref)
    visited = {start.code}
    ordered: List[Tuple[Spot, int]] = [(start, 0)]  # (spot, walk_in_minutes)
    used = start.suggested_minutes

    # 贪心扩张：起点本身已超期望时长时不再拼接；
    # 跳过占比过大（>80%）的单个超长景点，避免把中部 40 min 拼进 20 min 路线。
    max_per_spot = max(int(pref.duration_min * 0.8), 5)
    while used < pref.duration_min:
        nxt, walk = _next_step(ordered[-1][0], graph, visited, pref, excluded)
        if nxt is None:
            break
        cost = walk + nxt.suggested_minutes
        if nxt.suggested_minutes > max_per_spot:
            visited.add(nxt.code)  # 标记为已考虑，避免死循环
            continue
        if used + cost > pref.duration_min + 5:  # 容许 5 分钟超出
            break
        ordered.append((nxt, walk))
        visited.add(nxt.code)
        used += cost

    # 超过期望太多时截断展示值，避免误导用户
    display_minutes = min(used, pref.duration_min + 15)

    spots_out = [
        RouteSpot(
            code=s.code, name=s.name,
            themes=[k for k, v in s.themes.items() if v >= 0.5],
            highlight=s.highlight,
            suggested_minutes=s.suggested_minutes,
            tags=s.tags,
            map_x=s.map_x,
            map_y=s.map_y,
        )
        for s, _ in ordered
    ]
    score = sum(_theme_score(s, pref) for s, _ in ordered)
    return RouteResponse(
        park=graph.park_name,
        total_minutes=display_minutes,
        score=round(score, 2),
        spots=spots_out,
        narrative="",  # 由调用方异步填充（避免阻塞）
    )


async def generate_narrative(route: RouteResponse, pref: TouristPreference) -> str:
    """让 LLM 写一段开场白，体现个性化（提偏好 + 路线亮点）。"""
    spots_brief = "、".join(s.name for s in route.spots[:6])
    prompt = (
        f"你是{route.park}的资深导游数字人。"
        f"游客偏好：历史{pref.history:.1f} 自然{pref.nature:.1f} "
        f"建筑{pref.architecture:.1f} 亲子{pref.family:.1f} 摄影{pref.photo:.1f}，"
        f"期望游览约{pref.duration_min}分钟。"
        f"我为他规划了路线：{spots_brief}。"
        "请用 80 字以内、亲切自然的口语，开场介绍今天的游览安排，"
        "突出 1-2 个最贴合其偏好的亮点，不要罗列全部景点。"
    )
    try:
        text = await llm_client.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=200,
        )
        return text.strip() or _fallback_narrative(route)
    except Exception as exc:
        logger.warning("路线开场白生成失败，用模板兜底：{}", exc)
        return _fallback_narrative(route)


def _fallback_narrative(route: RouteResponse) -> str:
    head = "、".join(s.name for s in route.spots[:3])
    return (f"欢迎来到{route.park}！我为您规划了约{route.total_minutes}分钟的游览，"
            f"重点带您打卡{head}等景点，让我们出发吧～")


def plan_remaining(
    park: str,
    current_code: str,
    remaining_codes: List[str],
    pref: TouristPreference,
    action: str = "skip",
    hint: str = "",
) -> Optional[RouteResponse]:
    """从当前位置对剩余路线重规划。

    action="skip": 移除 remaining_codes 第一个（当前下一站），从 current 继续贪心；
    action="add":  在 hint 中模糊匹配景点名，插入到下一站位置，其余不变。
    返回新的 RouteResponse，total_minutes 为剩余预估时长。
    """
    graph = load_park(park)
    if graph is None:
        return None

    current = graph.get(current_code)
    if current is None:
        return None

    remaining_set = set(remaining_codes)

    if action == "add" and hint:
        # 模糊匹配：景点名包含 hint 关键词
        matched = next(
            (s for s in graph.all() if hint in s.name and s.code not in remaining_set
             and s.code != current_code),
            None,
        )
        if matched:
            # 插入到剩余列表第一位
            new_remaining = [matched.code] + remaining_codes
            spots_out = []
            total = 0
            for code in new_remaining:
                s = graph.get(code)
                if s:
                    spots_out.append(RouteSpot(
                        code=s.code, name=s.name,
                        themes=[k for k, v in s.themes.items() if v >= 0.5],
                        highlight=s.highlight,
                        suggested_minutes=s.suggested_minutes,
                        tags=s.tags, map_x=s.map_x, map_y=s.map_y,
                    ))
                    total += s.suggested_minutes
            return RouteResponse(
                park=graph.park_name, total_minutes=total,
                score=0.0, spots=spots_out, narrative="",
            )

    # action=="skip": 移除第一个 remaining，从 current 重新贪心规划剩余
    skip_code = remaining_codes[0] if remaining_codes else None
    # 已访问 = 不在 remaining 中，且不是 current
    visited = {s.code for s in graph.all()
               if s.code != current_code and s.code not in remaining_set}
    if skip_code:
        visited.add(skip_code)

    # 估算剩余时间：用剩余景点平均时长粗估
    remaining_spots = [graph.get(c) for c in remaining_codes[1:] if graph.get(c)]
    remaining_total = sum(s.suggested_minutes for s in remaining_spots if s)
    duration_remaining = max(remaining_total, pref.duration_min // 2)

    ordered: List[Tuple[Spot, int]] = [(current, 0)]
    visited.add(current_code)
    used = 0

    max_per_spot = max(int(duration_remaining * 0.8), 5)
    while used < duration_remaining:
        nxt, walk = _next_step(ordered[-1][0], graph, visited, pref)
        if nxt is None:
            break
        cost = walk + nxt.suggested_minutes
        if nxt.suggested_minutes > max_per_spot:
            visited.add(nxt.code)
            continue
        if used + cost > duration_remaining + 5:
            break
        ordered.append((nxt, walk))
        visited.add(nxt.code)
        used += cost

    spots_out = [
        RouteSpot(
            code=s.code, name=s.name,
            themes=[k for k, v in s.themes.items() if v >= 0.5],
            highlight=s.highlight,
            suggested_minutes=s.suggested_minutes,
            tags=s.tags, map_x=s.map_x, map_y=s.map_y,
        )
        for s, _ in ordered[1:]  # 去掉 current 本身，只返回待游览部分
    ]
    total = sum(s.suggested_minutes for s in spots_out)
    return RouteResponse(
        park=graph.park_name, total_minutes=total,
        score=0.0, spots=spots_out, narrative="",
    )
