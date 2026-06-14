"""个性化路线规划 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import RouteResponse, TouristPreference
from app.services.kg_planner import generate_narrative, plan_route

router = APIRouter(prefix="/api/route", tags=["route"])

PARKS = ["lingshan", "liuyuan"]


@router.get("/parks")
async def list_parks():
    return [{"code": "lingshan", "name": "灵山胜境"},
            {"code": "liuyuan", "name": "留园"}]


@router.post("/{park}/plan", response_model=RouteResponse)
async def plan(park: str, pref: TouristPreference):
    if park not in PARKS:
        raise HTTPException(404, f"unknown park: {park}")
    route = plan_route(park, pref)
    if route is None:
        raise HTTPException(404, "park graph not found")
    route.narrative = await generate_narrative(route, pref)
    return route


@router.get("/{park}/graph")
async def get_park_graph(park: str):
    """返回景区知识图谱结构（节点 + 有向边），供前端可视化。

    Response:
    ```json
    {
      "park": "lingshan",
      "park_name": "拙政园",
      "nodes": [
        {
          "code": "yuanxiang_tang",
          "name": "远香堂",
          "themes": {"history": 0.9, ...},
          "suggested_minutes": 12,
          "map_x": 0.3,
          "map_y": 0.4,
          "tags": ["wheelchair_ok"]
        },
        ...
      ],
      "edges": [
        {"source": "yuanxiang_tang", "target": "xiao_canglang", "walk_minutes": 4},
        ...
      ]
    }
    ```
    """
    if park not in PARKS:
        raise HTTPException(404, f"unknown park: {park}")
    from app.services.kg_repo import load_park
    graph = load_park(park)
    if graph is None:
        raise HTTPException(404, "park graph not found")

    nodes = [
        {
            "code": s.code,
            "name": s.name,
            "themes": s.themes,
            "highlight": s.highlight,
            "suggested_minutes": s.suggested_minutes,
            "map_x": s.map_x,
            "map_y": s.map_y,
            "tags": s.tags,
        }
        for s in graph.all()
    ]
    # 从 neighbors 推导有向边（去重：a→b 和 b→a 视为同一条无向边取一次）
    seen: set[tuple[str, str]] = set()
    edges = []
    for s in graph.all():
        for n in s.neighbors:
            key = tuple(sorted([s.code, n["code"]]))
            if key not in seen:
                seen.add(key)
                edges.append({
                    "source": s.code,
                    "target": n["code"],
                    "walk_minutes": n["walk_minutes"],
                })
    return {
        "park": graph.park,
        "park_name": graph.park_name,
        "entrance": graph.entrance_code,
        "nodes": nodes,
        "edges": edges,
    }

