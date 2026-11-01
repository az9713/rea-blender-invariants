# Scientific evidence above a node-history layer

This is an application extension implemented through public Python APIs and pinned
source. No native/binary reverse-engineering success is claimed. A compiled-only
discrepancy was not necessary to deliver this bounded change.

## Existing implementations

| Existing feature/project | Already available | Delivered scientific distinction |
|---|---|---|
| Native undo/repeat/history | Standard reversible edits and repeat operations; exposed in pinned `space_topbar.py` | A numerical contract can fail even when an undo/restore operation succeeds |
| [NodeSync](https://github.com/sneeezed/nodesync) | Git-backed node snapshots, restore, branching and visual node diffs | Measures evaluated mesh results and tests declared controls individually in a clean process |
| [Undo History](https://superhivemarket.com/products/undohistory/faq/new) | Author describes persistent history including Geometry Nodes | Explicit area/volume/topology limits and unsupported-volume flags |
| [Blender Bridge](https://github.com/Blender-Bridge/blender-bridge) | AI edits and scene checkpoints; documented rollback limits for exports/caches | SHA-256 dependency identities and independently checked replay preconditions |

The ecosystem search was bounded; it does not prove no existing product can supply
these checks. These comparisons avoid calling ordinary node history a novel feature.

## Source observation that changed the implementation

Actual Blender **5.2.3** rejected legacy `modifier[identifier] = value` with
`TypeError: id properties not supported for this type`. The shipped source and
[5.2 API](https://docs.blender.org/api/5.2/bpy.types.NodesModifier.html) expose
`modifier.properties.inputs`. The pinned `geometry_nodes.py` uses
`getattr(modifier.properties.inputs, identifier)`. The adapter now reads/writes that
RNA property's `value` and refuses attribute-driven scalar inputs.

This is a verified version-specific API adaptation, not an unexplained native
mechanism. The source commit matches `bpy.app.build_hash`, and packaging checks the
collected file hashes.

## What the clean-process test establishes

The fixture captures a Geometry Nodes cube with volume 8 and area 24. It then
changes the exposed uniform GN scale to 2 and the object scale to 1.25. Measured
volume becomes 125 and area 150, violating the default 0.8–1.2 ratio intervals.

A separate Blender process reopens the SHA-256-pinned baseline, verifies image and
declared cache identities, checks the node graph and baseline controls, and evaluates
each edit alone. The isolated volumes are 64 and 15.625. Applying both yields 125.
This demonstrates nonlinear composition, not additive attribution by guesswork.

The child compares exact mesh counts/connectivity summaries and tolerant area,
volume and axis-aligned bounds. A match proves equivalence **only for those
summaries**. It does not prove full mesh equality, material/render equivalence,
physical correctness or arbitrary simulation reproducibility.

## Explicit unsupported boundaries

Unreviewed modifiers/nodes, simulation/time-driven nodes, changing the node graph,
editing base mesh data, untracked transforms, animation/constraints/parenting,
shape keys, changed frame or external identities block the supported replay path.
Open, loose, nonmanifold or inconsistently wound meshes cannot claim volume.
Persistent image IDs and one explicitly declared cache file are audited; this is
not an exhaustive discovery of every file or runtime side effect a scene can use.

Only files inside the chosen workspace are hashed (64 MiB per-file limit). Other
paths are flagged without being read. No unknown Python expression or executable
from a manifest is evaluated, and replay opens the baseline with auto-execution
disabled. These restrictions define a useful experiment rather than a universal
Blender history/reproducibility engine.
