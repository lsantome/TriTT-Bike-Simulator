# Cycling simulator for triathlon (non-drafting) and time trial

[![tests](../../actions/workflows/tests.yml/badge.svg)](../../actions/workflows/tests.yml)

**[English](#english) · [Español](#español)**

---

# English

A personal-use tool that does two different jobs:

1. **Estimates the drag coefficient (CdA)** of your bike and riding position from a real `.fit`
   activity, by closing the energy balance over flat segments ridden in both directions.
2. **Predicts a race**: given the route **GPX**, that CdA and a **power-by-gradient profile**
   (climb / flat / descent), it computes time, speed and power per segment with a physical model
   and editable parameters.

Everything the tool produces comes with its uncertainty margin. That is the design principle of the
project: **no number is ever presented on its own**, and anything unverified is said to be so.

> **What this repository is and what it is not.** It is a **Streamlit (Python)** application that
> runs on your own computer via `./run.sh` or `run.bat` and opens your browser on `localhost`. It
> is **not an installable PWA, it is not published on GitHub Pages and there is no APK**: Streamlit
> needs a Python process behind it, and a PWA is a set of static files. Rewriting the model in
> JavaScript (or running it in the browser with Pyodide/stlite) is a separate project that would
> require revalidating the physics against the five real activities.

## Features

**CdA estimation from your own activities**

- Reads `.fit` files with GPS and power and estimates CdA by closing the energy balance, integrating
  interval by interval: it assumes neither constant speed nor constant gradient.
- **Automatic search for reliable segments**: sweeps the activity in windows from 1 to 5 km, keeps
  the flat, fast, non-overlapping ones, and for each one locates **the return pass along the same
  road**. Averaging out and back is the only way to cancel the wind without modelling it.
- **Manual selection** of a segment, by dragging over the route profile or with a slider.
- Every estimate comes with its **uncertainty** (propagating altitude error, Crr error and power
  meter bias) and with a **validity diagnosis** of the segment: if it is not usable, it says so and
  does not present the value as good.
- **Activity coherence check**: before accepting a CdA, it tests whether the ride is explainable by
  the model or whether it was faster than the recorded power allows (tailwind, drafting, group).
  See [does this activity qualify?](#does-this-activity-qualify-the-coherence-check).
- **Impossible pairs rejected and shown**: an out-and-back pair whose speeds differ too much is not
  measuring wind, it is measuring gradient; it is rejected with its reason written out.
- A table with **one row per segment** and CSV download, including the breakdown of uncertainty by
  source.
- The result is carried over to the simulator **with one button**, where it becomes an editable
  value.

**Race prediction**

- **GPX** loading, resampling to constant distance, elevation and track smoothing.
- **Power-by-gradient profile** with a continuous transition, editable threshold and width.
- Output with **total time, average speed, per-segment table and charts, NP, VI and IF**.
- **Curvature speed limit** and descent speed cap, with maximum braking propagated backwards; if
  the limit cuts the speed, the applied power is reduced to what is needed, and that is reflected in
  NP/VI/IF.
- **Two uncertainty bands** that measure different things (model and day), both derived from
  cross-validation with real activities. See [how much to trust it](#how-much-you-can-trust-the-predicted-time).
- **Sensitivity report**: the effect on total time of each parameter at ±10 %, contrasted against
  your own route data.
- **Named bike profiles** that record where their CdA came from.
- With no GPX loaded, a **synthetic example route** (~26 km) to try it out.

**Across both modules**

- **Spanish and English**, with a sidebar selector: labels, tooltips for all 40 parameters, tabs,
  messages and estimator warnings. Downloadable CSVs keep the technical column names (`tiempo_s`,
  `cda`, `desnivel_m`) in both languages, deliberately, so spreadsheets do not break.
- **Light theme by default and a complete dark theme**, both derived from the same tokens, charts
  included.
- **Its own design system** in a single module (`app/theme.py`), with an explicit visual language
  for uncertainty: solid narrow band = estimated from data; hatched wide band = margin of the day or
  unverified claim.
- **Core with no interface dependencies** (`core/`): the physics, the estimator and the tables can
  be used and verified without Streamlit.
- **372 automated tests** tied to the 32 acceptance criteria of the specification.

## Requirements

| | |
|---|---|
| **Python** | 3.9 or later. The launchers detect it and, if missing, say so with the download link |
| **System** | Windows, macOS or Linux |
| **App dependencies** | `numpy`, `pandas`, `streamlit`, `plotly`, `fitdecode` (`requirements.txt`) |
| **Test dependencies** | the above plus `pytest` and `scipy` (`requirements-dev.txt`) |
| **Disk** | about 300 MB once the virtual environment is created |
| **Browser** | any recent one; the app opens on `localhost` |

`scipy` is for the tests only, which use it as an independent reference solution. **Starting the app
does not install test dependencies**, and a test checks that everything the app and the core import
is declared in `requirements.txt`.

To estimate CdA you also need a `.fit` activity **with GPS and power**, preferably with some flat
stretch ridden in both directions.

## How to run it

**Without the command line** (recommended):

- **Windows:** double-click `run.bat`
- **macOS / Linux:** `./run.sh` in a terminal (on macOS, if you prefer double-clicking, rename the
  file to `run.command`)

The first run creates a virtual environment in `.venv` and installs the dependencies (a couple of
minutes); later runs start straight away. If you clone the repository on macOS or Linux and
`./run.sh` will not start, give it execute permission with `chmod +x run.sh`.

| Option | What it does |
|---|---|
| `run.sh` / `run.bat` | opens the application in the browser |
| `run.sh --estimador` / `run.bat --estimador` | starts directly in the CdA estimation module |
| `run.sh --tests` | installs the test dependencies and runs the 372 tests |
| `run.sh --reinstalar` | rebuilds the environment from scratch |
| `run.sh --reinstalar --tests` | both |

By hand, if you prefer:

```bash
pip install -r requirements.txt          # app
pip install -r requirements-dev.txt      # app + tests
streamlit run app/streamlit_app.py       # from the project root
python -m pytest -q                      # 372 tests
```

The initial module can also be set by adding `?modo=estimador` to the URL.

> `run.sh` has been tested end to end (environment built from scratch, application responding).
> **`run.bat` could not be run on Windows**: it is validated by inspection and by a static lint of
> the usual `cmd` pitfalls. If it fails for you, send whatever the window says.

### Self-contained Windows package (no Python required)

For people who should not have to install anything there is a Windows package: a folder carrying an
embedded Python with every dependency inside. Extract the **whole** folder and double-click
`TriTT.bat`.

- It is built by the `paquete-windows` workflow on a clean `windows-latest` runner, never by hand,
  so whatever is distributed comes from an identifiable commit. Run it from the Actions tab to get
  a downloadable artifact, or push a `v*` tag to attach the ZIP to that release.
- To build it yourself: `pwsh -File packaging\windows\construir.ps1`.
- **Nothing is frozen** (no PyInstaller): it is the same Python running the same code, with the
  interpreter travelling in the folder. Freezing Streamlit is fragile — it boots through its own
  CLI, loads static assets from the package directory and reads metadata with
  `importlib.metadata` — so every upgrade can break the build. The build does check that the
  packaged interpreter can import the application, and fails rather than shipping a folder that
  will not start.
- Bike profiles are written to `%APPDATA%\TriTT-Bike-Simulator\`, not next to the program, so the
  package can sit in a read-only location and replacing it does not lose your profiles.
- The package is **not code-signed**, so SmartScreen warns on first run. `LEEME.txt` inside the ZIP
  explains that, and everything else, to someone who has never opened a terminal (in Spanish).

## The two modules and the intended workflow

They are chosen with the **What do you want to do** selector in the sidebar:

| Module | Input | Output | Parameters it asks for |
|---|---|---|---|
| **CdA estimation** | one `.fit` activity | the CdA of that bike in that position, with its margin | 23 |
| **Race prediction** | the route GPX and a CdA | time, speed and power per segment | 40 |

The order matters, because **CdA is an input to the prediction and it is the parameter that moves it
most**: a prediction made with the default CdA is not a prediction of your bike.

1. In the **estimation** module, upload an activity with the setup and position you intend to race
   with, and with some flat stretch ridden in both directions. Press **🔍 Find reliable segments**.
2. Read the coherence verdict and the warnings **before** the number. If the activity does not
   qualify, neither does the CdA.
3. Press the button to **apply that CdA**. It lands in the simulator as an editable field: use it as
   is, or correct it by hand if your race setup is not exactly the one in the activity.
4. In the **prediction** module, upload the race GPX and state the power you plan to hold.

The estimation module **does not ask for a GPX** nor for parameters that play no part in its
calculation. Above all, **it does not ask for CdA**: that is what it estimates, and asking for it as
an input would be circular. It does not ask for the power profiles, FTP, the speed and curvature
limits or the route resampling either.

That split lives in the core (`core.params.specs_for_module`) and an **empirical** test guards it:
changing a parameter the module does not show must not move the estimate, and changing one it does
show must move it. The list is not maintained by hand.

## What the CdA this tool estimates actually is (and what it is not)

This is the most important thing to understand in order to use the numbers sensibly.

In the model, `CdA` is the **drag area** (m², the product of the shape coefficient and the frontal
area) multiplying the aerodynamic term `½·ρ·CdA·v²`. But the value the tool **estimates** is not a
wind-tunnel CdA: it comes from closing the energy balance of a real segment. Whatever came in
through the pedals, minus what went into climbing, rolling resistance and changes in kinetic energy,
is attributed entirely to the aerodynamic term:

```
∫ η·P dt − Σ ½·m_ef·Δ(v²) − m·g·Σ Δh − ∫ Crr(v)·m·g·cosθ·v dt  =  ∫ ½·ρ·CdA·v³ dt
```

Because CdA is **the residual that makes that equality balance**, *everything* that opposed forward
motion and is not named separately by the model ends up inside it:

| Inside the estimated CdA | How much it weighs |
|---|---|
| The real aerodynamics (bike, body, helmet, clothing, position) | what you actually want to know |
| **The net wind of the day** | **by far the largest term**: 1 m/s shifts the result by roughly ±0.04–0.06 m², more than all the other errors put together |
| Drafting behind other riders, vehicles or a group | can be enormous and is indistinguishable from wind |
| Altimeter error | ±1 m of elevation change over the segment propagates into the result; on short, slow or hilly segments it swallows the estimate whole |
| The gap between the chosen Crr and the real road surface | ±0.0005 of Crr, propagated |
| Power meter bias | ±1.5 % of power, propagated |
| Any residual error of the model itself | goes to the same place, by construction |

So, strictly speaking, **what comes out is an effective coefficient of resistance to forward
motion** for that bike, that position and conditions similar to those of the activity — not a
physical property of the bike. Practical consequences:

- **Wind is removed by pairing, not by modelling.** It is not an input to the model. Because it is a
  **bias and not noise**, it does not enter the uncertainty: it is shown separately (hatched band)
  and it cancels to first order by averaging an outbound stretch with the same stretch inbound. That
  is why the recommended value is the one from **pairs**, not from an isolated segment.
- **The bearing of each segment gives the wind away.** If segments one way give a low CdA and those
  the other way give a high one, that is wind and not your position. The table carries that column
  for exactly that reason.
- **If you change kit or position, it has to be estimated again.** What you wear is not a model
  parameter: it is inside the CdA.
- **Do not compare it with manufacturer or wind-tunnel figures.** They do not measure the same
  thing.
- **A CdA obtained in training is not the racing one.** The example profile shipped with this
  repository comes from 4-hour rides at 210-226 W and 31-33 km/h: it is a training-position CdA.

### Does this activity qualify? The coherence check

Any fitting method **always** returns a number: it looks for the CdA that makes the books balance
and it finds one. What it does not tell you is whether that number means anything. If one day you
went faster than the power you recorded allows, the fit lowers the CdA until the total matches, and
the result is not an aerodynamic figure but the residual of a fit that does not close.

The check detects that signature by separating the error **by gradient band**, and warns if:

- the resulting CdA falls **outside the plausible range 0.20–0.35 m²**, or
- the pattern **flat too slow (error ≥ +5 %) and descents too fast (≤ −4 %)** appears, which is what
  a ride with a tailwind, drafting or a group produces, and which a mere CdA error cannot produce
  (not with both signs at once).

Both rules are needed: one of the five reference rides has its CdA inside the range and only the
pattern catches it. The thresholds are backed by data: across the three coherent rides the flat
error does not exceed −0.7 % and the descent error +0.8 %; across the two incoherent ones the flat
is at +15.8 % and +29.6 % and the descents at −7.9 % and −18.4 %. There is an **order of magnitude**
between the worst coherent ride and the best incoherent one.

The diagnosis is built in the core (`core/coherence.py`), not in the interface, and it uses a fixed
configuration on purpose: the verdict must not change because someone adjusted a parameter in order
to predict a race.

### Recommended protocol

1. Use only rides from **the same bike**.
2. **Put each one through the coherence check** and leave out those that raise a warning. Record the
   reason with the figure that backs it, not with a hypothesis.
3. Obtain the CdA from the **out-and-back pairs**, which is the reproducible method (3.3 % spread
   across rides, 1.9 % with the impossible-pair filter, versus 21.3 % for the total-time fit). The
   total-time fit remains an **independent cross-check**, not the source of the figure.
4. Use **at least 2** coherent rides and look at the spread between them, not just the best fit.
5. **Do not average incoherent rides** with the good ones: they would inject the wind of their day
   into the parameter.

### When a segment is not accepted

Minimums for a segment to count as usable: **1 km**, 45 s, 25 km/h average, at least **half** of the
dissipated energy being aerodynamic, and uncertainty **≤ ±0.030 m²**. A segment that fails any of
these is flagged as not usable with the reason written out, not hidden.

## The physical model

For each segment of length `d` over the road, with constant power `P` and speeds `v₀ → v₁`:

```
½·m_ef·(v₁² − v₀²) = d·( η·P / v̄ − ½·ρ·CdA(v̄)·(v₀²+v₁²)/2 − Crr(v̄)·m·g·cosθ ) − m·g·Δh
```

with `v̄ = (v₀+v₁)/2` and `m_ef = m + I/r²` (wheel inertia). This form is exact for constant power
and uniform acceleration. It is solved per segment with regula falsi (Illinois); where several
solutions exist (the CdA transition zone) the one closest to `v₀` is chosen, following the real
trajectory. The segment time is `d·2/(v₀+v₁)`.

| Element | Model |
|---|---|
| **Mass** | a single total value (rider + bike + equipment). The split enters no equation: only the sum |
| **Power by gradient** | `P(g)` = flat / climb / descent with a continuous *smoothstep* transition; threshold (±2 %) and width editable |
| **CdA(v)** | `CdA + ΔCdA·σ((v₀ − v)/w)`, a logistic centred on 20 km/h (default ΔCdA = +0.25 m², w = 1 km/h). Continuous, no jumps |
| **Crr(v, p)** | `Crr_ref·(p_ref/p)^exp + crr1·(v − 29 km/h)` per surface (smooth / normal / rough); `Crr_ref` is defined at 29 km/h and at the reference pressure. Floor at 0.5·Crr_ref |
| **Wheel** | the circumference comes from the ETRTO size (default 28-622) or is entered as measured with the «manual» option; the radius is derived from it. It only enters rotational inertia and moves the time by less than 0.001 % |
| **ρ** | humid air: temperature, humidity (Magnus), sea-level pressure corrected for the altitude of each point (ISA) |
| **Curvature limit** | `v ≤ √(a_lat/κ)` (on by default, `a_lat` = 3 m/s²), with maximum braking (3 m/s²) propagated backwards; κ from the heading derivative with dilation towards the ends of the arc. Reliable for R ≥ max(10 m, track window / 7); below that it is **optimistic** (+4.5 % speed at R = 8 m, +16.3 % at R = 4 m) |
| **Speed cap** | 100 km/h by default |
| **Applied power** | if the limit cuts the speed, the applied power is reduced to what is needed (≥ 0), and that is reflected in NP/VI/IF |
| **NP / VI / IF** | NP: 30 s rolling mean at 1 Hz and 4th-power mean; VI = NP/mean; IF = NP/FTP |

**GPX smoothing:** resampling to constant distance (20 m), Gaussian smoothing of elevation (150 m
window) and of the track (60 m), gradient clipped to ±30 %.

### Parameters (defaults: sea level, A Coruña)

| Category | Main parameters | Advanced |
|---|---|---|
| **Rider** | total mass (**mandatory**, no default) · P climb/flat/descent 220/200/0 W · FTP (optional) | gradient threshold 2 %, transition width 1 %, initial speed 18 km/h |
| **Equipment** | CdA 0.27 m² · ΔCdA 0.25 m² · η 0.975 · wheel ETRTO 28-622 (or measured circumference) | position threshold 20 km/h, width 1 km/h, inertia 0.14 kg·m² |
| **External variables** | temperature 15 °C · humidity 75 % · surface (smooth/normal/rough) · pressure 7.0 bar · segments per km · max speed 100 km/h · curvature limit | atmospheric pressure 1013.25 hPa, manual density, Crr per surface, variation of Crr with v, a_lat, braking, smoothing windows, step, impossible-pair threshold |

The main/advanced classification is a design decision. The **Sensitivity** tab contrasts it against
your own route data (`sugerencia` column).

## Bike profiles

Each bike has its own CdA and its own masses, so the application saves **named profiles**
(`perfiles_bici.json`, next to the project; it can be changed with the `SIMCICLISMO_PERFILES`
environment variable). A profile fixes masses, CdA, ΔCdA, η, Crr, surface and inertia, and also
records **where the CdA came from**: which activities produced it and whether it is calibrated or a
default value. A CdA saved without that provenance is not traceable and the application marks it as
*not calibrated*.

`perfiles_bici.ejemplo.json` holds the profile obtained from the out-and-back pairs over the 3
coherent rides of the reference route (CdA 0.261 m², total mass 90 kg). Rename it to
`perfiles_bici.json` to use it. It is a **training-position** CdA: to race, estimate your own with
an activity carrying the race setup and position.

## How much you can trust the predicted time

The application always shows the time with its margin, using **two bands that measure different
things** — which is why both are given, rather than their average or the better of the two:

| Band | Value | What it measures and where it comes from |
|---|---|---|
| **Model precision** | **±1.4 %** | Leave-one-out cross-validation with the 3 coherent rides of the reference route; mean error 0.94 %, maximum 1.39 %. This is what the physical model is worth on the same bike and route when the day is unremarkable |
| **Margin of the day** | **±15 %** | Obtained with the protocol the tool itself recommends: calibrating only with the 3 coherent rides and predicting any day, including the 2 incoherent ones. Worst error **14.27 %**. This is what not knowing the wind costs |

Tables and CSVs carry four extra columns for every time column (`_min_modelo`, `_max_modelo`,
`_min_dia`, `_max_dia`), so that no time leaves the tool without its margin.

**On a new route there is no verified band.** The margin of the day is a **floor**, not an estimate:
no validation has been able to cross routes, because there are no rides of this bike on another
course. The ±11 % this table used to give for a new route was withdrawn as incoherent: it was
*smaller* than the wind margin already observed on the calibration route itself.

### Results with the real data (5 rides on the same route, Mar 2025 to Apr 2026)

The model was validated by separating the error **by gradient band**, which is more demanding than
total time: a global fit can be right by cancelling opposite errors, and this cannot.

| Gradient band | 30 Mar | 06 Apr | 19 Apr 26 |
|---|---|---|---|
| descent > 6 % | −7.7 % | −1.6 % | +0.6 % |
| descent 3-6 % | +1.0 % | +0.2 % | +1.2 % |
| descent 1-3 % | +0.5 % | −0.4 % | +1.3 % |
| flat ±1 % | −2.5 % | −0.7 % | −1.3 % |
| climb 1-3 % | +0.9 % | +0.1 % | +1.0 % |
| climb 3-6 % | +1.1 % | +1.0 % | −0.3 % |
| climb > 6 % | +0.4 % | −0.5 % | −1.8 % |

With a single CdA the error stays **within ±2.5 % across all seven bands**, from −6 % to +6 %
gradient. The only weak spot is the descent steeper than 6 % (4.6 % of the route), where what limits
the rider is braking and visibility, not physics.

And the CdA by both methods, across the five rides:

| Ride | by total-time fit | by out-and-back pairs |
|---|---|---|
| 30 Mar 2025 | 0.2758 | 0.2611 ± 0.0049 |
| 06 Apr 2025 | 0.2621 | 0.2661 ± 0.0087 |
| 04 May 2025 | **0.1550** | 0.2435 ± 0.0188 |
| 08 Jun 2025 | **0.2131** | 0.2542 ± 0.0095 |
| 19 Apr 2026 | 0.2583 | 0.2550 ± 0.0090 |
| **spread** | **21.3 %** | **3.3 %** (1.9 % with the impossible-pair filter) |

**The out-and-back pairs are reproducible and the total-time fit is not**, because the pairs cancel
the mean wind while total time absorbs it whole into the CdA. Hence the protocol uses the pairs as
the source of the figure. The 19 Apr 2026 ride agrees with the 2025 ones by both methods thirteen
months later: the CdA turns out to be stable over a year.

Isolated segments, one by one, give between 0.18 and 0.39 m² depending on the segment. That is **not
method spread**: it is the wind, and it shows up in the bearings. On top of that, **the selection
bias is quantified and the application declares it**: demanding high speed and little elevation
change is not a neutral sample — the chosen segments run at 36.3 km/h against the 31.4 km/h of the
route, with a mean gradient of −0.16 %. They are precisely the segments with a tailwind or a gentle
descent, which is why an isolated segment, however reliable its diagnosis looks, gives a low CdA.

The full report, with the per-band tables for each ride and the diagnosis of the two incoherent
ones, is in [`simulador-ciclismo-triatlon.validacion.md`](simulador-ciclismo-triatlon.validacion.md)
(Spanish).

### Finding: elevation noise matters more than expected

Total-time error (%) against the noise-free route, by smoothing window and i.i.d. elevation noise
(σ), on a rolling 30 km route with the default power profile (maximum over 4 seeds):

| σ noise | 100 m | 150 m (default) | 200 m | 300 m |
|---|---|---|---|---|
| 1 m | 0.36 | 0.63 | 0.53 | 0.33 |
| 2 m | **3.06** | 0.78 | 0.32 | 0.59 |
| 3 m | **8.23** | 2.35 | 0.83 | 0.41 |
| 5 m | **15.06** | 7.17 | 3.16 | 1.15 |

With a 10 m window the error is around 20 %. **If your GPX has noisy GPS elevation (σ ≥ 3 m), raise
the smoothing window** (advanced) or use a GPX with barometric or corrected elevation. Part of the
error comes from `P_descent = 0 W` turning gradient noise into fictitious descents.

## Known limitations

- **Wind is not an input to the model.** The wind of the real activity ends up absorbed into the
  estimated CdA (a bias, not noise). It is the underlying limitation of the whole tool.
- **The estimated CdA is an effective coefficient**, not a property of the bike: it includes wind,
  drafting, altimeter error, road surface and power meter bias. See
  [the dedicated section](#what-the-cda-this-tool-estimates-actually-is-and-what-it-is-not).
- **A single CdA** per bike (the switch to an upright position is modelled by speed alone), and it
  is the largest source of uncertainty: ±0.02 m² moves the time more than any fine adjustment of the
  terrain.
- **Transfer between routes is unverified:** the five reference rides are the same course, with
  94-98 % overlap. A ride of the same bike on another course is missing to close this.
- **Racing position is unverified:** the available data is from training.
- **Instantaneous speed:** still off by ±3 km/h MAE even when the total time is right.
- **`crr1` values** (variation of Crr with speed): estimates without solid experimental backing;
  calibrate them or leave them at the default.
- **Surface:** the GPX does not carry it; it is chosen globally and overridden by hand per km block.
- **Tyre pressure:** the model only lowers Crr as pressure rises. It does not represent that on a
  rough surface, above a certain pressure, the whole thing becomes slower. On rough surfaces at high
  pressure the result is optimistic.
- **Mass is mandatory:** the application will not simulate until the total mass is entered.
- **More mass can be faster** on routes with descents at 0 W (gravity scales with mass and
  aerodynamic drag does not).
- **Tables in dark mode:** they stay light, because Streamlit draws them on a canvas the CSS does not
  reach. This is a declared exception.
- **Scope of this version:** direct simulation only. No pacing optimiser, no inverse mode, no DEM
  and no surface extraction from OSM.
- GPX XML is parsed with `xml.etree` (personal use; do not expose it to untrusted files).

## Repository layout

```
core/                 Python/numpy core, no interface dependencies
  params.py           parameters, defaults, ranges, categories, validation (single source of truth)
  atmosphere.py       air density (temperature, humidity, pressure, altitude)
  route.py            GPX reading, resampling, smoothing, gradient and curvature
  physics.py          power by gradient, CdA(v), Crr(v) and per-segment solving
  simulate.py         full simulation + per-km-block table
  metrics.py          average power, NP, VI, IF
  sensitivity.py      ±10 % sensitivity of each parameter
  cda_estimator.py    CdA estimation: per segment, automatic search for flat segments
                      and out-and-back pairing along the same road
  coherence.py        activity coherence check: does it qualify for estimating?
  validation.py       .fit reading, replay of the real power and total-time fitting
  profiles.py         bike profiles (mass, CdA, Crr, η) with the provenance of the CdA
  wheels.py           ETRTO sizes and wheel circumference
  uncertainty.py      uncertainty bands obtained in the real validation
  exports.py          tables the application shows and downloads, with the bands included
  i18n.py             English translations and interface strings
  synthetic.py        synthetic routes (tests and example route)
app/streamlit_app.py  Streamlit interface, with the two modules
app/theme.py          design system: colour tokens, typefaces and the numeric-reading
                      and uncertainty-band components
.streamlit/config.toml  light theme by default and Streamlit top bar hidden
tests/                automated tests of the acceptance criteria
  fixtures/           5 real activities, reduced and anonymised; see their README
packaging/windows/    self-contained Windows package: build script, launcher and end-user notes
docs/calidad/         defect registry and independent reviews
simulador-ciclismo-triatlon.spec.md       the specification and its 32 acceptance criteria
simulador-ciclismo-triatlon.validacion.md validation report with real data
```

## Tests

```bash
python -m pytest -q        # 372 tests
run.sh --tests            # installs the test dependencies and runs them
```

They cover: physics (against an analytical solution and against an independent RK4 integration),
speed and curvature limits, continuity of CdA and of power, monotonicity, elevation noise, loop
symmetry, parameters and range validation, sensitivity, the `.fit` reader (with a minimal FIT writer
of our own), the CdA estimator and out-and-back pairing, the coherence check, bike profiles,
uncertainty bands, wheels, pressure, exports, both languages, the design system and the interface
with `streamlit.testing` (including the estimator tab end to end, uploading a real `.fit`).

The specific thresholds of each test and the criterion each one answers are in
[`simulador-ciclismo-triatlon.spec.md`](simulador-ciclismo-triatlon.spec.md) (Spanish). The quality
status, with the defect registry and the independent reviews, is in
[`docs/calidad/README.md`](docs/calidad/README.md).

---

# Español

Herramienta de uso personal que hace dos trabajos distintos:

1. **Estima el coeficiente de resistencia al avance (CdA)** de tu bici y tu posición a partir de
   una actividad real en `.fit`, cerrando el balance de energía sobre tramos llanos recorridos en
   los dos sentidos.
2. **Predice una carrera**: con el **GPX** del recorrido, ese CdA y un **perfil de potencia por
   pendiente** (subida / llano / descenso), calcula tiempo, velocidad y potencia por tramo con un
   modelo físico y parámetros editables.

Todo lo que sale de la herramienta va acompañado de su margen de incertidumbre. Ese es el criterio
de diseño del proyecto: **ningún número se presenta solo**, y lo que no está verificado se dice.

> **Qué es este repositorio y qué no.** Es una aplicación **Streamlit (Python)** que se ejecuta en
> tu ordenador con `./run.sh` o `run.bat` y abre el navegador en `localhost`. **No es una PWA
> instalable, no se publica en GitHub Pages y no hay APK**: Streamlit necesita un proceso Python
> detrás, y una PWA es un conjunto de ficheros estáticos. Reescribir el modelo en JavaScript (o
> correrlo en el navegador con Pyodide/stlite) es un proyecto aparte que obligaría a revalidar la
> física contra las cinco actividades reales.

## Características

**Estimación del CdA a partir de tus actividades**

- Lee `.fit` con GPS y potencia y estima el CdA cerrando el balance de energía, integrando
  intervalo a intervalo: no supone velocidad ni pendiente constantes.
- **Búsqueda automática de tramos fiables**: barre la actividad en ventanas de 1 a 5 km, se queda
  con los llanos, rápidos y sin solapes, y para cada uno localiza **la pasada de vuelta por la
  misma carretera**. Promediar ida y vuelta es la única forma de cancelar el viento sin modelarlo.
- **Selección manual** de un segmento, arrastrando sobre el perfil de la ruta o con un deslizador.
- Cada estimación llega con su **incertidumbre** (propagando error de altitud, de Crr y de sesgo
  del potenciómetro) y con un **diagnóstico de validez** del tramo: si no sirve, lo dice y no
  presenta el valor como bueno.
- **Examen de coherencia de la actividad**: antes de dar por bueno un CdA, comprueba si la salida
  es explicable por el modelo o si fue más rápida de lo que permite la potencia registrada
  (viento a favor, rebufo, grupo). Ver [¿sirve esta actividad?](#sirve-esta-actividad-examen-de-coherencia).
- **Pares imposibles descartados y a la vista**: un par de ida y vuelta cuyas velocidades difieran
  demasiado no mide viento, mide pendiente; se rechaza con su motivo escrito.
- Tabla con **una fila por segmento** y descarga en CSV, con el desglose de la incertidumbre por
  fuente.
- El resultado se lleva al simulador **con un botón**, y queda como un valor editable.

**Predicción de carrera**

- Carga de **GPX**, remuestreo a distancia constante, suavizado de elevación y de trazado.
- **Perfil de potencia por pendiente** con transición continua, umbral y anchura editables.
- Resultado con **tiempo total, velocidad media, tabla y gráficas por tramo, NP, VI e IF**.
- **Límite por curvatura** y tope de velocidad en descenso, con frenada máxima propagada hacia
  atrás; si el límite recorta la velocidad, la potencia aplicada se reduce a la necesaria y eso se
  refleja en NP/VI/IF.
- **Dos bandas de incertidumbre** que miden cosas distintas (modelo y día), las dos obtenidas de
  validación cruzada con actividades reales. Ver [cuánto fiarte](#cuánto-te-puedes-fiar-del-tiempo-predicho).
- **Informe de sensibilidad**: efecto en el tiempo total de cada parámetro a ±10 %, contrastado
  con los datos de tu ruta.
- **Perfiles de bici** con nombre, que guardan de dónde sale su CdA.
- Sin GPX cargado, una **ruta de ejemplo sintética** (~26 km) para probar.

**Transversal**

- **Español e inglés**, con selector en la barra lateral: etiquetas, tooltips de los 40 parámetros,
  pestañas, mensajes y avisos del estimador. Los CSV conservan los nombres técnicos de columna
  (`tiempo_s`, `cda`, `desnivel_m`) en los dos idiomas, a propósito, para no romper hojas de
  cálculo.
- **Tema claro por defecto y oscuro completo**, los dos derivados de los mismos tokens, gráficas
  incluidas.
- **Sistema de diseño propio** en un único módulo (`app/theme.py`), con lenguaje visual explícito
  para la incertidumbre: banda sólida y estrecha = estimado a partir de datos; banda rayada y
  ancha = margen del día o afirmación sin verificar.
- **Núcleo sin dependencias de interfaz** (`core/`): la física, el estimador y las tablas se
  pueden usar y verificar sin Streamlit.
- **372 tests automáticos** ligados a los 32 criterios de aceptación de la especificación.

## Requisitos

| | |
|---|---|
| **Python** | 3.9 o superior. Los lanzadores lo detectan y, si falta, lo dicen con el enlace de descarga |
| **Sistema** | Windows, macOS o Linux |
| **Dependencias de la app** | `numpy`, `pandas`, `streamlit`, `plotly`, `fitdecode` (`requirements.txt`) |
| **Dependencias de test** | las anteriores más `pytest` y `scipy` (`requirements-dev.txt`) |
| **Espacio** | unos 300 MB con el entorno virtual creado |
| **Navegador** | cualquiera reciente; la app se abre en `localhost` |

`scipy` es solo para los tests, que lo usan como solución de referencia independiente. **Arrancar
la app no instala dependencias de test**, y un test comprueba que todo lo que importan la app y el
núcleo esté declarado en `requirements.txt`.

Para estimar el CdA necesitas, además, una actividad en `.fit` **con GPS y potencia**, y
preferiblemente con algún tramo llano recorrido en los dos sentidos.

## Cómo se ejecuta

**Sin línea de comandos** (recomendado):

- **Windows:** doble clic en `run.bat`
- **macOS / Linux:** `./run.sh` en una terminal (en macOS, si prefieres el doble clic, renombra el
  archivo a `run.command`)

La primera vez crea un entorno virtual en `.venv` e instala las dependencias (un par de minutos);
las siguientes arranca directo. Si clonas el repositorio en macOS o Linux y `./run.sh` no arranca,
dale permiso de ejecución con `chmod +x run.sh`.

| Opción | Qué hace |
|---|---|
| `run.sh` / `run.bat` | abre la aplicación en el navegador |
| `run.sh --estimador` / `run.bat --estimador` | arranca directamente en el módulo de estimación de CdA |
| `run.sh --tests` | instala las dependencias de test y ejecuta los 372 tests |
| `run.sh --reinstalar` | rehace el entorno desde cero |
| `run.sh --reinstalar --tests` | las dos cosas |

A mano, si lo prefieres:

```bash
pip install -r requirements.txt          # app
pip install -r requirements-dev.txt      # app + tests
streamlit run app/streamlit_app.py       # desde la raíz del proyecto
python -m pytest -q                      # 372 tests
```

También se puede fijar el módulo inicial añadiendo `?modo=estimador` a la URL.

> `run.sh` está probado de punta a punta (entorno creado desde cero, aplicación respondiendo).
> **`run.bat` no se ha podido ejecutar en Windows**: está validado por inspección y por un lint
> estático de las trampas de `cmd`. Si te falla, manda lo que diga la ventana.

### Paquete autocontenido de Windows (sin instalar Python)

Para quien no tenga por qué instalar nada hay un paquete de Windows: una carpeta que lleva dentro
un Python embebido con todas las dependencias. Se descomprime la carpeta **completa** y se hace
doble clic en `TriTT.bat`.

- Lo construye el workflow `paquete-windows` en un runner limpio de `windows-latest`, nunca a
  mano, para que lo que se reparte salga de un commit identificable. Ejecutándolo desde la pestaña
  Actions queda como artefacto descargable; empujando una etiqueta `v*` se adjunta el ZIP a esa
  release.
- Para construirlo tú mismo: `pwsh -File packaging\windows\construir.ps1`.
- **No hay nada congelado** (nada de PyInstaller): es el mismo Python ejecutando el mismo código,
  solo que el intérprete viaja en la carpeta. Congelar Streamlit es frágil —arranca por su propio
  CLI, carga estáticos desde el directorio del paquete y lee metadatos con `importlib.metadata`—,
  así que cada actualización puede romper el empaquetado. La construcción comprueba que el
  intérprete empaquetado puede importar la aplicación, y falla antes que repartir una carpeta que
  no arranca.
- Los perfiles de bici se guardan en `%APPDATA%\TriTT-Bike-Simulator\`, no junto al programa, así
  que el paquete puede vivir en una ruta de solo lectura y sustituirlo no pierde los perfiles.
- El paquete **no está firmado digitalmente**, así que SmartScreen avisa la primera vez. El
  `LEEME.txt` que va dentro del ZIP explica eso, y todo lo demás, a alguien que no ha abierto una
  terminal en su vida.

## Los dos módulos y el flujo pensado

Se eligen con el selector **Qué quieres hacer** de la barra lateral:

| Módulo | Entra | Sale | Parámetros que pide |
|---|---|---|---|
| **Estimación de CdA** | una actividad `.fit` | el CdA de esa bici en esa posición, con su margen | 23 |
| **Predicción de carrera** | el GPX del recorrido y un CdA | tiempo, velocidad y potencia por tramo | 40 |

El orden importa, porque **el CdA es una entrada de la predicción y es el parámetro que más la
mueve**: una predicción hecha con el CdA por defecto no es una predicción de tu bici.

1. En el módulo de **estimación**, sube una actividad con el montaje y la posición que vas a llevar
   en carrera, y con algún tramo llano recorrido en los dos sentidos. Pulsa
   **🔍 Buscar tramos fiables**.
2. Lee el veredicto de coherencia y los avisos **antes** del número. Si la actividad no sirve, el
   CdA tampoco.
3. Pulsa el botón para **aplicar ese CdA**. Queda puesto en el simulador como un campo editable:
   úsalo tal cual o corrígelo a mano si tu montaje de carrera no es exactamente el de la actividad.
4. En el módulo de **predicción**, sube el GPX de la competición y di qué potencia piensas
   sostener.

El módulo de estimación **no pide un GPX** ni los parámetros que no intervienen en su cálculo.
Sobre todo, **no pide el CdA**: es lo que estima, y pedirlo como entrada sería circular. Tampoco
pide los perfiles de potencia, el FTP, los límites de velocidad y curvatura ni el remuestreo del
recorrido.

Esa partición vive en el núcleo (`core.params.specs_for_module`) y la vigila un test **empírico**:
cambiar un parámetro que el módulo no muestra no mueve la estimación, y cambiar uno de los que
muestra sí la mueve. La lista no se mantiene a mano.

## Qué es el CdA que estima esta herramienta (y qué no es)

Esto es lo más importante que hay que entender para usar los números con cabeza.

En el modelo, `CdA` es el **área de arrastre** (m², el producto del coeficiente de forma por el
área frontal) que multiplica al término aerodinámico `½·ρ·CdA·v²`. Pero el valor que la
herramienta **estima** no es un CdA de túnel de viento: sale de cerrar el balance de energía de un
tramo real. Lo que entró por los pedales, menos lo que se fue en subir, en rodadura y en cambiar la
energía cinética, se atribuye entero al término aerodinámico:

```
∫ η·P dt − Σ ½·m_ef·Δ(v²) − m·g·Σ Δh − ∫ Crr(v)·m·g·cosθ·v dt  =  ∫ ½·ρ·CdA·v³ dt
```

Como el CdA es **el residuo que hace cuadrar esa igualdad**, dentro de él acaba *todo* lo que se
opuso al avance y el modelo no nombra por separado:

| Dentro del CdA estimado | Cuánto pesa |
|---|---|
| La aerodinámica real (bici, cuerpo, casco, ropa, posición) | lo que de verdad se quiere conocer |
| **El viento neto del día** | **el término más grande, con diferencia**: 1 m/s mueve el resultado unos ±0,04–0,06 m², más que todos los demás errores juntos |
| Rebufo de otros ciclistas, vehículos o grupo | puede ser enorme y no se distingue del viento |
| Error del altímetro | ±1 m de desnivel en el tramo se propaga al resultado; en tramos cortos, lentos o con cuesta se traga la estimación entera |
| Diferencia entre el Crr elegido y el firme real | ±0,0005 de Crr, propagado |
| Sesgo del potenciómetro | ±1,5 % de la potencia, propagado |
| Cualquier error residual del propio modelo | va al mismo sitio, por construcción |

Así que, estrictamente, **lo que sale es un coeficiente efectivo de resistencia al avance** para
esa bici, esa posición y condiciones parecidas a las de la actividad — no una propiedad física de
la bici. Consecuencias prácticas:

- **El viento se descuenta emparejando, no modelando.** No es una entrada del modelo. Como es un
  **sesgo y no ruido**, no entra en la incertidumbre: se muestra aparte (banda rayada) y se cancela
  en primer orden promediando un tramo de ida con el mismo de vuelta. Por eso el valor recomendado
  es el de los **pares**, no el de un tramo suelto.
- **El rumbo de cada tramo delata el viento.** Si los tramos hacia un lado dan CdA bajo y los del
  contrario alto, eso es viento y no tu posición. La tabla trae esa columna por ese motivo.
- **Si cambias de equipación o de posición, hay que volver a estimarlo.** Lo que lleves puesto no
  es un parámetro del modelo: está dentro del CdA.
- **No lo compares con cifras de fabricante o de túnel de viento.** No miden lo mismo.
- **Un CdA obtenido en entrenamiento no es el de competición.** El perfil de ejemplo que acompaña
  al repositorio sale de salidas de 4 h a 210-226 W y 31-33 km/h: es un CdA de posición de
  entrenamiento.

### ¿Sirve esta actividad? Examen de coherencia

Cualquier método de ajuste **siempre** devuelve un número: busca el CdA que hace cuadrar las
cuentas y lo encuentra. Lo que no dice es si ese número significa algo. Si un día fuiste más rápido
de lo que permite la potencia que registraste, el ajuste baja el CdA hasta cuadrar el total y el
resultado no es un dato aerodinámico, sino el residuo de un ajuste que no cierra.

El examen detecta esa firma separando el error **por banda de pendiente**, y avisa si:

- el CdA que sale cae **fuera del rango plausible 0,20–0,35 m²**, o
- aparece el patrón **llano demasiado lento (error ≥ +5 %) y bajadas demasiado rápidas (≤ −4 %)**,
  que es lo que produce una salida con viento a favor, rebufo o grupo, y que un simple error de CdA
  no puede producir (los dos signos a la vez, no).

Hacen falta las dos reglas: una de las cinco salidas de referencia tiene el CdA dentro del rango y
solo la caza el patrón. Los umbrales están justificados con datos: en las tres salidas coherentes
el error en llano no pasa de −0,7 % y en bajadas de +0,8 %; en las dos incoherentes el llano está
en +15,8 % y +29,6 % y las bajadas en −7,9 % y −18,4 %. Hay un **orden de magnitud** entre la peor
coherente y la mejor incoherente.

El diagnóstico se construye en el núcleo (`core/coherence.py`), no en la interfaz, y usa
configuración fija a propósito: el veredicto no debe cambiar porque alguien haya tocado un
parámetro para predecir una carrera.

### Protocolo recomendado

1. Usa solo salidas de **la misma bici**.
2. **Pasa cada una por el examen de coherencia** y deja fuera las que avisen. Anota el motivo con
   el dato que lo respalda, no con una hipótesis.
3. Obtén el CdA con los **pares de ida y vuelta**, que es el método reproducible (3,3 % de
   dispersión entre salidas, 1,9 % con el filtro de pares imposibles, frente al 21,3 % del ajuste
   por tiempo total). El ajuste por tiempo total queda como **comprobación independiente**, no como
   fuente del dato.
4. Usa **al menos 2 salidas** coherentes y mira la dispersión entre ellas, no solo el mejor ajuste.
5. **No promedies salidas incoherentes** con las buenas: meterían el viento de su día en el
   parámetro.

### Cuándo un tramo no se da por bueno

Mínimos para considerar utilizable un tramo: **1 km**, 45 s, 25 km/h de media, que al menos la
**mitad** de la energía disipada sea aerodinámica e incertidumbre **≤ ±0,030 m²**. Un tramo que no
los cumpla aparece marcado como no utilizable y con el motivo escrito, no escondido.

## El modelo físico

Para cada tramo de longitud `d` sobre el firme, con potencia constante `P` y velocidades `v₀ → v₁`:

```
½·m_ef·(v₁² − v₀²) = d·( η·P / v̄ − ½·ρ·CdA(v̄)·(v₀²+v₁²)/2 − Crr(v̄)·m·g·cosθ ) − m·g·Δh
```

con `v̄ = (v₀+v₁)/2` y `m_ef = m + I/r²` (inercia de las ruedas). Esta forma es exacta para potencia
constante y aceleración uniforme. Se resuelve por tramo con regula falsi (Illinois); si hay varias
soluciones (zona de transición de CdA) se elige la más próxima a `v₀`, siguiendo la trayectoria
real. El tiempo del tramo es `d·2/(v₀+v₁)`.

| Elemento | Modelo |
|---|---|
| **Masa** | un único valor total (ciclista + bici + equipo). El reparto no entra en ninguna ecuación: solo la suma |
| **Potencia por pendiente** | `P(g)` = llano / subida / descenso con transición *smoothstep* continua; umbral (±2 %) y anchura editables |
| **CdA(v)** | `CdA + ΔCdA·σ((v₀ − v)/w)`, logística centrada en 20 km/h (por defecto ΔCdA = +0,25 m², w = 1 km/h). Continuo, sin saltos |
| **Crr(v, p)** | `Crr_ref·(p_ref/p)^exp + crr1·(v − 29 km/h)` por superficie (liso / normal / rugoso); `Crr_ref` se define a 29 km/h y a la presión de referencia. Suelo en 0,5·Crr_ref |
| **Rueda** | el perímetro sale de la medida ETRTO (defecto 28-622) o se introduce medido con la opción «manual»; el radio se deduce de él. Solo entra en la inercia de rotación y mueve el tiempo menos del 0,001 % |
| **ρ** | aire húmedo: temperatura, humedad (Magnus), presión a nivel del mar corregida con la altitud de cada punto (ISA) |
| **Límite por curvatura** | `v ≤ √(a_lat/κ)` (activo por defecto, `a_lat` = 3 m/s²), con frenada máxima (3 m/s²) propagada hacia atrás; κ por derivada del rumbo con dilatación a los extremos del arco. Fiable para R ≥ max(10 m, ventana de trazado/7); por debajo es **optimista** (+4,5 % de velocidad a R = 8 m, +16,3 % a R = 4 m) |
| **Tope de velocidad** | 100 km/h por defecto |
| **Potencia aplicada** | si el límite recorta la velocidad, la potencia aplicada se reduce a la necesaria (≥ 0), y eso se refleja en NP/VI/IF |
| **NP / VI / IF** | NP: media móvil 30 s a 1 Hz y media de 4.ª potencia; VI = NP/media; IF = NP/FTP |

**Suavizado del GPX:** remuestreo a distancia constante (20 m), suavizado gaussiano de la elevación
(ventana 150 m) y del trazado (60 m), pendiente limitada a ±30 %.

### Parámetros (valores por defecto: nivel del mar, A Coruña)

| Categoría | Parámetros principales | Avanzados |
|---|---|---|
| **Ciclista** | masa total (**obligatoria**, sin valor por defecto) · P subida/llano/descenso 220/200/0 W · FTP (opcional) | umbral de pendiente 2 %, anchura de transición 1 %, velocidad inicial 18 km/h |
| **Equipamiento** | CdA 0,27 m² · ΔCdA 0,25 m² · η 0,975 · rueda ETRTO 28-622 (o perímetro medido) | umbral de posición 20 km/h, anchura 1 km/h, inercia 0,14 kg·m² |
| **Variables externas** | temperatura 15 °C · humedad 75 % · superficie (liso/normal/rugoso) · presión 7,0 bar · tramos por km · velocidad máx. 100 km/h · límite por curvatura | presión atmosférica 1013,25 hPa, densidad manual, Crr por superficie, variación de Crr con v, a_lat, frenada, ventanas de suavizado, paso, umbral de pares imposibles |

La clasificación principal/avanzado es una decisión de diseño. La pestaña **Sensibilidad** la
contrasta con los datos de tu ruta (columna `sugerencia`).

## Perfiles de bici

Cada montura tiene su propio CdA y sus propias masas, así que la aplicación guarda **perfiles con
nombre** (`perfiles_bici.json`, junto al proyecto; se puede cambiar con la variable de entorno
`SIMCICLISMO_PERFILES`). Un perfil fija masas, CdA, ΔCdA, η, Crr, superficie e inercia, y guarda
además **el origen del CdA**: de qué actividades sale y si está calibrado o es un valor por
defecto. Un CdA guardado sin ese origen no es trazable y la aplicación lo marca como *sin
calibrar*.

`perfiles_bici.ejemplo.json` contiene el perfil obtenido con los pares de ida y vuelta sobre las 3
salidas coherentes del recorrido de referencia (CdA 0,261 m², masa total 90 kg). Renómbralo a
`perfiles_bici.json` para usarlo. Es un CdA de **posición de entrenamiento**: para competir,
estima el tuyo con una actividad que lleve el montaje y la posición de carrera.

## Cuánto te puedes fiar del tiempo predicho

La aplicación muestra siempre el tiempo con su margen, con **dos bandas que miden cosas
distintas** — por eso se dan las dos y no la media ni la mejor:

| Banda | Valor | Qué mide y de dónde sale |
|---|---|---|
| **Precisión del modelo** | **±1,4 %** | Validación cruzada dejando una fuera con las 3 salidas coherentes del recorrido de referencia; error medio 0,94 %, máximo 1,39 %. Es lo que vale el modelo físico con la misma bici y ruta cuando el día no se sale de lo normal |
| **Margen del día** | **±15 %** | Obtenido con el protocolo que la propia herramienta recomienda: calibrando solo con las 3 salidas coherentes y prediciendo cualquier día, incluidos los 2 incoherentes. Peor error **14,27 %**. Es lo que cuesta no saber qué viento hizo |

Las tablas y los CSV traen, por cada columna de tiempo, cuatro columnas más (`_min_modelo`,
`_max_modelo`, `_min_dia`, `_max_dia`), para que ningún tiempo salga de la herramienta sin su
margen.

**En una ruta nueva no hay banda verificada.** El margen del día es un **suelo**, no una
estimación: ninguna validación ha podido cruzar de ruta, porque no hay salidas de esta bici por
otro recorrido. El ±11 % que esta tabla daba en versiones anteriores quedó retirado por
incoherente: era *menor* que el margen por viento ya observado en la propia ruta de calibración.

### Resultados con los datos reales (5 salidas del mismo recorrido, mar-2025 a abr-2026)

El modelo se validó separando el error **por banda de pendiente**, que es más exigente que el
tiempo total: un ajuste global puede acertar compensando errores opuestos, y esto no.

| Banda de pendiente | 30-mar | 06-abr | 19-abr-26 |
|---|---|---|---|
| bajada > 6 % | −7,7 % | −1,6 % | +0,6 % |
| bajada 3-6 % | +1,0 % | +0,2 % | +1,2 % |
| bajada 1-3 % | +0,5 % | −0,4 % | +1,3 % |
| llano ±1 % | −2,5 % | −0,7 % | −1,3 % |
| subida 1-3 % | +0,9 % | +0,1 % | +1,0 % |
| subida 3-6 % | +1,1 % | +1,0 % | −0,3 % |
| subida > 6 % | +0,4 % | −0,5 % | −1,8 % |

Con un solo CdA el error se queda **dentro de ±2,5 % en las siete bandas**, de −6 % a +6 % de
pendiente. El único punto flojo es la bajada de más del 6 % (4,6 % de la ruta), donde lo que limita
al ciclista es la frenada y la visibilidad, no la física.

Y el CdA por los dos métodos, en las cinco salidas:

| Salida | por ajuste de tiempo total | por pares de ida y vuelta |
|---|---|---|
| 30-mar-2025 | 0,2758 | 0,2611 ± 0,0049 |
| 06-abr-2025 | 0,2621 | 0,2661 ± 0,0087 |
| 04-may-2025 | **0,1550** | 0,2435 ± 0,0188 |
| 08-jun-2025 | **0,2131** | 0,2542 ± 0,0095 |
| 19-abr-2026 | 0,2583 | 0,2550 ± 0,0090 |
| **dispersión** | **21,3 %** | **3,3 %** (1,9 % con el filtro de pares imposibles) |

**Los pares de ida y vuelta son reproducibles y el ajuste por tiempo total no**, porque los pares
cancelan el viento medio y el tiempo total lo absorbe entero en el CdA. De ahí que el protocolo use
los pares como fuente del dato. La salida del 19-abr-2026 encaja con las de 2025 por los dos
métodos trece meses después: el CdA resulta estable a lo largo de un año.

Los tramos sueltos, uno a uno, dan entre 0,18 y 0,39 m² según el tramo. Eso **no es dispersión de
método**: es el viento, y se ve en los rumbos. Además, **el sesgo de selección está cuantificado y
la aplicación lo declara**: exigir velocidad alta y poco desnivel no da una muestra neutra — los
tramos elegidos van a 36,3 km/h frente a los 31,4 km/h de la ruta, con una pendiente media de
−0,16 %. Son justo los tramos con viento a favor o bajada suave, y por eso un tramo suelto, por muy
fiable que parezca su diagnóstico, da un CdA bajo.

El informe completo, con las tablas por banda de cada salida y el diagnóstico de las dos
incoherentes, está en [`simulador-ciclismo-triatlon.validacion.md`](simulador-ciclismo-triatlon.validacion.md).

### Hallazgo: el ruido de elevación manda más de lo esperado

Error del tiempo total (%) frente a la ruta sin ruido, según la ventana de suavizado y el ruido
i.i.d. de elevación (σ), en una ruta ondulada de 30 km con el perfil de potencia por defecto
(máximo de 4 semillas):

| σ ruido | 100 m | 150 m (defecto) | 200 m | 300 m |
|---|---|---|---|---|
| 1 m | 0,36 | 0,63 | 0,53 | 0,33 |
| 2 m | **3,06** | 0,78 | 0,32 | 0,59 |
| 3 m | **8,23** | 2,35 | 0,83 | 0,41 |
| 5 m | **15,06** | 7,17 | 3,16 | 1,15 |

Con ventana de 10 m el error ronda el 20 %. **Si tu GPX tiene elevación GPS ruidosa (σ ≥ 3 m), sube
la ventana de suavizado** (avanzado) o usa un GPX con elevación barométrica o corregida. Parte del
error viene de que `P_descenso = 0 W` convierte el ruido de pendiente en descensos ficticios.

## Limitaciones conocidas

- **El viento no es una entrada del modelo.** El de la actividad real queda absorbido en el CdA
  estimado (sesgo, no ruido). Es la limitación de fondo de toda la herramienta.
- **El CdA estimado es un coeficiente efectivo**, no una propiedad de la bici: incluye viento,
  rebufo, error de altímetro, firme y sesgo del potenciómetro. Ver
  [la sección dedicada](#qué-es-el-cda-que-estima-esta-herramienta-y-qué-no-es).
- **CdA único** por bici (el cambio a posición convencional se modela solo por velocidad), y es la
  mayor fuente de incertidumbre: ±0,02 m² mueven el tiempo más que cualquier ajuste fino del
  terreno.
- **Transferencia entre rutas sin verificar:** las cinco salidas de referencia son el mismo
  recorrido, con un 94-98 % de solape. Falta una salida de la misma bici por otro recorrido para
  cerrarlo.
- **Posición de carrera sin verificar:** los datos disponibles son de entrenamiento.
- **Velocidad instantánea:** sigue fallando ±3 km/h de MAE aunque el tiempo total acierte.
- **Valores de `crr1`** (variación de Crr con la velocidad): estimaciones sin respaldo experimental
  sólido; calíbralos o déjalos en el defecto.
- **Superficie:** el GPX no la trae; se elige global y se sobrescribe a mano por tramos de km.
- **Presión de neumáticos:** el modelo solo baja el Crr al subir la presión. No representa que en
  firme rugoso, por encima de cierta presión, el conjunto se vuelva más lento. En rugoso y a mucha
  presión el resultado es optimista.
- **Masa obligatoria:** la aplicación no simula hasta introducir la masa total.
- **La masa mayor puede ser más rápida** en rutas con descensos a 0 W (la gravedad escala con la
  masa y la resistencia aerodinámica no).
- **Tablas en modo oscuro:** se quedan claras, porque Streamlit las dibuja en un lienzo al que no
  llega el CSS. Es una excepción declarada.
- **Alcance de esta versión:** solo simulación directa. Sin optimizador de pacing, sin modo
  inverso, sin DEM y sin extracción de superficie desde OSM.
- XML del GPX parseado con `xml.etree` (uso personal; no exponer a archivos no confiables).

## Estructura del repositorio

```
core/                 núcleo en Python/numpy, sin dependencias de interfaz
  params.py           parámetros, defaults, rangos, categorías, validación (única fuente de verdad)
  atmosphere.py       densidad del aire (temperatura, humedad, presión, altitud)
  route.py            lectura de GPX, remuestreo, suavizado, pendiente y curvatura
  physics.py          potencia por pendiente, CdA(v), Crr(v) y resolución por tramo
  simulate.py         simulación completa + tabla por bloques de km
  metrics.py          potencia media, NP, VI, IF
  sensitivity.py      sensibilidad ±10 % de cada parámetro
  cda_estimator.py    estimación del CdA: por segmento, búsqueda automática de tramos llanos
                      y emparejado de ida y vuelta por la misma carretera
  coherence.py        examen de coherencia de una actividad: ¿sirve para estimar con ella?
  validation.py       lectura de .fit, reproducción de la potencia real y ajuste por tiempo total
  profiles.py         perfiles de bici (masa, CdA, Crr, η) con el origen del CdA
  wheels.py           medidas ETRTO y perímetro de rueda
  uncertainty.py      bandas de incertidumbre obtenidas en la validación real
  exports.py          tablas que la aplicación muestra y descarga, con las bandas incorporadas
  i18n.py             traducciones al inglés y cadenas de la interfaz
  synthetic.py        rutas sintéticas (tests y ruta de ejemplo)
app/streamlit_app.py  interfaz en Streamlit, con los dos módulos
app/theme.py          sistema de diseño: tokens de color, tipografías y los componentes
                      de lectura numérica y de banda de incertidumbre
.streamlit/config.toml  tema claro por defecto y barra superior de Streamlit oculta
tests/                tests automáticos de los criterios de aceptación
  fixtures/           5 actividades reales reducidas y anonimizadas; ver su README
packaging/windows/    paquete autocontenido de Windows: script de construcción, lanzador y LEEME
docs/calidad/         registro de defectos y revisiones independientes
simulador-ciclismo-triatlon.spec.md       especificación y sus 32 criterios de aceptación
simulador-ciclismo-triatlon.validacion.md informe de validación con datos reales
```

## Tests

```bash
python -m pytest -q        # 372 tests
run.sh --tests            # instala las dependencias de test y los ejecuta
```

Cubren: física (contra solución analítica y contra una integración RK4 independiente), límites de
velocidad y curvatura, continuidad de CdA y de potencia, monotonía, ruido de elevación, simetría de
circuitos, parámetros y validación de rangos, sensibilidad, lector de `.fit` (con un escritor FIT
mínimo propio), estimador de CdA y emparejado de ida y vuelta, examen de coherencia, perfiles de
bici, bandas de incertidumbre, ruedas, presión, exportaciones, los dos idiomas, el sistema de
diseño y la interfaz con `streamlit.testing` (incluida la pestaña del estimador de punta a punta,
subiendo un `.fit` de verdad).

Los umbrales concretos de cada test y el criterio al que responde están en
[`simulador-ciclismo-triatlon.spec.md`](simulador-ciclismo-triatlon.spec.md). El estado de la
calidad, con el registro de defectos y las revisiones independientes, en
[`docs/calidad/README.md`](docs/calidad/README.md).
