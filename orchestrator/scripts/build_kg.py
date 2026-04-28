"""把 data/kg/*.json 写入 Neo4j。

用法：
  python -m scripts.build_kg            # 写入两个园林
  python -m scripts.build_kg --park liuyuan
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from neo4j import GraphDatabase

from app.core.config import settings

KG_DIR = Path(__file__).resolve().parents[1] / "data" / "kg"


def upsert_park(driver, park_code: str) -> None:
    fp = KG_DIR / f"{park_code}.json"
    raw = json.loads(fp.read_text(encoding="utf-8"))

    cypher_park = """
    MERGE (p:Park {code: $code})
    SET p.name = $name
    """
    cypher_spot = """
    MATCH (p:Park {code: $park})
    MERGE (s:Spot {code: $code})
    SET s.name = $name,
        s.themes = $themes,
        s.highlight = $highlight,
        s.suggested_minutes = $suggested_minutes
    MERGE (p)-[:HAS_SPOT]->(s)
    """
    cypher_edge = """
    MATCH (a:Spot {code: $a}), (b:Spot {code: $b})
    MERGE (a)-[r:NEXT_TO]->(b) SET r.walk_minutes = $w
    MERGE (b)-[r2:NEXT_TO]->(a) SET r2.walk_minutes = $w
    """

    with driver.session() as sess:
        sess.run(cypher_park, code=raw["park"], name=raw["park_name"])
        for s in raw["spots"]:
            sess.run(cypher_spot, park=raw["park"], code=s["code"], name=s["name"],
                     themes=json.dumps(s["themes"], ensure_ascii=False),
                     highlight=s["highlight"],
                     suggested_minutes=s["suggested_minutes"])
        for s in raw["spots"]:
            for n in s.get("neighbors", []):
                sess.run(cypher_edge, a=s["code"], b=n["code"], w=n["walk_minutes"])
    print(f"[OK] 写入 {raw['park_name']}：{len(raw['spots'])} 个景点")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--park", default=None,
                        help="留空写入全部 (zhuozhengyuan, liuyuan)")
    args = parser.parse_args()
    parks = [args.park] if args.park else ["zhuozhengyuan", "liuyuan"]

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    try:
        for p in parks:
            upsert_park(driver, p)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
