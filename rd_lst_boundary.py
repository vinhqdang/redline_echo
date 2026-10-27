"""
Regression discontinuity in summer land-surface temperature (Landsat 8/9, 30 m, via the
Microsoft Planetary Computer's anonymous STAC API) at the boundaries between adjacent HOLC grades.

For each HOLC city: sample points every STEP metres inside graded areas, compute the signed
distance to the nearest boundary between two adjacent grades (positive on the worse-graded side),
read mean summer land-surface temperature, and estimate a local-linear RD jump with a triangular
kernel. Also reports placebo jumps at fake cutoffs and bandwidth sensitivity.

Usage:  python rd_lst_boundary.py            # all eligible cities, 4 workers, resumable
        python rd_lst_boundary.py Chicago IL # one city
Results are appended to rd_results.csv (one row per city x boundary pair x bandwidth).
"""
import json
import os
import sys
import warnings
from multiprocessing import Pool

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

HOLC_PATH = os.path.join("data", "holc_crosswalk.geojson")
OUT = "rd_results.csv"   # outcome in {lst, ndvi, elev}; ndvi/elev are covariate-balance checks
STEP = 60
MAX_BW = 600
BANDWIDTHS = (200, 400, 600)
PAIRS = {"AB": ("A", "B"), "BC": ("B", "C"), "CD": ("C", "D")}
MIN_AREAS = 40


def load_city_index():
    d = json.load(open(HOLC_PATH))
    counts = {}
    for f in d["features"]:
        p = f["properties"]
        if p.get("grade") in ("A", "B", "C", "D"):
            counts.setdefault((p["city"], p["state"]), set()).add(p["area_id"])
    return d, sorted(k for k, v in counts.items() if len(v) >= MIN_AREAS)


def polygonal(geom):
    import shapely
    from shapely.geometry import MultiPolygon, Polygon
    parts = [p for p in shapely.get_parts(geom) if isinstance(p, Polygon) and not p.is_empty]
    return MultiPolygon(parts) if parts else Polygon()


def rd_fit(g, bw, cutoff=0.0, side=None, y="lst"):
    import statsmodels.formula.api as smf
    g = g[np.abs(g.dist - cutoff) <= bw]
    if side == "worse":
        g = g[g.dist > 0]
    elif side == "better":
        g = g[g.dist < 0]
    g = g.assign(t=(g.dist > cutoff).astype(int), r=g.dist - cutoff, w=1 - np.abs(g.dist - cutoff) / bw)
    if g.t.nunique() < 2 or len(g) < 200:
        return None
    cl = (g.x // 300).astype(int) * 100000 + (g.y // 300).astype(int)
    m = smf.wls(f"{y} ~ t + r + t:r", g, weights=g.w).fit(cov_type="cluster", cov_kwds={"groups": cl})
    return m.params["t"], m.bse["t"], len(g)


def run_city(args):
    city, state = args
    try:
        import planetary_computer as pc
        import pystac_client
        import rasterio
        from pyproj import Transformer
        from shapely import contains_xy, distance, points as mkpts
        from shapely.geometry import shape
        from shapely.ops import unary_union
        from shapely.validation import make_valid
        import shapely

        data = json.load(open(HOLC_PATH))
        polys = {}
        for f in data["features"]:
            p = f["properties"]
            if p["city"] == city and p["state"] == state and p.get("grade") in ("A", "B", "C", "D"):
                polys.setdefault((p["area_id"], p["grade"]), []).append(make_valid(shape(f["geometry"])))
        areas = [(g, polygonal(unary_union(ps))) for (_, g), ps in polys.items()]
        areas = [(g, a) for g, a in areas if not a.is_empty]
        allu = unary_union([a for _, a in areas])
        lon0, lat0 = allu.centroid.coords[0]
        crs = f"EPSG:{(32600 if lat0 >= 0 else 32700) + int((lon0 + 180) // 6) + 1}"
        fwd = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        areas = [(g, shapely.transform(a, lambda c: np.column_stack(fwd.transform(c[:, 0], c[:, 1])))) for g, a in areas]
        gu = {g: polygonal(unary_union([a for gg, a in areas if gg == g])) for g in "ABCD"}
        ext = unary_union([a for _, a in areas]).bounds

        xs, ys = np.arange(ext[0], ext[2], STEP), np.arange(ext[1], ext[3], STEP)
        gx, gy = np.meshgrid(xs, ys)
        pts = pd.DataFrame({"x": gx.ravel(), "y": gy.ravel()})
        grade = np.full(len(pts), "", dtype=object)
        for g in "ABCD":
            grade[contains_xy(gu[g], pts.x.values, pts.y.values)] = g
        pts["grade"] = grade
        pts = pts[pts.grade != ""]

        frames = []
        for name, (better, worse) in PAIRS.items():
            meet = gu[better].buffer(10).intersection(gu[worse].buffer(10))
            if meet.is_empty:
                continue
            seg = gu[better].boundary.intersection(meet)
            if seg.is_empty:
                continue
            sub = pts[pts.grade.isin([better, worse])].copy()
            dist = distance(mkpts(sub.x.values, sub.y.values), seg)
            sub["dist"] = np.where(sub.grade == worse, dist, -dist)
            sub["pair"] = name
            frames.append(sub[np.abs(sub.dist) <= MAX_BW])
        if not frames:
            return []
        rd = pd.concat(frames)

        back = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
        bb = back.transform_bounds(*ext)
        cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)
        items = list(cat.search(collections=["landsat-c2-l2"], bbox=bb, datetime="2019-06-01/2022-08-31",
                                query={"eo:cloud_cover": {"lt": 15}, "platform": {"in": ["landsat-8", "landsat-9"]}}).items())
        items = [i for i in items if i.properties["datetime"][5:7] in ("06", "07", "08")]
        if not items:
            return []
        tiles = {}
        for i in items:
            tiles.setdefault((i.properties["landsat:wrs_path"], i.properties["landsat:wrs_row"]), []).append(i)

        uxy = rd[["x", "y"]].drop_duplicates().reset_index(drop=True)

        def read(href, scale, offset, fill=0):
            with rasterio.open(href) as ds:
                tx = Transformer.from_crs(crs, ds.crs, always_xy=True)
                px, py = tx.transform(uxy.x.values, uxy.y.values)
                v = np.array([q[0] for q in ds.sample(zip(px, py))], dtype=float)
            return np.where(v == fill, np.nan, v * scale + offset)

        lst = np.full(len(uxy), np.nan)
        ndvi = np.full(len(uxy), np.nan)
        for grp in tiles.values():
            lv, nv = [], []
            for it in sorted(grp, key=lambda i: i.properties["eo:cloud_cover"])[:3]:
                lv.append(read(it.assets["lwir11"].href, 0.00341802, 149.0 - 273.15))
                red = read(it.assets["red"].href, 0.0000275, -0.2)
                nir = read(it.assets["nir08"].href, 0.0000275, -0.2)
                nv.append((nir - red) / (nir + red))
            lst = np.where(np.isnan(lst), np.nanmean(np.vstack(lv), axis=0), lst)
            ndvi = np.where(np.isnan(ndvi), np.nanmean(np.vstack(nv), axis=0), ndvi)
        uxy["lst"], uxy["ndvi"] = lst, ndvi

        elev = np.full(len(uxy), np.nan)
        for it in cat.search(collections=["cop-dem-glo-30"], bbox=bb).items():
            elev = np.where(np.isnan(elev), read(it.assets["data"].href, 1.0, 0.0, fill=-32767), elev)
        uxy["elev"] = elev
        rd = rd.merge(uxy, on=["x", "y"]).dropna(subset=["lst"])
        rd = rd[(rd.lst > 5) & (rd.lst < 65) & rd.ndvi.between(-1, 1)]

        rows = []
        for pair, g in [("all", rd)] + list(rd.groupby("pair")):
            for yv in ("lst", "ndvi", "elev"):
                for bw in BANDWIDTHS:
                    r = rd_fit(g, bw, y=yv)
                    if r:
                        rows.append(dict(city=city, state=state, pair=pair, bw=bw, kind="rd", outcome=yv, est=r[0], se=r[1], n=r[2]))
            for kind, cutoff, side in (("placebo_worse", 200.0, "worse"), ("placebo_better", -200.0, "better")):
                r = rd_fit(g, 200, cutoff, side)
                if r:
                    rows.append(dict(city=city, state=state, pair=pair, bw=200, kind=kind, outcome="lst", est=r[0], se=r[1], n=r[2]))
        return rows
    except Exception as e:  # keep the batch going; the failure is recorded
        return [dict(city=city, state=state, pair="ERR", bw=0, kind=f"{type(e).__name__}: {str(e)[:80]}", outcome="", est=np.nan, se=np.nan, n=0)]


if __name__ == "__main__":
    _, cities = load_city_index()
    if len(sys.argv) == 3:
        cities = [(sys.argv[1], sys.argv[2])]
    done = set()
    if os.path.exists(OUT):
        prev = pd.read_csv(OUT)
        done = set(zip(prev.city, prev.state))
    todo = [c for c in cities if c not in done]
    print(f"{len(cities)} eligible cities, {len(todo)} to run", flush=True)
    with Pool(4) as pool:
        for k, rows in enumerate(pool.imap_unordered(run_city, todo), 1):
            if rows:
                pd.DataFrame(rows).to_csv(OUT, mode="a", header=not os.path.exists(OUT), index=False)
            print(f"[{k}/{len(todo)}] {rows[0]['city'] if rows else '(no rows)'}", flush=True)
