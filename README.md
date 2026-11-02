# Invariant Ledger for Blender

A model can still look fine after an edit even when it has become much larger than you intended. This add-on lets you save a few rules about its size and mesh structure, then check whether your edits broke those rules.

Suppose you are making a part that must stay near its original size, or exploring a design without wanting its volume to change too much. Looking at the viewport is a poor way to judge that. Making a solid twice as wide, tall and deep gives it eight times the volume, not twice the volume.

**Example:** The cube below starts with sides of 2 units: volume 8 and surface area 24. One size control multiplies each side by 2; another multiplies it by 1.25. Together they make each side 5 units, so volume becomes 125 and area becomes 150. The added feature is the report that explains this jump and flags the example's chosen 20% limits. Making the cube bigger is ordinary Blender behavior.

**What you install:** An experimental Blender add-on for checking model changes.

**Current scope:** The calculations and repeat runs were tested in Blender 5.2.3. The sidebar still needs a test in a normal Blender window. This release handles a narrow set of scale changes; it is not a general check of every modeling operation, simulation or 3D-printing requirement.

[Live guide](https://az9713.github.io/rea-blender-invariants/) · [Download packages](https://github.com/az9713/rea-blender-invariants/releases/tag/v0.1.1)

<!-- rea-release-expectations:start -->
## What to expect from this release

**Status: experimental.** Read the tested scope and remaining work below before choosing this release for your workflow.

- **What you get:** An add-on intended to run inside Blender, with a separate browser explanation. It checks supported model changes; it is not a replacement Blender executable.
- **Verified so far:** Size and mesh-structure measurements, recorded scale changes, repeat checks in fresh Blender processes, extracted release checks and native CPU renders were executed.
- **Still needs testing or implementation:** The sidebar panel and a complete interactive modeling session still need testing in a normal Blender window.
- **Relationship to the original app:** Supported object-scale and Geometry Nodes size changes are a small part of Blender. Passing these checks does not certify arbitrary modifiers, simulations, manufacturing suitability or every modeling edit.

<!-- rea-release-expectations:end -->

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

1. Download `InvariantLedger-0.1.1-addon.zip` from Releases.
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

`InvariantLedger-0.1.1-example.zip` contains the original synthetic baseline,
portable relative asset paths, manifest, expected evidence and dependencies. Extract
it into a directory. The `.blend` contains the baseline; the manifest supplies the
declared later edits. No user scene or proprietary runtime is bundled.

## Release fixture privacy repair (0.1.1)

The previous 0.1.0 example scene retained local folder text in cached file-selector metadata and stale bytes after a valid relative image filename. The .blend used Zstandard compression, so scanning only its enclosing ZIP did not inspect those bytes. The add-on source itself contained no such build paths.

The new release regenerates our synthetic scene uncompressed, clears two bounded printable metadata/padding spans without changing any binary block length or address, updates the baseline SHA and replay manifests, then reopens/replays it in real Blender. The active relative image path remains valid; image/cache hashes and measured Geometry Nodes outputs still match. See [exact fixture report](artifacts/fixture-privacy.json).

This helper is only for the owned, pinned Blender 5.2 synthetic fixture. It is not an arbitrary user-document sanitizer and does not run during normal add-on capture. The render pipeline also removes PNG textual/EXIF metadata while preserving every IDAT image byte, because Blender embeds scene filenames even without visible stamp text. See [render privacy report](artifacts/render-privacy.json). Review your own .blend and embedded metadata before publishing. The original 0.1.0 local archives are preserved as incident evidence; the GitHub distributor should retire its old example download after validating this replacement.

## What the verification proves

**26 pure tests and 11 real Blender integration checks pass.** Native checks
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
python -m unittest discover -s tests -p 'test_*.py' -v
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
