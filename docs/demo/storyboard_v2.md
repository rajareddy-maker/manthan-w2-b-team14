# GridPulse — Explainer Video v2: Time-coded Script & Storyboard

**Target:** 6:47 (≈ 975 spoken words at ~147 wpm, offline voice at Rate 1) · 1920×1080, 30 fps
**Source of truth:** `Downloads/GridPulse — Team 14 Deck v2.pptx` (13 slides) + `docs/evidence/`. Every number on screen is taken from the deck, which was fact-checked against the repo and the live warehouse on 27-Nov-2026.
**Visual language:** dark navy canvas (`0B1220`), cyan headline (`22D3EE`), amber highlight (`FFD54F`), orange focus boxes (`FF8C00`). Motion: kinetic type, slow push-in/pan over real screens, cross-fades (0.5 s), animated charts that build as the narration names each value.
**Production toolchain (local, no external services):** matplotlib for animated charts and diagram frames · ffmpeg for motion, transitions, typography and the final render · Windows offline TTS (Zira) for the voiceover · real screenshots in `docs/demo/frames/` and `Downloads/GridPulse_screenshots/`.

| # | Time | Deck slide | On screen (storyboard) | Animation / data visual |
|---|---|---|---|---|
| 1 | 0:00–0:14 | 1 Title | Black → "480,000 readings a day." types on; then "Can you bill from them?"; GridPulse title card | Kinetic typography; counter 0 → 480,000; title fade-up |
| 2 | 0:14–0:44 | 2 Problem | Four stat cards slide in one by one: 3 teams · 1000× · after complaints · 480k/day | Cards stagger in (0.3 s apart); "1000×" pulses on "watt-hours vs kilowatt-hours" |
| 3 | 0:44–1:14 | 3 Goals & KPIs | Six goal rows; each gets a green tick with its measured result | Checklist animation G1→G6, result text slides in on each tick |
| 4 | 1:14–1:36 | 4 Options | Horizontal bars A 4.70 · B 3.45 · C 2.80; "A: batch lakehouse" crowned | Animated bar chart growing to scored values; rejected options dim |
| 5 | 1:36–2:28 | 5 Architecture | Flow builds left→right: gateways → landing → bronze → silver → gold → GX gate → Postgres → Superset; Airflow arc underneath | Diagram nodes appear in narration order; "397 MB → 38 MB" counter on bronze; pinned-stack chips fade in |
| 6 | 2:28–2:50 | 6 Data model | Grain ladder: 15-min interval → hour → day → IST month; feeder/zone roll-ups | Ladder steps drop in; "DECIMAL(18,4) — never FLOAT" stamp |
| 7 | 2:50–3:35 | 7 Pipeline | Airflow graph screenshot; six tasks light up in sequence; "174 s" | Push-in on the DAG graph; task boxes highlight one by one; timer counts to 174 s |
| 8 | 3:35–4:10 | 8 Data quality | Equation 3,392,136 = 3,347,177 + 43,439 + 1,520; then spike-rule bar 34,932 → 10 flagged intervals | Equation assembles term by term; before/after bar chart collapses (z>3 alone vs z>3 + 8× guard) |
| 9 | 4:10–4:26 | 9 Scenario 1 | Feeder-consumption screenshot | Slow zoom to callout 1 → 2 (evening peaks) → 3 (22 Nov outage dip) |
| 10 | 4:26–5:07 | 10 Scenario 2 | Anomalies screenshot | Zoom: pie (9 events) → spike rows → outage row → tamper rows; "0 false positives" stamp |
| 11 | 5:07–5:43 | 11 Scenarios 3 & 4 | Completeness screenshot, then pipeline-health screenshot | Cross-fade between the two; zoom to the 22 Nov bar, then the CRITICAL alert row |
| 12 | 5:43–6:16 | 12 Testing & delivery | Counters: 95% coverage · 72 tests · 14 defects closed · 96/111 pts; velocity bars 13 · 19 · 23 · 41 | Number tickers; velocity bar chart grows |
| 13 | 6:16–6:47 | 13 Limitations & ask + close | Three honest gaps (CI token scope, 10× run, UTC display); end card "GridPulse — a pipeline that runs itself" | Bullets fade in; end-card logo hold |

## Narration (voiceover, per scene)

**1 · 0:00** Four hundred and eighty thousand readings a day. Five thousand smart meters, every fifteen minutes. The question every utility has to answer: can you bill from them? This is GridPulse, by Team 14.

**2 · 0:14** Three teams live with this data: billing, network operations, and revenue protection. Today, readings arrive late, duplicated and in two formats. One meter reports watt-hours, another kilowatt-hours, a thousand-fold error waiting to happen. Gaps are silently filled, and tampering or outages are found only after customers complain. At four hundred and eighty thousand readings a day, three point three nine million in our demo week, nobody can check this by hand.

**3 · 0:44** So we wrote six goals before any code, each with a measurable result. Consumption reconciles exactly to the meter registers. The monthly billing table covers all five thousand meters. Every gap is marked, never invented, with ninety-nine point four seven percent completeness. Every planted anomaly is found, with zero false positives. A seven-day backfill finishes in a hundred and seventy-four seconds. And the whole platform starts with one command, in under eleven minutes.

**4 · 1:14** We scored three architectures. A batch lakehouse on files, DuckDB and dbt scored four point seven. Streaming with Kafka scored three point four five, and a Spark lakehouse two point eight. With a daily SLA, about a hundred megabytes a day and a fourteen-gigabyte laptop, streaming and Spark add cost without benefit.

**5 · 1:36** Here is the flow. Gateways drop JSON files into landing. An extractor writes every line, unchanged, into a bronze Parquet lake, three hundred and ninety-seven megabytes shrinking to thirty-eight. Silver, built in dbt on DuckDB, converts to kilowatt-hours in Indian Standard Time, removes duplicates, snaps readings to a fifteen-minute grid and quarantines bad rows. Gold reconciles to the register, and only after the Great Expectations gate passes are the marts swapped into Postgres for Superset. Airflow orchestrates it all, with every version pinned. Two design choices make this safe to re-run. Bronze is append-only, so any day can be replayed from the raw payload. And every write is an atomic swap, so a dashboard never sees a half-loaded table, and publishing twice gives identical totals.

**6 · 2:28** The data model is built on grain. Silver holds one row per meter per fifteen-minute slot. Gold rolls that up to hour, day and Indian-time month for billing, plus feeder and zone per day. Every kilowatt-hour is a fixed decimal with four places, never a float, because these numbers become bills.

**7 · 2:50** In Airflow, one chain of six tasks runs every night at one-thirty. Ingest, build and test with dbt, run the quality gates, publish, record metrics and alerts, then apply retention. Each task retries twice, and a three-day lookback absorbs late files automatically. If a quality gate fails, publish simply never runs, and yesterday's numbers stay live. For older corrections, a separate backfill pipeline takes any start and end date and runs the same chain. DuckDB allows a single writer, so those tasks share one slot and never collide. The seven-day backfill completes in one hundred and seventy-four seconds, about twenty-five seconds per day of data against a fifteen-minute SLA.

**8 · 3:35** Nothing disappears silently. Every bronze row is accounted for: three point three nine million landed equals rows kept, plus forty-three thousand duplicates, plus fifteen hundred quarantined with a reason code. We also measured our own spike rule before shipping it. A z-score above three, alone, flagged nearly thirty-five thousand intervals on almost every meter. Adding an eight-times-normal guard cut that to the ten real spike intervals, and we recorded the decision in an architecture decision record, so the threshold can be tuned later with evidence.

**9 · 4:10** This is the live dashboard. Network load: about sixty-three thousand kilowatt-hours a day across twenty feeders, reconciled to four decimals. The evening peak shows up every day. And on the twenty-second, one feeder dips: a two-hour outage.

**10 · 4:26** Revenue protection. Nine events: five spikes, three tampers and one outage, exactly the set we planted, with zero false positives. Each rule is simple to explain. A spike is an interval far above the meter's own thirty-day history. Tamper is a register that stays flat for at least two days while the other meters on its feeder keep consuming, which is what separates theft from a dead feeder. An outage is thirty percent or more of a feeder's meters missing the same intervals. Here, a hundred and two of two hundred and fifty meters went silent at once.

**11 · 5:07** Data quality: every zone stays above ninety-eight percent, and the outage day stands out in Bhawarkua. Operations: every run records the rows it ingested, the rows it rejected, the duplicate rate, completeness and ingest lag, about three point four million rows in two to four and a half minutes. When a task fails after its retries, a critical alert appears here automatically, and when data arrives too late for the three-day window, the alert tells the on-call engineer to run a backfill, exactly as the runbook describes.

**12 · 5:43** Seventy-two tests at ninety-five percent coverage. Fourteen defects found and closed. The tests work at three levels: unit tests for the Python, crafted meter histories pushed through the real dbt pipeline, including cases that must not raise an alert, and integration tests against the live Postgres and Superset. Every anomaly rule is checked row by row against the generator's ground truth. Four sprints in one day, with ninety-six of a hundred and eleven points accepted by our Product Owner.

**13 · 6:16** We're honest about what's left. The CI workflow is written but needs a token scope to reach GitHub. The ten-times load test hasn't run yet. And Superset shows times in UTC, although the data is in Indian time. Next come incremental models, email alert delivery, and Kafka once the gateways can stream. Every number you saw links to an evidence file in the repository. GridPulse: billing you can trust, and a pipeline that runs itself.

## Notes for review
- Numbers that changed since v1: monthly billing coverage (5,000/5,000), 72 tests (53 unit + 19 integration), and the spike-rule measurement (34,932 → 10 flagged intervals).
- Removed from v1: unverified fresh-clone failure claims (DEF-015 does not exist in the repo).
