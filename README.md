# Invariant Ledger for Blender

An **in-app scientific validation add-on**: declare a geometric contract, measure
the consequences of selected Geometry Nodes/object-scale edits, then test those
edits individually in a clean Blender process.

[Interactive explanation](https://az9713.github.io/rea-blender-invariants/) ·
[Installable release](https://github.com/az9713/rea-blender-invariants/releases/tag/v0.1.0) ·
[Pinned investigation](investigation/COMPARISON.md)

## The meaningful before/after

| Before | With Invariant Ledger |
|---|---|
| A node diff shows that a scale input changed | Evaluated world-space area, volume, bounds and topology show the scientific consequence |
| A scene looks plausible after an AI edit | Explicit ratio intervals and topology requirements produce a pass/fail contract |
| Multiple edits leave attribution uncertain | A separate process evaluates each declared edit alone against the same baseline |
| A cache or image silently changes between runs | Its recorded SHA-256 must match independently in the child process |
| Undo/checkpoints restore a scene | A hashed baseline plus bounded operations must reproduce the selected mesh summaries |

The synthetic example starts with volume **8** and area **24**. Changing the exposed
GN scale to **2** and object scale to **1.25** yields volume **125** and area **150**.
Each isolated edit gives volume **64** or **15.625**. Their joint result is nonlinear;
the add-on measures the counterfactuals instead of guessing an additive explanation.

## Install and use inside Blender

Tested on a separately acquired **Blender 5.2.3 LTS**, build `e13b728c6880`.

1. Download `InvariantLedger-0.1.0-addon.zip` from Releases.
2. In Blender Preferences → Add-ons → Install from Disk, select the ZIP and enable
   **Invariant Ledger**. The native test uses those actual installation/enable APIs.
3. Select a mesh object. Open the 3D View sidebar (`N`) → **Invariant Ledger**.
4. Choose a workspace and declare area/volume ratio intervals. Put external files
   to be audited inside that workspace; optionally name one cache-identity file.
5. Choose **Capture baseline and contract**. This writes a **copy** of the scene as
   `baseline.blend` plus `capture.json`, without replacing the active document.
6. Edit the object's scale and/or exposed scalar GN inputs. Choose **Measure and
   explain changes**. The panel shows ratios, violations, declared edits and flags.
   Complete evidence is also a Blender Text datablock, `InvariantLedgerEvidence`.
7. Choose **Export and verify clean-process replay**. A separate Blender process
   verifies hashes, reopens the baseline with auto-execution disabled, evaluates
   each edit alone, applies both/all edits and compares the recorded summaries.

Capture fixes the contract. Changing the UI interval fields later does not silently
rewrite it; recapture explicitly. Keep prior evidence elsewhere before recapturing
the same workspace, because `baseline.blend` and the manifest are replaced.

`InvariantLedger-0.1.0-example.zip` contains the original synthetic baseline,
portable relative asset paths, manifest, expected evidence and dependencies. Extract
it into a directory. The `.blend` contains the baseline; the manifest supplies the
declared later edits. No user scene or proprietary runtime is bundled.

## What the verification proves

**12 pure policy tests and 10 real Blender integration checks pass.** Native checks
install/enable the candidate ZIP, hash-compare installed source, evaluate Geometry
Nodes, invoke the actual operators, verify a different replay PID, measure isolated
counterfactuals, reject cache tampering, flag untracked edits and refuse open-mesh
volume. `artifacts/integration-results.json` fingerprints the tested code.

The replay compares exact vertex/edge/face/triangle counts, component/Euler/boundary
summaries, and tolerant area/volume/axis-aligned bounds (`1e-6`). It **does not prove
full mesh equality, scientific correctness, render equivalence or arbitrary
simulation reproducibility**. Baseline/expected summaries can match for different
shapes; the scope is explicit in every replay report.

The panel and operators were registered/executed in the native headless host.
Hidden-window GUI screenshot attempts encountered a native Blender access
violation on this laptop, so complete GUI drawing is **unverified**. The website's
before/after images are actual **CPU renders of original synthetic geometry**,
not panel screenshots or a render-equivalence test. An optional GUI smoke script
is supplied so this remaining check can be retried on another supported display.

## Reproduce locally

The pure core needs Python 3.9+; acquisition/build helpers use Python 3.11+:

```powershell
python -m unittest discover -s tests -p test_core.py -v
python scripts/acquire_blender.py
python scripts/stage_addon.py
./scripts/run_portable.ps1
./scripts/run_portable.ps1 -Script tests/render_fixture.py
python scripts/build.py
```

The official portable archive is downloaded from a Blender mirror and checked
against the publisher's SHA-256. All downloads, extracted runtime, configuration,
scripts, datafiles, home/AppData and caches remain inside `.runtime`. The launcher
uses factory startup, disabled auto-execution, one thread and an explicit Python
failure exit code. The child process receives a fresh isolated configuration too.
No installed Blender app or private profile is used.

Optional GUI retry, with a hidden owned process and a 60-second timeout:

```powershell
./scripts/run_portable.ps1 -Gui -Script tests/gui_smoke.py
```

The release build uses exact package/fixture paths, verifies pinned source and
tested-code hashes, requires all native checks passing and rejects ZIP path
escapes. Every HTML file lives under `docs/` for GitHub Pages.

## Scope and refusal rules

Supported replay controls: positive object-scale triples and exposed **constant
float/int/bool** GN modifier inputs. The adapter uses Blender 5.2's
`modifier.properties.inputs` RNA API, not removed legacy ID-property assignment.
A small reviewed node set defines the initial replay scope; others are flagged.

Changing the internal graph, base mesh, untracked transform or frame; using
unreviewed modifiers/nodes, parents/constraints/animation/shape keys; or changing
external dependencies blocks supported replay. Simulation/time nodes are outside
the reviewed set. Missing/outside-workspace/oversized files are flagged without
being hashed. Persistent file-backed image IDs, packed images and one declared
cache file are covered; this is not exhaustive discovery of every possible scene
dependency. File hashing is capped at 64 MiB each.

Open, nonmanifold, loose or inconsistently wound meshes report unsupported volume.
Surface measurements are in world units; physical units remain the user's modeling
responsibility. These limits make the result inspectable rather than implying a
universal Blender history or simulation replay engine.

This public-source/API investigation complements native undo and existing
NodeSync/history/checkpoint tools. No binary reverse-engineering success is claimed.
Original code: **GPL-2.0-or-later**. See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE).
