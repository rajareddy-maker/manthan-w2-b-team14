"""Render docs/demo/gridpulse_explainer_v2.mp4 — the 13-scene animated explainer (storyboard_v2.md).

Local toolchain only: Pillow + numpy draw every frame (kinetic type, animated charts, a
step-by-step architecture flow, camera moves over the real dashboard screenshots), ffmpeg
encodes, and the offline Windows voice (Zira, Rate 1) reads the narration. Scene lengths are
the measured length of each narration clip, so picture and voice stay in sync.

Usage (repo root, Windows):  FFMPEG=<path to ffmpeg.exe> python docs/demo/build_video_v2.py
Env: SHOTS (annotated screenshots dir, default ~/Downloads/GridPulse_screenshots).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

DEMO = Path(__file__).resolve().parent
WORK = DEMO / "_build_v2"
FRAMES = DEMO / "frames"
SHOTS = Path(os.environ.get("SHOTS", Path.home() / "Downloads" / "GridPulse_screenshots"))
FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
W, H, FPS = 1920, 1080, 30
PAUSE = 0.7
FADE = 0.35

NAVY, CYAN, AMBER, ORANGE = (11, 18, 32), (34, 211, 238), (255, 213, 79), (255, 140, 0)
WHITE, MUTED, GREEN, CARD, LINE = (
    (241, 245, 249),
    (148, 163, 184),
    (74, 222, 128),
    (21, 31, 52),
    (51, 65, 85),
)
FD = Path("C:/Windows/Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FD / name), size)


F = {
    k: font(*v)
    for k, v in {
        "hero": ("seguibl.ttf", 150),
        "h1": ("segoeuib.ttf", 64),
        "h2": ("seguisb.ttf", 44),
        "h3": ("seguisb.ttf", 34),
        "body": ("segoeui.ttf", 30),
        "small": ("segoeui.ttf", 24),
        "label": ("seguisb.ttf", 22),
        "big": ("seguibl.ttf", 84),
        "mid": ("seguibl.ttf", 60),
    }.items()
}


# ----------------------------------------------------------------------------------- helpers
def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ramp(t: float, start: float, dur: float = 0.6) -> float:
    return ease((t - start) / dur) if dur > 0 else float(t >= start)


def background() -> Image.Image:
    """Navy canvas with a soft cinematic vignette and a faint cyan glow."""
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W * 0.5) / W) ** 2 + ((y - H * 0.45) / H) ** 2)
    v = np.clip(1.15 - d * 1.4, 0.55, 1.0)[..., None]
    glow = np.exp(-(((x - W * 0.78) / 520) ** 2 + ((y - H * 0.18) / 360) ** 2))[..., None]
    base = np.array(NAVY, dtype=np.float32) * v + np.array((10, 60, 80), np.float32) * glow * 0.6
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


BG = background()


def text(d: ImageDraw.ImageDraw, xy, s, f, fill=WHITE, a=1.0, anchor="la"):
    if a <= 0.01:
        return
    r, g, b = fill
    d.text(xy, s, font=F[f], fill=(r, g, b, int(255 * a)), anchor=anchor)


def header(d, label: str, title: str, t: float):
    a = ramp(t, 0.0, 0.5)
    text(d, (96, 64), label.upper(), "label", ORANGE, a)
    text(d, (96 - int(30 * (1 - a)), 96), title, "h1", WHITE, a)


def card(d, box, a=1.0, outline=LINE, fill=CARD):
    if a <= 0.01:
        return
    x0, y0, x1, y1 = box
    d.rounded_rectangle(
        box, radius=22, fill=fill + (int(235 * a),), outline=outline + (int(255 * a),), width=2
    )


def hbar(d, x, y, w_full, h, frac, color, a=1.0):
    d.rounded_rectangle((x, y, x + w_full, y + h), radius=h // 2, fill=(30, 41, 59, int(255 * a)))
    if frac > 0.002:
        d.rounded_rectangle(
            (x, y, x + max(h, int(w_full * frac)), y + h),
            radius=h // 2,
            fill=color + (int(255 * a),),
        )


def fmt_int(n: float) -> str:
    return f"{int(round(n)):,}"


def canvas():
    img = BG.copy().convert("RGBA")
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return img, over, ImageDraw.Draw(over)


def compose(img, over):
    return Image.alpha_composite(img, over).convert("RGB")


# ------------------------------------------------------------------------------- scenes
def s_title(t, dur):
    img, over, d = canvas()
    n = 480000 * ease(t / 2.4)
    a1 = ramp(t, 0.1) * (1 - ramp(t, dur * 0.42, 0.5))
    text(d, (W // 2, 430), fmt_int(n), "hero", CYAN, a1, "mm")
    text(d, (W // 2, 560), "readings a day.", "h2", WHITE, a1, "mm")
    a2 = ramp(t, dur * 0.25) * (1 - ramp(t, dur * 0.42, 0.5))
    text(d, (W // 2, 660), "Can you bill from them?", "h2", AMBER, a2, "mm")
    a3 = ramp(t, dur * 0.43, 0.7)
    text(d, (W // 2, 470 - int(20 * (1 - a3))), "GridPulse", "hero", WHITE, a3, "mm")
    text(
        d,
        (W // 2, 600),
        "Smart-meter telemetry → billing-ready kWh and anomaly flags",
        "h3",
        CYAN,
        a3,
        "mm",
    )
    text(d, (W // 2, 670), "Team 14 · Track B · NucleusTeq Indore", "body", MUTED, a3, "mm")
    return compose(img, over)


PROBLEM = [
    ("3 teams", "Who is affected", "Billing, network operations, revenue protection"),
    ("1000×", "Unit errors", "Wh next to kWh; late and duplicated events"),
    ("After complaints", "Tamper & outages found", "Gaps silently filled; issues surface late"),
    ("480k / day", "Readings to trust", "5,000 meters × 96 · 3.39M in the demo week"),
]


def s_problem(t, dur):
    img, over, d = canvas()
    header(d, "The problem", "Meter data nobody can bill from", t)
    for i, (big, lab, desc) in enumerate(PROBLEM):
        a = ramp(t, 0.8 + i * dur * 0.2, 0.6)
        cx, cy = 96 + (i % 2) * 880, 250 + (i // 2) * 370
        off = int(60 * (1 - a))
        card(d, (cx + off, cy, cx + 840 + off, cy + 320), a)
        text(d, (cx + 50 + off, cy + 40), big, "big", ORANGE if i != 3 else CYAN, a)
        text(d, (cx + 50 + off, cy + 160), lab, "h3", WHITE, a)
        text(d, (cx + 50 + off, cy + 215), desc, "body", MUTED, a)
    return compose(img, over)


GOALS = [
    ("G1 Trustworthy consumption", "Σ hourly = Σ register deltas (dbt test PASS)"),
    ("G2 Billing-ready monthly table", "5,000 rows = all 5,000 meters"),
    ("G3 Transparent gaps", "99.47% complete · 17,823 gaps marked, none filled"),
    ("G4 Early anomaly detection", "5/5 spike · 3/3 tamper · 1/1 outage · 0 false +"),
    ("G5 Reliable operations", "7-day backfill in 174 s · lag p50 35 / p95 59 min"),
    ("G6 Fast onboarding", "One command: 658 s end to end"),
]


def s_goals(t, dur):
    img, over, d = canvas()
    header(d, "Goals & KPIs", "Six goals, each with a measured result", t)
    for i, (g, r) in enumerate(GOALS):
        start = 1.2 + i * (dur - 3.0) / 6
        a = ramp(t, start, 0.5)
        y = 250 + i * 128
        card(d, (96, y, W - 96, y + 108), 0.35 + 0.65 * a)
        cx = 160
        d.ellipse(
            (cx - 30, y + 24, cx + 30, y + 84),
            outline=GREEN + (255,),
            width=4,
            fill=(20, 60, 40, int(255 * a)),
        )
        if a > 0.05:
            k = ease(a)
            pts = [(cx - 14, y + 54), (cx - 3, y + 54 + 11 * k), (cx + 15, y + 40 - 6 * k)]
            d.line(pts, fill=GREEN + (int(255 * a),), width=7, joint="curve")
        text(d, (220, y + 32), g, "h3", WHITE, 0.55 + 0.45 * a)
        text(d, (900 + int(40 * (1 - a)), y + 36), r, "body", CYAN, a)
    return compose(img, over)


def s_options(t, dur):
    img, over, d = canvas()
    header(d, "Solution options", "Batch lakehouse won 4.70 to 3.45", t)
    rows = [
        ("A  Batch lakehouse (files · DuckDB · dbt)", 4.70, CYAN),
        ("B  Streaming (Kafka)", 3.45, MUTED),
        ("C  Spark lakehouse", 2.80, MUTED),
    ]
    dim = ramp(t, dur * 0.55, 0.8)
    for i, (lab, v, col) in enumerate(rows):
        y = 320 + i * 190
        a = 1.0 if i == 0 else 1 - 0.55 * dim
        text(d, (120, y), lab, "h3", WHITE, a)
        hbar(d, 120, y + 60, 1380, 56, (v / 5) * ease((t - 0.8 - i * 0.3) / 1.8), col, a)
        if t > 2.6 + i * 0.3:
            text(d, (1530, y + 88), f"{v:.2f}", "mid", col if i == 0 else WHITE, a, "lm")
    a = ramp(t, dur * 0.55, 0.6)
    text(
        d,
        (120, 890),
        "Daily SLA · ~100 MB/day · 14 GB laptop → Kafka and Spark add cost, not value (ADR-002)",
        "body",
        AMBER,
        a,
    )
    return compose(img, over)


ARCH = [
    ("Gateways", "JSONL v1+v2"),
    ("Landing", "by arrival"),
    ("Bronze", "Parquet, raw"),
    ("Silver", "kWh · IST"),
    ("Gold", "marts"),
    ("GX gate", "silver+gold"),
    ("Postgres", "marts · ops"),
    ("Superset", "dashboard"),
]


def s_arch(t, dur):
    img, over, d = canvas()
    header(d, "Architecture", "Landing → bronze → silver → gold → BI", t)
    n = len(ARCH)
    bw, gap, y = 190, 28, 360
    x0 = (W - (n * bw + (n - 1) * gap)) // 2
    for i, (name, sub) in enumerate(ARCH):
        a = ramp(t, 1.0 + i * dur * 0.07, 0.5)
        x = x0 + i * (bw + gap)
        hl = (
            CYAN if name in ("Bronze", "Silver", "Gold") else (AMBER if name == "GX gate" else LINE)
        )
        card(d, (x, y, x + bw, y + 190), a, outline=hl)
        text(d, (x + bw // 2, y + 72), name, "h3", WHITE, a, "mm")
        text(d, (x + bw // 2, y + 130), sub, "small", MUTED, a, "mm")
        if i < n - 1 and a > 0.9:
            ax = x + bw + 2
            d.line((ax, y + 95, ax + gap - 6, y + 95), fill=CYAN + (255,), width=4)
            d.polygon(
                [(ax + gap - 8, y + 87), (ax + gap, y + 95), (ax + gap - 8, y + 103)],
                fill=CYAN + (255,),
            )
    a = ramp(t, dur * 0.62, 0.6)
    d.rounded_rectangle(
        (x0, 620, x0 + n * (bw + gap) - gap, 690),
        radius=18,
        outline=MUTED + (int(255 * a),),
        width=2,
    )
    text(
        d,
        (W // 2, 655),
        "Airflow 3.3.2 orchestrates daily + backfill · every write is an atomic swap",
        "body",
        WHITE,
        a,
        "mm",
    )
    b = ramp(t, dur * 0.25, 0.6)
    mb = 397 - (397 - 38) * ease((t - dur * 0.25) / 2.5)
    text(d, (x0 + 2 * (bw + gap) + bw // 2, 300), f"397 → {mb:.0f} MB", "h3", AMBER, b, "mm")
    chips = ["Airflow 3.3.2", "DuckDB 2.0.1 + dbt", "GX 1.25.0", "Postgres 16.16", "Superset 6.1.0"]
    c = ramp(t, dur * 0.78, 0.6)
    cx = 180
    for ch in chips:
        wch = int(d.textlength(ch, font=F["small"])) + 48
        d.rounded_rectangle(
            (cx, 790, cx + wch, 850),
            radius=30,
            fill=(30, 41, 59, int(255 * c)),
            outline=CYAN + (int(255 * c),),
            width=2,
        )
        text(d, (cx + wch // 2, 820), ch, "small", WHITE, c, "mm")
        cx += wch + 26
    text(d, (W // 2, 930), "Kafka and Spark dropped: ADR-002", "small", MUTED, c, "mm")
    return compose(img, over)


GRAIN = [
    ("15-min interval", "silver · int_meter_intervals", "3,360,000 rows"),
    ("Hour", "fct_consumption_hourly", "840,000 rows"),
    ("Day", "fct_consumption_daily", "35,000 rows"),
    ("IST month", "mart_billing_monthly", "5,000 rows"),
]


def s_model(t, dur):
    img, over, d = canvas()
    header(d, "Data model", "Facts by grain, seeds as dimensions", t)
    for i, (g, m, r) in enumerate(GRAIN):
        a = ramp(t, 0.8 + i * dur * 0.15, 0.5)
        x, y = 160 + i * 150, 260 + i * 150
        card(d, (x, y, x + 1000, y + 120), a, outline=CYAN)
        text(d, (x + 40, y + 28), g, "h3", WHITE, a)
        text(d, (x + 40, y + 74), m, "small", MUTED, a)
        text(d, (x + 960, y + 60), r, "h3", CYAN, a, "rm")
    a = ramp(t, dur * 0.7, 0.4)
    s = 1 + 0.25 * (1 - a)
    f = font("seguibl.ttf", int(54 * s))
    if a > 0.01:
        d.rounded_rectangle(
            (1240, 820, 1830, 960), radius=20, outline=AMBER + (int(255 * a),), width=5
        )
        d.text((1535, 890), "DECIMAL(18,4)", font=f, fill=AMBER + (int(255 * a),), anchor="mm")
        text(d, (1535, 990), "never FLOAT — these numbers become bills", "small", MUTED, a, "mm")
    return compose(img, over)


def load_shot(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


TASK_NAMES = ["ingest", "dbt build", "GX gates", "publish", "ops metrics", "retention"]


def s_pipeline(t, dur):
    img, over, d = canvas()
    header(d, "Pipeline & orchestration", "Six tasks, every night at 01:30 IST", t)
    n, bw, gap, y = 6, 240, 46, 300
    x0 = (W - (n * bw + (n - 1) * gap)) // 2
    subs = [
        "landing D-3..D+1",
        "84/84 nodes",
        "silver 6 · gold 5",
        "atomic swap",
        "runs + alerts",
        "30 days",
    ]
    for i, name in enumerate(TASK_NAMES):
        k = ramp(t, 1.2 + i * dur * 0.08, 0.45)
        x = x0 + i * (bw + gap)
        card(d, (x, y, x + bw, y + 170), 0.4 + 0.6 * k, outline=GREEN if k > 0.5 else LINE)
        text(d, (x + bw // 2, y + 66), name, "h3", WHITE, 0.4 + 0.6 * k, "mm")
        text(
            d,
            (x + bw // 2, y + 120),
            subs[i],
            "small",
            GREEN if k > 0.5 else MUTED,
            0.4 + 0.6 * k,
            "mm",
        )
        if i < n - 1:
            ax = x + bw + 4
            col = GREEN if k > 0.9 else LINE
            d.line((ax, y + 85, ax + gap - 10, y + 85), fill=col + (255,), width=5)
            d.polygon(
                [(ax + gap - 12, y + 76), (ax + gap - 2, y + 85), (ax + gap - 12, y + 94)],
                fill=col + (255,),
            )
    facts = [
        "2 retries × 2 min · DuckDB tasks share one slot (single writer)",
        "3-day lookback absorbs late files · backfill DAG for any date range",
        "GX gate fails → publish never runs → yesterday's numbers stay live",
    ]
    for i, f_ in enumerate(facts):
        k = ramp(t, dur * (0.45 + i * 0.1), 0.5)
        text(d, (x0, 560 + i * 70), "■  " + f_, "body", WHITE, k)
    k = ramp(t, dur * 0.78, 0.4)
    secs = 174 * ease((t - dur * 0.78) / 1.8)
    text(d, (1580, 880), f"{secs:.0f} s", "big", AMBER, k, "mm")
    text(d, (1580, 960), "7-day backfill", "small", MUTED, k, "mm")
    return compose(img, over)


def s_quality(t, dur):
    img, over, d = canvas()
    header(d, "Data quality", "Nothing disappears silently", t)
    terms = [
        ("3,392,136", "landed in bronze", WHITE),
        ("=", "", MUTED),
        ("3,347,177", "kept", CYAN),
        ("+", "", MUTED),
        ("43,439", "duplicates", AMBER),
        ("+", "", MUTED),
        ("1,520", "quarantined", ORANGE),
    ]
    x = 150
    for i, (v, lab, col) in enumerate(terms):
        a = ramp(t, 0.8 + i * 0.45, 0.4)
        f = "mid" if lab else "big"
        wv = d.textlength(v, font=F[f])
        text(d, (x, 330), v, f, col, a)
        if lab:
            text(d, (x, 420), lab, "small", MUTED, a)
        x += int(wv) + 46
    half = dur * 0.5
    a = ramp(t, half, 0.5)
    text(d, (150, 560), "Spike rule, measured before shipping (ADR-006)", "h3", WHITE, a)
    rows = [
        ("z > 3 alone", 34932, "34,932 intervals · 4,998 meters", ORANGE),
        ("z > 3 + 8× guard", 10, "10 intervals · the 5 real spike meters", GREEN),
    ]
    for i, (lab, v, desc, col) in enumerate(rows):
        y = 640 + i * 150
        k = ramp(t, half + 0.5 + i * 0.8, 0.5)
        text(d, (150, y), lab, "body", WHITE, k)
        hbar(d, 520, y, 1100, 48, (v / 34932) * ease((t - half - 0.6 - i * 0.8) / 1.5), col, k)
        text(d, (520, y + 64), desc, "small", MUTED, k)
    return compose(img, over)


# ---- camera tours over annotated screenshots
def shot_canvas(path: Path) -> Image.Image:
    im = load_shot(path)
    cw, ch = im.width, int(im.width * 9 / 16)
    if ch < im.height:
        ch = im.height
        cw = int(ch * 16 / 9)
    c = Image.new("RGB", (cw, ch), NAVY)
    c.paste(im, ((cw - im.width) // 2, (ch - im.height) // 2))
    return c


def tour(canvas_img: Image.Image, keys, t, dur, ox=0, oy=0):
    """keys: list of (x0,y0,x1,y1) in screenshot coords; first = full view. Ease between them."""
    cw, ch = canvas_img.size
    full = (0, 0, cw, ch)
    views = [full] + [(x0 + ox, y0 + oy, x1 + ox, y1 + oy) for x0, y0, x1, y1 in keys] + [full]
    seg = dur / (len(views) - 1)
    i = min(int(t / seg), len(views) - 2)
    u = ease(min(1.0, ((t - i * seg) / seg) / 0.45))  # move in first 45% of each segment, then hold

    def fit(v):
        x0, y0, x1, y1 = v
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        w = max(x1 - x0, (y1 - y0) * 16 / 9) * 1.15
        w = min(w, cw)
        h = w * 9 / 16
        cx = min(max(cx, w / 2), cw - w / 2)
        cy = min(max(cy, h / 2), ch - h / 2)
        return cx, cy, w

    a, b = fit(views[i]), fit(views[i + 1])
    cx, cy, w = (a[k] + (b[k] - a[k]) * u for k in range(3))
    h = w * 9 / 16
    return canvas_img.resize(
        (W, H), Image.BICUBIC, box=(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    )


SC1 = shot_canvas(SHOTS / "01_consumption_patterns.png")
SC2 = shot_canvas(SHOTS / "02_revenue_protection_anomalies.png")
SC3 = shot_canvas(SHOTS / "03_data_quality_completeness.png")
SC4 = shot_canvas(SHOTS / "04_operations_pipeline_health.png")


def offs(sc, name):
    im = load_shot(SHOTS / name)
    return (sc.width - im.width) // 2, (sc.height - im.height) // 2


def s_shot1(t, dur):
    ox, oy = offs(SC1, "01_consumption_patterns.png")
    return tour(
        SC1, [(100, 295, 830, 640), (880, 300, 1490, 520), (1050, 395, 1500, 530)], t, dur, ox, oy
    )


def s_shot2(t, dur):
    ox, oy = offs(SC2, "02_revenue_protection_anomalies.png")
    return tour(
        SC2,
        [(220, 265, 670, 610), (800, 275, 1470, 520), (40, 515, 1470, 640), (800, 545, 1470, 640)],
        t,
        dur,
        ox,
        oy,
    )


def s_shot34(t, dur):
    h = dur / 2
    if t < h:
        ox, oy = offs(SC3, "03_data_quality_completeness.png")
        fr = tour(SC3, [(100, 260, 750, 345), (320, 275, 1110, 620)], t, h, ox, oy)
    else:
        ox, oy = offs(SC4, "04_operations_pipeline_health.png")
        fr = tour(
            SC4,
            [(60, 200, 750, 510), (795, 275, 1480, 460), (795, 455, 1480, 630)],
            t - h,
            h,
            ox,
            oy,
        )
    xf = 0.5
    if abs(t - h) < xf:  # cross-fade between the two tours
        k = (t - (h - xf)) / (2 * xf)
        ox3, oy3 = offs(SC3, "03_data_quality_completeness.png")
        ox4, oy4 = offs(SC4, "04_operations_pipeline_health.png")
        a_ = tour(SC3, [(100, 260, 750, 345), (320, 275, 1110, 620)], min(t, h - 1e-3), h, ox3, oy3)
        b_ = tour(
            SC4,
            [(60, 200, 750, 510), (795, 275, 1480, 460), (795, 455, 1480, 630)],
            max(t - h, 0),
            h,
            ox4,
            oy4,
        )
        fr = Image.blend(a_, b_, ease(k))
    return fr


def s_testing(t, dur):
    img, over, d = canvas()
    header(d, "Testing & delivery", "Executed results only", t)
    stats = [
        (95, "%", "Python coverage", "72 tests passed"),
        (72, "", "Tests", "53 unit + 19 integration"),
        (14, "", "Defects closed", "4 High · 5 Medium · 5 Low"),
        (96, " / 111", "Points accepted", "4 sprints, one day"),
    ]
    for i, (v, suf, lab, desc) in enumerate(stats):
        a = ramp(t, 0.7 + i * 0.5, 0.5)
        x = 96 + i * 440
        card(d, (x, 250, x + 410, 560), a)
        n = v * ease((t - 0.7 - i * 0.5) / 1.6)
        text(d, (x + 40, 290), f"{n:.0f}{suf}", "big", CYAN if i != 2 else ORANGE, a)
        text(d, (x + 40, 420), lab, "h3", WHITE, a)
        text(d, (x + 40, 478), desc, "small", MUTED, a)
    a = ramp(t, dur * 0.55, 0.5)
    text(d, (96, 620), "Velocity (points completed per sprint)", "h3", WHITE, a)
    for i, (sp, v) in enumerate([("S0", 13), ("S1", 19), ("S2", 23), ("S3", 41)]):
        y = 690 + i * 78
        k = ramp(t, dur * 0.6 + i * 0.35, 0.4)
        text(d, (96, y + 6), sp, "body", WHITE, k)
        hbar(
            d,
            180,
            y,
            1300,
            50,
            (v / 41) * ease((t - dur * 0.6 - i * 0.35) / 1.2),
            CYAN if i == 3 else (56, 189, 248),
            k,
        )
        text(d, (1510, y + 25), str(v), "h3", WHITE, k, "lm")
    return compose(img, over)


def s_close(t, dur):
    img, over, d = canvas()
    end = dur * 0.62
    a0 = 1 - ramp(t, end, 0.6)
    header(d, "Limitations & next steps", "Stated plainly", t) if a0 > 0.5 else None
    gaps = [
        "CI workflow written; needs the GitHub token's workflow scope",
        "10× (70-day) load test not yet run",
        "Superset displays UTC; data and logic are IST",
        "Next: incremental models · e-mail alert delivery · Kafka when gateways stream",
    ]
    for i, g in enumerate(gaps):
        k = ramp(t, 0.8 + i * dur * 0.12, 0.5) * a0
        text(d, (140, 290 + i * 110), "■  " + g, "h3", WHITE if i < 3 else CYAN, k)
    a = ramp(t, end + 0.3, 0.9)
    text(d, (W // 2, 440), "GridPulse", "hero", WHITE, a, "mm")
    text(
        d, (W // 2, 580), "Billing you can trust. A pipeline that runs itself.", "h2", CYAN, a, "mm"
    )
    text(
        d,
        (W // 2, 660),
        "Team 14 · github.com/rajareddy-maker/manthan-w2-b-team14",
        "body",
        MUTED,
        a,
        "mm",
    )
    return compose(img, over)


SCENES = [
    s_title,
    s_problem,
    s_goals,
    s_options,
    s_arch,
    s_model,
    s_pipeline,
    s_quality,
    s_shot1,
    s_shot2,
    s_shot34,
    s_testing,
    s_close,
]
LABELS = [
    "Title",
    "Problem",
    "Goals & KPIs",
    "Options",
    "Architecture",
    "Data model",
    "Pipeline",
    "Data quality",
    "Scenario 1",
    "Scenario 2",
    "Scenarios 3 & 4",
    "Testing & delivery",
    "Close",
]


# ------------------------------------------------------------------------------ pipeline
def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def tts(text_: str, out: Path) -> float:
    src = out.with_suffix(".txt")
    src.write_text(text_, encoding="utf-8")
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.SelectVoice('Microsoft Zira Desktop');$s.Rate=1;"
        f"$s.SetOutputToWaveFile('{out}');$s.Speak([IO.File]::ReadAllText('{src}'));$s.Dispose()"
    )
    run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    with wave.open(str(out)) as w:
        return w.getnframes() / w.getframerate()


def narration() -> list[str]:
    s = (DEMO / "storyboard_v2.md").read_text(encoding="utf-8")
    n = s.split("## Narration (voiceover, per scene)")[1].split("## Notes")[0]
    blocks = re.findall(r"\*\*\d+ · \d:\d\d\*\* (.+?)(?=\n\n\*\*\d+ ·|\Z)", n.strip() + "\n", re.S)
    return [" ".join(b.split()) for b in blocks]


def render_scene(fn, dur: float, out: Path) -> None:
    frames = int(round(dur * FPS))
    p = subprocess.Popen(
        [
            FFMPEG,
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        stdin=subprocess.PIPE,
    )
    for i in range(frames):
        t = i / FPS
        fr = fn(t, dur)
        k = min(1.0, t / FADE, (dur - t) / FADE)
        arr = np.asarray(fr, dtype=np.uint8)
        if k < 1:
            arr = (arr.astype(np.float32) * max(k, 0)).astype(np.uint8)
        p.stdin.write(arr.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {out}")


def main() -> None:
    WORK.mkdir(exist_ok=True)
    texts = narration()
    assert len(texts) == len(SCENES), f"{len(texts)} narration blocks vs {len(SCENES)} scenes"
    only = os.environ.get("ONLY")  # e.g. ONLY=5 renders just scene 5 (preview)
    vids, auds, total = [], [], 0.0
    for i, (fn, txt) in enumerate(zip(SCENES, texts, strict=True), start=1):
        wav = WORK / f"n{i:02d}.wav"
        if wav.exists():
            with wave.open(str(wav)) as w_:
                dur = w_.getnframes() / w_.getframerate() + PAUSE
        else:
            dur = tts(txt, wav) + PAUSE
        padded = WORK / f"n{i:02d}_pad.wav"
        run(
            [
                FFMPEG,
                "-v",
                "error",
                "-y",
                "-i",
                str(wav),
                "-af",
                f"apad=pad_dur={PAUSE}",
                "-ar",
                "22050",
                str(padded),
            ]
        )
        mp4 = WORK / f"s{i:02d}.mp4"
        if only is None or int(only) == i:
            render_scene(fn, dur, mp4)
        vids.append(f"file '{mp4.as_posix()}'")
        auds.append(f"file '{padded.as_posix()}'")
        print(
            f"scene {i:>2} {LABELS[i - 1]:<20} {total // 60:.0f}:{total % 60:04.1f}  {dur:5.1f}s",
            flush=True,
        )
        total += dur
    if only:
        return
    (WORK / "v.txt").write_text("\n".join(vids) + "\n", encoding="utf-8")
    (WORK / "a.txt").write_text("\n".join(auds) + "\n", encoding="utf-8")
    out = DEMO / "gridpulse_explainer_v2.mp4"
    run(
        [
            FFMPEG,
            "-v",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(WORK / "v.txt"),
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(WORK / "a.txt"),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB, {total // 60:.0f}:{total % 60:04.1f})")


if __name__ == "__main__":
    main()
