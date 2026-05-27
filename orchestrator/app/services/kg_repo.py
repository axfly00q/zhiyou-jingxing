"""景区知识图谱访问层。

为了在无 Neo4j 环境也能跑通，提供"双源"实现：
1) 优先 Neo4j：执行 Cypher 拉取节点与边；
2) 回退 JSON：读取 data/kg/{park}.json，结构同下。

JSON 结构（也是 Neo4j 节点属性的镜像）：
{
  "park": "zhuozhengyuan",
  "park_name": "拙政园",
  "spots": [
    {
      "code": "yuanxiang_tang",
      "name": "远香堂",
      "themes": {"history": 0.9, "architecture": 0.8, "nature": 0.4,
                  "family": 0.3, "photo": 0.6},
      "highlight": "园中主厅，'香远益清'……",
      "suggested_minutes": 12,
      "neighbors": [
        {"code": "xiao_canglang", "walk_minutes": 4},
        ...
      ]
    },
    ...
  ]
}
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.logger import logger

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "kg"


class Spot:
    __slots__ = ("code", "name", "themes", "highlight", "suggested_minutes", "neighbors", "tags", "map_x", "map_y", "quiz")

    def __init__(self, code: str, name: str, themes: Dict[str, float],
                 highlight: str, suggested_minutes: int,
                 neighbors: List[dict],
                 tags: Optional[List[str]] = None,
                 map_x: Optional[float] = None,
                 map_y: Optional[float] = None,
                 quiz: Optional[List[dict]] = None) -> None:
        self.code = code
        self.name = name
        self.themes = themes
        self.highlight = highlight
        self.suggested_minutes = suggested_minutes
        self.neighbors = neighbors  # [{code, walk_minutes}]
        self.tags: List[str] = tags or []
        self.map_x: Optional[float] = map_x
        self.map_y: Optional[float] = map_y
        self.quiz: List[dict] = quiz or []

    def neighbor_minutes(self, other_code: str) -> Optional[int]:
        for n in self.neighbors:
            if n["code"] == other_code:
                return n["walk_minutes"]
        return None


class ParkGraph:
    def __init__(self, park: str, park_name: str, spots: List[Spot],
                 entrance_code: Optional[str] = None) -> None:
        self.park = park
        self.park_name = park_name
        self.spots: Dict[str, Spot] = {s.code: s for s in spots}
        self.entrance_code: Optional[str] = entrance_code

    def get(self, code: str) -> Optional[Spot]:
        return self.spots.get(code)

    def all(self) -> List[Spot]:
        return list(self.spots.values())


def _load_from_json(park: str) -> Optional[ParkGraph]:
    fp = DATA_DIR / f"{park}.json"
    if not fp.exists():
        return None
    raw = json.loads(fp.read_text(encoding="utf-8"))
    spots = [Spot(
        s["code"], s["name"], s["themes"], s["highlight"],
        s["suggested_minutes"], s.get("neighbors", []),
        tags=s.get("tags", []),
        map_x=s.get("map_x"),
        map_y=s.get("map_y"),
        quiz=s.get("quiz", []),
    ) for s in raw["spots"]]
    return ParkGraph(raw["park"], raw["park_name"], spots,
                     entrance_code=raw.get("entrance"))


def _load_from_neo4j(park: str) -> Optional[ParkGraph]:
    try:
        from neo4j import GraphDatabase  # 延迟导入，避免无 Neo4j 时报错
    except Exception:
        return None
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    except Exception as exc:
        logger.warning("Neo4j 连接失败：{}", exc)
        return None

    cypher_spots = """
    MATCH (p:Park {code: $park})-[:HAS_SPOT]->(s:Spot)
    RETURN s.code AS code, s.name AS name, s.themes AS themes,
           s.highlight AS highlight, s.suggested_minutes AS suggested_minutes,
           p.name AS park_name
    """
    cypher_edges = """
    MATCH (p:Park {code: $park})-[:HAS_SPOT]->(s1:Spot)-[r:NEXT_TO]->(s2:Spot)
    RETURN s1.code AS a, s2.code AS b, r.walk_minutes AS w
    """
    spots: Dict[str, Spot] = {}
    park_name = ""
    try:
        with driver.session() as sess:
            for rec in sess.run(cypher_spots, park=park):
                themes = rec["themes"] or {}
                if isinstance(themes, str):
                    themes = json.loads(themes)
                spots[rec["code"]] = Spot(
                    rec["code"], rec["name"], themes,
                    rec["highlight"] or "", int(rec["suggested_minutes"] or 10), [],
                )
                park_name = rec["park_name"] or ""
            for rec in sess.run(cypher_edges, park=park):
                a, b, w = rec["a"], rec["b"], int(rec["w"] or 5)
                if a in spots:
                    spots[a].neighbors.append({"code": b, "walk_minutes": w})
                if b in spots:
                    spots[b].neighbors.append({"code": a, "walk_minutes": w})
    except Exception as exc:
        logger.warning("Neo4j 查询失败，回退 JSON：{}", exc)
        return None
    finally:
        driver.close()
    if not spots:
        return None
    return ParkGraph(park, park_name, list(spots.values()))


def load_park(park: str) -> Optional[ParkGraph]:
    """优先 Neo4j → 失败回退 JSON。Neo4j 加载时从 JSON 补充 entrance/tags/坐标。"""
    return _load_park_cached(park)


@lru_cache(maxsize=16)
def _load_park_cached(park: str) -> Optional[ParkGraph]:
    g = _load_from_neo4j(park)
    if g is not None:
        # 用 JSON 补充 Neo4j 不含的字段
        g_json = _load_from_json(park)
        if g_json is not None:
            g.entrance_code = g_json.entrance_code
            for spot in g.all():
                js = g_json.get(spot.code)
                if js is not None:
                    spot.tags = js.tags
                    spot.map_x = js.map_x
                    spot.map_y = js.map_y
        return g
    return _load_from_json(park)
