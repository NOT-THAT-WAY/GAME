#!/usr/bin/env python3
"""Migrate the legacy 16x16 edge grids to the strict topology v1 document."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "Assets" / "_Project" / "Maze" / "MazeGrid16x16.json"
DEFAULT_OUTPUT = REPO_ROOT / "Assets" / "_Project" / "Maze" / "MazeTopology16x16.v1.json"
DIRECTIONS = ("N", "E", "S", "W")
MAXIMUM_GRID_SIDE = 1024


def reject_duplicate_members(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON property: {key}")
        result[key] = value
    return result


def require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return value


def require_int(value: Any, path: str, minimum: int, maximum: int) -> int:
    # bool herite de int en Python : `type` est volontaire ici.
    if type(value) is not int or value < minimum or value > maximum:
        raise ValueError(f"{path} must be an integer in [{minimum}, {maximum}]")
    return value


def require_pair(value: Any, path: str, maximum_x: int, maximum_y: int) -> list[int]:
    pair = require_list(value, path)
    if len(pair) != 2:
        raise ValueError(f"{path} must contain exactly two coordinates")
    return [
        require_int(pair[0], f"{path}[0]", 0, maximum_x),
        require_int(pair[1], f"{path}[1]", 0, maximum_y),
    ]


def edge_is_in_bounds(edge: dict[str, Any], width: int, height: int) -> bool:
    if edge["axis"] == "vertical":
        return 0 <= edge["x"] <= width and 0 <= edge["y"] < height
    return edge["axis"] == "horizontal" and 0 <= edge["x"] < width and 0 <= edge["y"] <= height


def edge_index(axis: str, x: int, y: int, width: int, height: int) -> int:
    if axis == "vertical":
        return y * (width + 1) + x
    return (width + 1) * height + y * width + x


def edge_for_direction(node: list[int], direction: str) -> dict[str, Any]:
    x, y = node
    if direction == "N":
        return {"axis": "vertical", "x": x, "y": y}
    if direction == "S":
        return {"axis": "vertical", "x": x, "y": y - 1}
    if direction == "E":
        return {"axis": "horizontal", "x": x, "y": y}
    if direction == "W":
        return {"axis": "horizontal", "x": x - 1, "y": y}
    raise ValueError(f"unknown pivot direction: {direction}")


def rotate(direction: str, quarter_turns: int) -> str:
    return DIRECTIONS[(DIRECTIONS.index(direction) + quarter_turns) % len(DIRECTIONS)]


def boundary_edge(cell: list[int], width: int, height: int) -> dict[str, Any]:
    x, y = cell
    if y == 0:
        return {"axis": "horizontal", "x": x, "y": 0}
    if y == height - 1:
        return {"axis": "horizontal", "x": x, "y": height}
    if x == 0:
        return {"axis": "vertical", "x": 0, "y": y}
    if x == width - 1:
        return {"axis": "vertical", "x": width, "y": y}
    raise ValueError(f"entrance cell is not on the perimeter: {cell}")


def inward_yaw(cell: list[int], width: int, height: int) -> int:
    x, y = cell
    if y == 0:
        return 0
    if y == height - 1:
        return 2
    if x == 0:
        return 1
    if x == width - 1:
        return 3
    raise ValueError(f"spawn cell is not on the perimeter: {cell}")


def edge_state_from_cell(
    cell: list[int],
    yaw_quarter_turns: int,
    vertical: list[list[int]],
    horizontal: list[list[int]],
) -> int:
    x, y = cell
    if yaw_quarter_turns == 0:  # +Y
        return horizontal[x][y + 1]
    if yaw_quarter_turns == 1:  # +X
        return vertical[x + 1][y]
    if yaw_quarter_turns == 2:  # -Y
        return horizontal[x][y]
    if yaw_quarter_turns == 3:  # -X
        return vertical[x][y]
    raise ValueError(f"invalid yaw quarter turns: {yaw_quarter_turns}")


def straight_clearance(
    cell: list[int],
    yaw_quarter_turns: int,
    width: int,
    height: int,
    vertical: list[list[int]],
    horizontal: list[list[int]],
) -> int:
    deltas = ((0, 1), (1, 0), (0, -1), (-1, 0))
    x, y = cell
    clearance = 0
    while edge_state_from_cell([x, y], yaw_quarter_turns, vertical, horizontal) == 0:
        delta_x, delta_y = deltas[yaw_quarter_turns]
        x += delta_x
        y += delta_y
        if x < 0 or x >= width or y < 0 or y >= height:
            break
        clearance += 1
    return clearance


def spawn_yaw(
    cell: list[int],
    width: int,
    height: int,
    vertical: list[list[int]],
    horizontal: list[list[int]],
) -> int:
    inward = inward_yaw(cell, width, height)
    candidates = (inward, (inward + 1) % 4, (inward + 3) % 4)
    ranked = [
        (
            straight_clearance(cell, yaw, width, height, vertical, horizontal),
            -order,
            yaw,
        )
        for order, yaw in enumerate(candidates)
    ]
    clearance, _, yaw = max(ranked)
    if clearance == 0:
        raise ValueError(f"spawn cell has no traversable inward edge: {cell}")
    return yaw


def canonical_document(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": document["schemaVersion"],
        "topologyId": document["topologyId"],
        "dimensions": {
            key: document["dimensions"][key]
            for key in ("widthCells", "heightCells", "cellPitchMm", "wallThicknessMm", "wallHeightMm")
        },
        "openings": [
            {
                "openingId": item["openingId"],
                "edge": {
                    "axis": item["edge"]["axis"],
                    "x": item["edge"]["x"],
                    "y": item["edge"]["y"],
                },
            }
            for item in sorted(document["openings"], key=lambda value: value["openingId"])
        ],
        "walls": [
            {
                "wallId": wall["wallId"],
                "pivotId": wall.get("pivotId"),
                "initialStateId": wall["initialStateId"],
                "states": [
                    {
                        "stateId": state["stateId"],
                        "edge": {
                            "axis": state["edge"]["axis"],
                            "x": state["edge"]["x"],
                            "y": state["edge"]["y"],
                        },
                        "quarterTurns": state["quarterTurns"],
                    }
                    for state in sorted(wall["states"], key=lambda value: value["stateId"])
                ],
            }
            for wall in sorted(document["walls"], key=lambda value: value["wallId"])
        ],
        "pivots": [
            {
                "pivotId": pivot["pivotId"],
                "node": {"x": pivot["node"]["x"], "y": pivot["node"]["y"]},
                "wallIds": sorted(pivot["wallIds"]),
            }
            for pivot in sorted(document["pivots"], key=lambda value: value["pivotId"])
        ],
        "spawns": [
            {
                "spawnId": spawn["spawnId"],
                "cell": {"x": spawn["cell"]["x"], "y": spawn["cell"]["y"]},
                "yawQuarterTurns": spawn["yawQuarterTurns"],
            }
            for spawn in sorted(document["spawns"], key=lambda value: value["spawnId"])
        ],
    }


def checksum(document: dict[str, Any]) -> str:
    canonical = json.dumps(
        canonical_document(document),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def migrate(legacy: dict[str, Any]) -> dict[str, Any]:
    legacy = require_mapping(legacy, "$")
    meta = require_mapping(legacy.get("meta"), "$.meta")
    width = require_int(meta.get("width"), "$.meta.width", 1, MAXIMUM_GRID_SIDE)
    height = require_int(meta.get("height"), "$.meta.height", 1, MAXIMUM_GRID_SIDE)
    vertical = require_list(legacy.get("vwalls"), "$.vwalls")
    horizontal = require_list(legacy.get("hwalls"), "$.hwalls")
    if len(vertical) != width + 1 or any(not isinstance(column, list) or len(column) != height for column in vertical):
        raise ValueError("legacy vwalls dimensions are invalid")
    if len(horizontal) != width or any(not isinstance(column, list) or len(column) != height + 1 for column in horizontal):
        raise ValueError("legacy hwalls dimensions are invalid")
    for grid_name, grid in (("vwalls", vertical), ("hwalls", horizontal)):
        for x, column in enumerate(grid):
            for y, state in enumerate(column):
                require_int(state, f"$.{grid_name}[{x}][{y}]", 0, 2)

    pivot_edges: dict[tuple[str, int, int], tuple[int, str]] = {}
    pivots = []
    pivot_nodes: set[tuple[int, int]] = set()
    for pivot_index, raw_pivot in enumerate(require_list(legacy.get("pivots"), "$.pivots")):
        pivot_path = f"$.pivots[{pivot_index}]"
        legacy_pivot = require_mapping(raw_pivot, pivot_path)
        node = require_pair(legacy_pivot.get("node"), pivot_path + ".node", width, height)
        node_key = (node[0], node[1])
        if node_key in pivot_nodes:
            raise ValueError(f"duplicate pivot node: {node_key}")
        pivot_nodes.add(node_key)
        orientation = require_int(legacy_pivot.get("orientation", 0), pivot_path + ".orientation", 0, 3)
        if orientation != 0:
            raise ValueError("migration expects legacy pivots at orientation 0")
        pivot_id = 10000 + node[1] * (width + 1) + node[0] + 1
        wall_ids = []
        arms = require_list(legacy_pivot.get("arms"), pivot_path + ".arms")
        if not 1 <= len(arms) <= 4:
            raise ValueError(f"{pivot_path}.arms must contain 1..4 directions")
        for arm_index, direction in enumerate(arms):
            if not isinstance(direction, str) or direction not in DIRECTIONS:
                raise ValueError(f"{pivot_path}.arms[{arm_index}] is not a known direction")
        if len(arms) != len(set(arms)):
            raise ValueError(f"{pivot_path}.arms must contain unique directions")
        for direction in arms:
            edge = edge_for_direction(node, direction)
            if not edge_is_in_bounds(edge, width, height):
                raise ValueError(f"pivot arm leaves the grid: {node} {direction}")
            key = (edge["axis"], edge["x"], edge["y"])
            if key in pivot_edges:
                raise ValueError(f"pivot edge assigned twice: {key}")
            grid = vertical if edge["axis"] == "vertical" else horizontal
            if grid[edge["x"]][edge["y"]] != 2:
                raise ValueError(f"pivot arm does not match state 2 edge: {key}")
            pivot_edges[key] = (pivot_id, direction)
            wall_ids.append(1 + edge_index(*key, width, height))
        pivots.append(
            {
                "pivotId": pivot_id,
                "node": {"x": node[0], "y": node[1]},
                "wallIds": sorted(wall_ids),
            }
        )

    walls = []
    consumed_pivot_edges = set()
    for axis, grid in (("vertical", vertical), ("horizontal", horizontal)):
        for x, column in enumerate(grid):
            for y, state in enumerate(column):
                if state == 0:
                    continue
                key = (axis, x, y)
                wall_id = 1 + edge_index(axis, x, y, width, height)
                if state == 1:
                    walls.append(
                        {
                            "wallId": wall_id,
                            "initialStateId": 0,
                            "states": [
                                {
                                    "stateId": 0,
                                    "edge": {"axis": axis, "x": x, "y": y},
                                    "quarterTurns": 0,
                                }
                            ],
                        }
                    )
                    continue
                if key not in pivot_edges:
                    raise ValueError(f"state 2 edge has no pivot arm: {key}")
                consumed_pivot_edges.add(key)
                pivot_id, home_direction = pivot_edges[key]
                node = next(pivot["node"] for pivot in pivots if pivot["pivotId"] == pivot_id)
                node_pair = [node["x"], node["y"]]
                walls.append(
                    {
                        "wallId": wall_id,
                        "pivotId": pivot_id,
                        "initialStateId": 0,
                        "states": [
                            {
                                "stateId": quarter_turns,
                                "edge": edge_for_direction(node_pair, rotate(home_direction, quarter_turns)),
                                "quarterTurns": quarter_turns,
                            }
                            for quarter_turns in range(4)
                        ],
                    }
                )
    if consumed_pivot_edges != set(pivot_edges):
        raise ValueError("one or more declared pivot arms were not migrated")

    openings = []
    spawns = []
    entrance_cells: set[tuple[int, int]] = set()
    entrance_edges: set[tuple[str, int, int]] = set()
    for entrance_index, raw_cell in enumerate(require_list(legacy.get("entrances"), "$.entrances")):
        cell = require_pair(
            raw_cell,
            f"$.entrances[{entrance_index}]",
            width - 1,
            height - 1,
        )
        cell_key = (cell[0], cell[1])
        if cell_key in entrance_cells:
            raise ValueError(f"duplicate entrance cell: {cell}")
        entrance_cells.add(cell_key)
        edge = boundary_edge(cell, width, height)
        edge_key = (edge["axis"], edge["x"], edge["y"])
        if edge_key in entrance_edges:
            raise ValueError(f"duplicate entrance edge: {edge_key}")
        entrance_edges.add(edge_key)
        grid = vertical if edge["axis"] == "vertical" else horizontal
        if grid[edge["x"]][edge["y"]] != 0:
            raise ValueError(f"entrance is blocked in legacy topology: {cell}")
        index = edge_index(edge["axis"], edge["x"], edge["y"], width, height)
        openings.append({"openingId": 20000 + index + 1, "edge": edge})
        spawns.append(
            {
                "spawnId": 30000 + cell[1] * width + cell[0] + 1,
                "cell": {"x": cell[0], "y": cell[1]},
                "yawQuarterTurns": spawn_yaw(cell, width, height, vertical, horizontal),
            }
        )

    result = {
        "schemaVersion": 1,
        "topologyId": "maze-16x16-v1",
        "dimensions": {
            "widthCells": width,
            "heightCells": height,
            "cellPitchMm": 2750,
            "wallThicknessMm": 250,
            "wallHeightMm": 3000,
        },
        "openings": sorted(openings, key=lambda value: value["openingId"]),
        "walls": sorted(walls, key=lambda value: value["wallId"]),
        "pivots": sorted(pivots, key=lambda value: value["pivotId"]),
        "spawns": sorted(spawns, key=lambda value: value["spawnId"]),
    }
    result["checksum"] = checksum(result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="fail if output differs; do not rewrite")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    legacy = json.loads(
        args.source.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_members,
    )
    result = migrate(legacy)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != serialized:
            raise SystemExit("TOPOLOGY MIGRATION DRIFT: regenerate MazeTopology16x16.v1.json")
        print(f"Topology migration is reproducible: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(
        f"Migrated {len(result['walls'])} walls, {len(result['pivots'])} pivots, "
        f"{len(result['openings'])} openings and {len(result['spawns'])} spawns -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
