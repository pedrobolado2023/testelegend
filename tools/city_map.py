#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import shutil
import zlib

from PIL import Image, ImageDraw

import amf3

ROOT = pathlib.Path(__file__).resolve().parent.parent
CELL = 20
TILE = 300


def land(map_id: int) -> pathlib.Path:
    return ROOT / "raw/mapmaterial/land" / str(map_id)


def grid_size(map_id: int) -> tuple[int, int]:
    keys = [tuple(map(int, p.stem[5:].split("_"))) for p in land(map_id).glob("tile_*.jpg")]
    return max(c for c, _ in keys) + 1, max(r for _, r in keys) + 1


def walkable(map_id: int) -> set[tuple[int, int]]:
    data = amf3.read_all(zlib.decompress((ROOT / f"raw/maps/{map_id}/{map_id}.titles").read_bytes()))[0]
    return {tuple(map(int, k.split("_"))) for k, v in data.items() if v}


def sync_manifest(map_id: int) -> None:
    path = ROOT / "index/res_md5.raw"
    xml = zlib.decompress(zlib.decompress(path.read_bytes())).decode("utf-8")
    prefix = f"mapmaterial\\land\\{map_id}\\"
    n = 0
    for f in land(map_id).glob("*.jpg"):
        data = f.read_bytes()
        name = re.escape(prefix + f.name)
        xml, k = re.subn(rf'(<Item name="{name}" md5=")[0-9a-f]+(" size=")\d+(")',
                         rf"\g<1>{hashlib.md5(data).hexdigest()[:8]}\g<2>{len(data)}\g<3>", xml)
        n += k
    path.write_bytes(zlib.compress(zlib.compress(xml.encode("utf-8"), 9), 9))
    print(f"manifest: {n} entries updated")


def export(map_id: int, out: pathlib.Path) -> None:
    cols, rows = grid_size(map_id)
    full = Image.new("RGB", (cols * TILE, rows * TILE))
    for c in range(cols):
        for r in range(rows):
            full.paste(Image.open(land(map_id) / f"tile_{c}_{r}.jpg"), (c * TILE, r * TILE))
    out.mkdir(parents=True, exist_ok=True)
    full.save(out / f"{map_id}_full.png")
    half = full.resize((full.width // 2, full.height // 2), Image.LANCZOS)
    half.save(out / f"{map_id}_half.jpg", quality=90)
    mask = Image.new("L", full.size, 0)
    draw = ImageDraw.Draw(mask)
    for gx, gy in walkable(map_id):
        draw.rectangle((gx * CELL, gy * CELL, gx * CELL + CELL - 1, gy * CELL + CELL - 1), fill=255)
    mask.save(out / f"{map_id}_walk_mask.png")
    tint = Image.new("RGB", full.size, (0, 255, 90))
    overlay = Image.composite(Image.blend(full, tint, 0.45), full, mask)
    overlay.resize(half.size, Image.LANCZOS).save(out / f"{map_id}_walk_overlay.jpg", quality=90)
    print(f"{cols}x{rows} tiles, {full.width}x{full.height} px, {len(walkable(map_id))} walkable cells -> {out}")


def apply(map_id: int, image: pathlib.Path) -> None:
    cols, rows = grid_size(map_id)
    size = (cols * TILE, rows * TILE)
    src = Image.open(image).convert("RGB")
    if abs(src.width / src.height - size[0] / size[1]) > 0.01:
        raise SystemExit(f"aspect ratio must be {size[0]}:{size[1]}, got {src.width}x{src.height}")
    src = src.resize(size, Image.LANCZOS)
    backup = land(map_id).with_name(f"{map_id}_original")
    if not backup.exists():
        shutil.copytree(land(map_id), backup)
    for c in range(cols):
        for r in range(rows):
            src.crop((c * TILE, r * TILE, (c + 1) * TILE, (r + 1) * TILE)).save(
                land(map_id) / f"tile_{c}_{r}.jpg", quality=88)
    small = Image.open(land(map_id) / "small.jpg").size
    src.resize(small, Image.LANCZOS).save(land(map_id) / "small.jpg", quality=88)
    sync_manifest(map_id)
    print(f"applied {image} to map {map_id} ({cols * rows} tiles), original kept in {backup}")


def restore(map_id: int) -> None:
    backup = land(map_id).with_name(f"{map_id}_original")
    for p in backup.iterdir():
        shutil.copy2(p, land(map_id) / p.name)
    sync_manifest(map_id)
    print(f"restored map {map_id} from {backup}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["export", "apply", "restore"])
    ap.add_argument("image", nargs="?")
    ap.add_argument("--map", type=int, default=10000)
    ap.add_argument("--out", default=str(ROOT / "build/city"))
    a = ap.parse_args()
    if a.cmd == "export":
        export(a.map, pathlib.Path(a.out))
    elif a.cmd == "apply":
        apply(a.map, pathlib.Path(a.image))
    else:
        restore(a.map)


if __name__ == "__main__":
    main()
