# PumpVerity AI - NCDMB demonstration runbook

A 6-8 minute live demonstration that proves the deck's core claims on screen: the four decision
outcomes (slide 10), the Sense → Interpret → Qualify → Act pipeline (slide 5), human review and
traceability, and the MCP Engineering Copilot (slide 9). Everything runs offline on one laptop.

## Test sign-in details

Local demo accounts, created by `scripts/setup.ps1` / `scripts/demo.ps1`. Sign in with the
**username** or the email. All four use the same password.

| Username | Email | Name | Role | Use it for |
|---|---|---|---|---|
| `admin` | `admin@petrosense.local` | Amina Bello | Administrator | **Presenting** - sees every screen and the presenter bar |
| `engineer` | `engineer@petrosense.local` | Chinedu Okafor | Engineer | Monitoring, pumps/sensors, alert review, presenter bar |
| `researcher` | `researcher@petrosense.local` | Fatima Yusuf | Researcher | Model registry and analysis |
| `reviewer` | `reviewer@petrosense.local` | Tunde Adeyemi | Reviewer | Alert acknowledgement and engineering review |

**Password (all accounts): `PumpVerity@2026`**

> These credentials are for the local, offline demonstration only (the app listens on
> `localhost`). Set a private `PETROSENSE_DEMO_PASSWORD` in `apps/api/.env` before any hosted or
> shared deployment. `scripts/demo.ps1` re-applies the password from `.env` on every launch.

## Morning checklist (start 15 minutes before)

1. Laptop on mains power; sleep and screen-off disabled; notifications off (Focus Assist).
2. Connect the projector and set the resolution first (1366×768 or larger works). Browser zoom 100%.
3. From the repository root, in PowerShell:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/demo.ps1 -Reset
   ```

   `-Reset` gives a clean database and streams a ~1-minute scripted history (healthy, uncertain,
   two faults, a sensor disconnect) so every screen has content with today's timestamps. Three
   windows open, titled *"... - keep this window open"* (API, Web, Edge stream). **Minimise them;
   never close them.** Closing the API window is what causes a 502 / "API is not running" error
   at sign-in. Each window restarts its service by itself if it ever stops.
4. In the browser, sign in as `admin`, open **Dashboard**, press **1** (Healthy). Collapse the
   Copilot panel. You are ready.
5. Keep `Downloads\PumpVerity_demo_screenshots` open in a background window as a fallback.

No internet connection is needed.

## Presenter controls

The dark **presenter bar** at the bottom of every page drives the simulated test rig. Keyboard
shortcuts work anywhere except while typing in a text box:

| Key | Scenario | Expected outcome on screen |
|---|---|---|
| `1` | Healthy operation | Green - *Operating normally* |
| `2` | Rotor imbalance | Red - *Fault suspected - inspect*, alert raised |
| `3` | Cavitation | Red - *Fault suspected*, alert raised |
| `4` | Weak anomaly | Amber - *Uncertain - engineering review* (the model abstains) |
| `5` | Sensor disconnect | Violet - *Sensor invalid - not inferred* (model never runs) |
| `P` | Pause / resume | Stream stops; the header shows IDLE |

The change appears within 1-3 seconds. One alert is raised per episode, not one per second.

## Demo script

| # | Do | Say (in your own words) | Slide |
|---|---|---|---|
| 1 | Dashboard, healthy (`1`) | "This is the edge decision console for our centrifugal-pump test rig. Every second a vibration window passes through the same pipeline you saw on slide 5." Point at the four pipeline stages and the live score. | 5 |
| 2 | Press `2` (imbalance) | "We inject a rotor imbalance. The score jumps into the fault zone, the condition turns red, and a reviewable alert is raised - in about 0.1 ms of on-device inference." | 10 |
| 3 | Press `4` (weak anomaly) | "This is the research differentiator. A weak, ambiguous signal lands in the amber band. Instead of guessing, the system abstains and routes it to an engineer." | 10, 12 |
| 4 | Press `5` (sensor disconnect) | "Now the sensor fails. Validation rejects the signal *before* the model runs. A broken sensor is never reported as a healthy pump." | 10 |
| 5 | Press `1`, then click the newest alert in **What just happened** | "Every alert keeps its original AI evidence - score, model version, signal window. The engineer acknowledges and records a judgement; the AI record is never edited." Acknowledge it and add a short review note. | 12 |
| 6 | Open **Engineering Copilot** on that alert, click or type *"Why was this event marked uncertain?"* | "The Copilot answers only from data it retrieves through MCP tools - you can see each tool call. It cannot change anything without approval." | 9 |
| 7 | Ask *"Generate a monitoring report"* → **Approve** | "Writes require explicit approval, are audited, and the report carries a SHA-256 fingerprint and a simulated-data disclosure." | 9 |
| 8 | **Model Registry** | "Models are hash-verified, versioned and can be rolled back. Note the warning: these metrics are synthetic. Real accuracy is what the six-month lab phase will measure." | 12 |
| 9 | Back to Dashboard | "The software is built and working today. The funding builds the calibrated rig, collects real data and measures real performance." | 16 |

Tips: in the Copilot, prefer the suggested-question chips - they are guaranteed to match a tool
plan. The deterministic local planner understands monitoring questions, not open conversation.

## Honest answers to likely questions

- **"Is this real pump data?"** No. Signals come from a deterministic simulator; every record is
  labelled SIMULATED. The software pipeline is real and is what will run on the rig.
- **"How accurate is it?"** Unknown until the lab phase - that is the research question. The
  synthetic hold-out score (1.000) is meaningless for real pumps and we do not claim it. The primary
  endpoint is recall at a fixed false-alert limit on independent runs plus one held-out regime
  (slide 12).
- **"Why a simple linear model and not deep learning?"** It runs in ~0.1 ms on an edge device and
  is transparent. Slide 9's 1D-CNN/XGBoost are candidates to compare against it, not what runs today.
- **"What happens when the network drops?"** Inference is local. Durable offline buffering and
  sync is the next software stage - not built yet; say so.
- **"Can it shut the pump down?"** No, by design. It is advisory; an engineer decides.
- **"What is Nigerian about it?"** Designed, coded and tested locally - sensing integration,
  signal processing, AI and software - building the instrumentation and embedded-AI capability
  slide 13 describes.

## If something goes wrong

| Symptom | Fix |
|---|---|
| Sign-in shows **"The monitoring API is not running"** (or "status 502") | The API window was closed. Run `powershell -ExecutionPolicy Bypass -File scripts/demo.ps1` again (it stops nothing that is still running; if it reports a port in use, run `scripts/demo-stop.ps1` first). |
| Presenter bar says **Edge stream offline** | The Edge window was closed. In the repo root: `apps/api/.venv/Scripts/python -m petrosense_edge.demo` |
| Page looks frozen | Press `F5`; the session restores automatically. |
| Signed out | Sign in again as `admin` / `PumpVerity@2026`. |
| Anything else | `powershell -File scripts/demo-stop.ps1`, then `powershell -ExecutionPolicy Bypass -File scripts/demo.ps1` (no `-Reset` keeps history; takes ~20 s). |
| Laptop failure | Present the fallback screenshots. |

The edge stream reconnects by itself if the API restarts, and closes any interrupted session as
ABORTED so the records stay honest.
