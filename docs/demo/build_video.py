"""Build docs/demo/gridpulse_demo.mp4: real app screenshots timed to an offline TTS voiceover.

Windows only (System.Speech voice "Microsoft Zira Desktop") + ffmpeg on PATH or FFMPEG env var.
Each narration paragraph is synthesised separately so its scene lasts exactly as long as it is
spoken. Run from the repo root:  python docs/demo/build_video.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import wave
from pathlib import Path

DEMO = Path(__file__).resolve().parent
FRAMES = DEMO / "frames"
WORK = DEMO / "_build"
FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
FONT = "C\\:/Windows/Fonts/segoeui.ttf"
FONT_B = "C\\:/Windows/Fonts/segoeuib.ttf"
PAUSE_S = 0.7  # silence after each paragraph

# One entry per narration paragraph (same order as narration.txt): images shown, split evenly.
SCENES: list[list[str]] = [
    ["slide:title"],
    ["slide:architecture"],
    ["airflow_dags.jpg", "airflow_backfill_graph.jpg", "airflow_backfill_runs.jpg"],
    ["dashboard_feeder_consumption.jpg"],
    ["dashboard_anomalies.jpg"],
    ["dashboard_completeness.jpg"],
    ["dashboard_pipeline_health.jpg"],
    ["github_docs.jpg"],
    ["slide:closing"],
]

SLIDES = {
    "title": [
        (90, FONT_B, "GridPulse"),
        (56, FONT, "Smart Meter Telemetry Platform"),
        (36, FONT, "Team 14  ·  Track B  ·  NucleusTeq Indore  ·  27 Nov 2026"),
        (32, FONT, "5,000 meters  ·  480k readings/day  ·  billing, outages, tamper detection"),
    ],
    "architecture": [
        (60, FONT_B, "Architecture"),
        (34, FONT, "Meter gateways (JSONL, v1 + v2)"),
        (34, FONT, "↓  Landing  →  Bronze Parquet lake (dt / zone, raw kept)"),
        (34, FONT, "↓  dbt on DuckDB: kWh · IST · dedup · 15-min grid · gaps · deltas"),
        (34, FONT, "↓  Marts: hourly / daily / monthly · spike · tamper · outage"),
        (34, FONT, "↓  Great Expectations gates  →  Postgres marts  →  Superset"),
        (30, FONT, "Orchestrated by Airflow 3.3.2 · all in Docker · one command: make demo"),
    ],
    "closing": [
        (80, FONT_B, "GridPulse"),
        (40, FONT, "Trustworthy billing · early tamper & outage warnings"),
        (40, FONT, "A pipeline that runs itself"),
        (32, FONT, "github.com/rajareddy-maker/manthan-w2-b-team14"),
        (40, FONT_B, "Thank you"),
    ],
}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def tts(text: str, out: Path) -> float:
    """Synthesise one paragraph with the offline Windows voice; return its duration (s)."""
    src = out.with_suffix(".txt")
    src.write_text(text, encoding="utf-8")
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.SelectVoice('Microsoft Zira Desktop');$s.Rate=0;"
        f"$s.SetOutputToWaveFile('{out}');"
        f"$s.Speak([IO.File]::ReadAllText('{src}'));$s.Dispose()"
    )
    run(["powershell", "-NoProfile", "-Command", ps])
    with wave.open(str(out)) as w:
        return w.getnframes() / w.getframerate()


def slide(name: str, out: Path) -> None:
    """Render a 1920x1080 text slide with ffmpeg drawtext (text from files: no escaping)."""
    lines = SLIDES[name]
    total = sum(size * 1.6 for size, _, _ in lines)
    y = (1080 - total) / 2
    filters = []
    for i, (size, font, text) in enumerate(lines):
        tf = WORK / f"{name}_{i}.txt"
        tf.write_text(text, encoding="utf-8")
        tfp = str(tf).replace("\\", "/").replace(":", "\\:")
        color = "0x22D3EE" if i == 0 else "white"
        filters.append(
            f"drawtext=fontfile='{font}':textfile='{tfp}':fontsize={size}:fontcolor={color}"
            f":x=(w-text_w)/2:y={int(y)}"
        )
        y += size * 1.6
    run([FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=0x0B1220:s=1920x1080", "-frames:v", "1",
         "-vf", ",".join(filters), str(out)])  # fmt: skip


def main() -> None:
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir()
    paras = [p.strip() for p in (DEMO / "narration.txt").read_text(encoding="utf-8").split("\n\n")]
    paras = [p for p in paras if p]
    assert len(paras) == len(SCENES), f"{len(paras)} paragraphs vs {len(SCENES)} scenes"
    for name in SLIDES:
        slide(name, WORK / f"slide_{name}.png")

    concat_v, concat_a = [], []
    for i, (text, images) in enumerate(zip(paras, SCENES, strict=True)):
        wav = WORK / f"p{i}.wav"
        dur = tts(text, wav) + PAUSE_S
        concat_a.append(f"file '{wav.as_posix()}'\nduration {dur:.3f}")
        padded = WORK / f"p{i}_pad.wav"
        run([FFMPEG, "-y", "-i", str(wav), "-af", f"apad=pad_dur={PAUSE_S}", str(padded)])
        concat_a[-1] = f"file '{padded.as_posix()}'"
        for j, img in enumerate(images):
            src = WORK / f"slide_{img[6:]}.png" if img.startswith("slide:") else FRAMES / img
            seg = WORK / f"seg_{i}_{j}.mp4"
            run([FFMPEG, "-y", "-loop", "1", "-i", str(src), "-t", f"{dur / len(images):.3f}",
                 "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0B1220,format=yuv420p",
                 "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                 str(seg)])  # fmt: skip
            concat_v.append(f"file '{seg.as_posix()}'")
        print(f"scene {i + 1}/{len(SCENES)}: {dur:5.1f}s  {', '.join(images)}")

    (WORK / "video.txt").write_text("\n".join(concat_v) + "\n", encoding="utf-8")
    (WORK / "audio.txt").write_text("\n".join(concat_a) + "\n", encoding="utf-8")
    out = DEMO / "gridpulse_demo.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(WORK / "video.txt"),
         "-f", "concat", "-safe", "0", "-i", str(WORK / "audio.txt"),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
         str(out)])  # fmt: skip
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
