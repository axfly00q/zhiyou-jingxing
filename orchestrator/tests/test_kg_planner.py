"""kg_planner 单测：纯 JSON 加载 + 贪心算法，验证主题加权 & 时长约束。"""
from __future__ import annotations

from app.schemas import TouristPreference
from app.services.kg_planner import plan_route


def test_history_preference_picks_history_spots():
    pref = TouristPreference(history=1.0, nature=0.0, architecture=1.0,
                             family=0.0, photo=0.0, duration_min=60)
    route = plan_route("zhuozhengyuan", pref)
    assert route is not None
    names = [s.name for s in route.spots]
    # 历史/建筑高分景点应优先入选
    assert "远香堂" in names or "香洲" in names or "见山楼" in names
    # 时长不超出
    assert route.total_minutes <= pref.duration_min + 5


def test_nature_preference_picks_nature_spots():
    pref = TouristPreference(history=0.0, nature=1.0, architecture=0.0,
                             family=0.0, photo=1.0, duration_min=60)
    route = plan_route("zhuozhengyuan", pref)
    assert route is not None
    names = [s.name for s in route.spots]
    # 自然/摄影高分景点应优先入选
    assert any(n in names for n in ("芙蓉榭", "倒影楼", "留听阁"))


def test_unknown_park_returns_none():
    pref = TouristPreference()
    assert plan_route("not_exist_park", pref) is None


def test_duration_short_yields_few_spots():
    pref = TouristPreference(duration_min=30)
    route = plan_route("liuyuan", pref)
    assert route is not None
    assert len(route.spots) <= 4
