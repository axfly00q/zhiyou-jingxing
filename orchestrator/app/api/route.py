"""个性化路线规划 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import RouteResponse, TouristPreference
from app.services.kg_planner import generate_narrative, plan_route

router = APIRouter(prefix="/api/route", tags=["route"])

PARKS = ["zhuozhengyuan", "liuyuan"]


@router.get("/parks")
async def list_parks():
    return [{"code": "zhuozhengyuan", "name": "拙政园"},
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
