# ADR-006: Spike detection needs a magnitude guard on top of z > 3

- **Status:** Accepted (relayed by Sagar Kalthiya on behalf of Mahendra Umath (PO), 27-Nov-2026) · **Deciders:** Mahendra Umath (PO), Rituja Kekatpure, Sagar Kalthiya
- **Req IDs:** FR-11, US-13 AC1 · **Changes:** CLAUDE.md anomaly default "Spike"

## Context
- The default rule is: interval kWh z-score > 3.0 against the meter's trailing 30 days, with at least 96 points.
- Household load has a strong daily shape. Evening intervals run at about 1.8× the daily mean and morning lows at about 0.45×.
- So a meter's trailing distribution is wide and skewed. Normal peak intervals with ordinary noise regularly exceed 3σ.
- At 3.36M intervals per week, even an ideal Gaussian 3σ test flags about 0.13% of intervals, roughly 4,400 alerts.

We measured the rule on the 7-day demo set (`docs/evidence/sprint_2/spike_rule_measurement.txt`):
- 2,845,357 intervals had at least 96 history points.
- The 5 meters with a crafted spike were injected at about 12× load.

| Rule | Flagged intervals | Meters | Crafted caught | Other meters flagged |
|---|---|---|---|---|
| z > 3 (current default) | 34,932 | 4,998 | 5/5 | 4,993 |
| z > 3 and kWh ≥ 4 × trailing mean | 198 | 183 | 5/5 | 178 |
| z > 3 and kWh ≥ 6 × trailing mean | 16 | 8 | 5/5 | 3 |
| **z > 3 and kWh ≥ 8 × trailing mean** | **10** | **5** | **5/5** | **0** |

For the crafted spikes, the lowest z is 17.8 and the lowest ratio is 14.1.

## Options
| # | Option | Verdict |
|---|---|---|
| A | Keep z > 3 only | Flags 99.9% of meters, so it is useless for revenue protection |
| B | Raise z to 5–6 | Still fires on skewed peaks, and how much depends on each meter's variance |
| C | Same-hour-of-day baseline | Needs 24+ days of history before it can run, which the 7-day demo doesn't have |
| D | **Keep z > 3 and add `kWh ≥ spike_min_multiple × trailing mean` (default 8)** | **Chosen.** The z-score stays the primary statistic; the multiple filters out normal peaks. |

## Decision
- **Spike** = z-score > `spike_z_threshold` (3.0) against the meter's trailing `spike_history_days` (30), using at least `spike_min_points` (96) clean intervals, **and** kWh ≥ `spike_min_multiple` (8) × the trailing mean.
- Clean means received, not spanning a gap, and with a known delta.
- Consecutive flagged intervals merge into one event.
- All four values are dbt vars. Revisit `spike_min_multiple` (8 → 6) or move to option C once 30+ days of history exist.

## Consequences
- Small spikes (2–7× normal) are not flagged. That class belongs to the planned daily-level consumption-shift detector (roadmap), not interval spikes.
- CLAUDE.md anomaly default line updated to match (on acceptance).
