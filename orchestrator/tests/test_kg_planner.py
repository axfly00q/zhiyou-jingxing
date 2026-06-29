from __future__ import annotations

from app.schemas import TouristPreference
from app.services.kg_planner import plan_route


def test_history_preference_picks_history_spots():
    pref = TouristPreference(
        history=1.0,
        nature=0.0,
        architecture=1.0,
        family=0.0,
        photo=0.0,
        duration_min=90,
    )
    route = plan_route("lingshan", pref)
    assert route is not None
    codes = {s.code for s in route.spots}
    assert codes & {"jiu_long_guan_yu", "xiang_mo_fu_diao", "xiang_fu_chan_si", "ling_shan_da_fo"}
    assert route.total_minutes <= pref.duration_min + 15


def test_nature_preference_picks_nature_or_photo_spots():
    pref = TouristPreference(
        history=0.0,
        nature=1.0,
        architecture=0.0,
        family=0.0,
        photo=1.0,
        duration_min=90,
    )
    route = plan_route("lingshan", pref)
    assert route is not None
    codes = {s.code for s in route.spots}
    assert codes & {"bai_lian_chi", "jiu_long_guan_yu", "ling_shan_da_fo", "wu_yin_tan_cheng"}


def test_unknown_park_returns_none():
    pref = TouristPreference()
    assert plan_route("not_exist_park", pref) is None


def test_duration_short_yields_few_spots():
    pref = TouristPreference(duration_min=30)
    route = plan_route("lingshan", pref)
    assert route is not None
    assert len(route.spots) <= 3
