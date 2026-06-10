# OpenPBR Version Conversion

`openpbr_version.py` converts an **OpenPBR Surface** parameter set between
specification versions, in either direction, choosing the parameter
correspondence that produces the **closest match of the resulting
appearance**.

It is both a Python API and a command-line tool, and is architected so that
each new release (1.3, …) is added as a single *adjacent* migration step; any
multi-version conversion is then composed automatically.

---

## 1. What a version converter can and cannot do

A material's appearance is determined by its parameters **and** by the fixed
shading math of the version that renders it. A version converter only changes
parameters, so it can only compensate for differences that are themselves
*parameterized*. Every difference between two versions therefore falls into one
of three classes:

| Class | Meaning | Converter action |
|-------|---------|------------------|
| **A — Exactly invertible** | A pure reparametrization. After the remap the appearance is identical. | Apply the closed-form map. |
| **B — Lossy / bounded** | Mappable over part of the parameter domain; outside it the two versions genuinely diverge. | Map where possible; clamp + **warn** elsewhere. |
| **C — Not parameter-correctable** | An internal change to the BSDF or the reference MaterialX graph. No parameter controls it, so no remap can undo it. | Make **no** parameter change; emit a **note**. |

The converter reports Class-B divergence as `warnings` and Class-C divergence
as `notes` on the `ConversionResult`. A clean (warning-free, note-free) result
means the conversion is exact for that material.

> **Key consequence.** "Closest appearance match" is an *honest* goal, not a
> perfect one. Two materials that differ only by Class-A parameters render
> identically across versions; materials that exercise Class B or C will differ,
> and the converter tells you exactly where and why.

---

## 2. Architecture

### The version ladder

Versions are linearly ordered in `VERSION_ORDER`:

```python
VERSION_ORDER = ("1.1", "1.2")        # extend with "1.3", …
```

Because the ladder is linear, the path between any two versions is an
unambiguous walk up or down — no graph search is needed.

### Adjacent migrations

Each *adjacent* pair is described by one `Migration`, holding both directions:

```python
@dataclass
class Migration:
    older: str
    newer: str
    upgrade: object     # rule(params, out, warnings, notes): older -> newer
    downgrade: object   # rule(params, out, warnings, notes): newer -> older

MIGRATIONS = [
    Migration("1.1", "1.2", _upgrade_1_1_to_1_2, _downgrade_1_2_to_1_1),
]
```

A **rule** is a callable `rule(params, out, warnings, notes)` that reads the
source `params` dict, mutates `out` (a shallow copy of `params`, which starts as
a pass-through of every parameter), and appends any `warnings` / `notes`.

### Composition

`convert_params` builds the ordered list of adjacent steps with `_build_chain`
and applies them in sequence, feeding the parameter set produced by each step
into the next:

```
1.1 → 1.3   ==   apply(_upgrade_1_1_to_1_2)  then  apply(_upgrade_1_2_to_1_3)
1.3 → 1.1   ==   apply(_downgrade_1_3_to_1_2) then apply(_downgrade_1_2_to_1_1)
```

When more than one hop runs, each warning/note is prefixed with its hop label
(e.g. `[1.2→1.3]`) so multi-version diagnostics stay attributable. Single-hop
output is unprefixed.

The intermediate parameter set after step *n* is, by construction, a valid
parameter set in the intermediate version, so step *n+1*'s defaults and rules
apply correctly.

### Two layers

* **`convert_params(params, from_version, to_version)`** — the dependency-free
  core. Operates on a plain `{name: value}` dict (values are floats or
  3-sequences for `color3`). Imports only the standard library, so any
  application or renderer can embed it.
* **`convert(input_path=…/input_string=…, from_version, to_version, output_path=…)`**
  — a MaterialX `.mtlx` document wrapper (requires the `MaterialX` package).
  It reads the `open_pbr_surface` shader instance, runs the core, and writes the
  converted parameters back, touching only the inputs the conversion changed.

### Valued vs. connected inputs

Whether a parameter is a literal **value** or **connected** to another node is
never something the caller specifies — the two layers handle it differently:

* The **core** has no concept of connections. It sees only values, so a
  connected (texture-driven) parameter is simply *absent from the dict*.
  Connection handling is the integrating application's concern.
* The **wrapper** reads connectivity *from the document*: a MaterialX `<input>`
  is "valued" if it has a `value=` attribute and "connected" if it instead has
  `nodename=` / `nodegraph=` / `output=` / `interfacename=` (then
  `getValueString()` is empty). Connected inputs are passed through untouched.

Most maps need no special handling for connected inputs, but the **coupled**
maps (whose result depends on *another* parameter) do:

* **`emission_weight` (1.1 → 1.2)** must be authored as the constant `1` even
  when `emission_luminance` is connected, or the textured emission goes dark
  (the new weight defaults to 0). `weight = 1` is exact regardless of how
  luminance is driven, so the wrapper detects a connected `emission_luminance`
  and sets it (with a warning). The valued case is handled by the core.
* **`transmission_scatter` (the `Ω = −S/ln T` albedo remap)** depends on
  `transmission_color`. If either input is node-driven, the result cannot be
  reduced to a constant; reproducing it exactly requires inserting the
  computation as nodes, which the wrapper does **not** do. Such cases are left
  to the application (insert a sub-graph, or approximate and flag).

---

## 3. The 1.1 ↔ 1.2 mapping reference

This is the authoritative per-parameter logic, derived by diffing the `v1.1`
spec tag against the 1.2 spec (not the changelog, which omits #254). Four
parameters were **added** in 1.2 and **none removed**; two shared parameters
were semantically **reinterpreted**; one default changed.

### 3.1 Emission — `emission_weight` (#231) + `emission_luminance` default 0 → 1000  · Class A

The emitted radiance is

```
1.1:  emission_color · emission_luminance
1.2:  emission_weight · emission_color · emission_luminance
```

In 1.2 `emission_weight` **defaults to 0**, and `emission_luminance`'s default
moved 0 → 1000. The two changes cancel for an *unauthored* material (both
non-emissive), so no action is needed when emission is unauthored. For authored
emission the product is what matters:

* **1.1 → 1.2:** `emission_weight = 1`, `emission_luminance` unchanged. *(Must
  set the weight — leaving it at the 1.2 default of 0 would zero the emission.)*
* **1.2 → 1.1:** `emission_luminance ← emission_weight × emission_luminance`;
  drop `emission_weight`.

Both directions are exact and always in range. (Going down, an HDR
`emission_color > 1` is outside 1.1's `[0,1]` range and is warned.)

### 3.2 `transmission_scatter` — coefficient → albedo (#286)  · Class B

Both versions share the extinction `μ_t = −ln(T)/λ` from `transmission_color`
*T* and `transmission_depth` *λ*. The scatter parameter sets the scattering
coefficient `μ_s` differently:

```
1.1:  μ_s = S / λ                    (S is a coefficient, "× 1/depth")
1.2:  μ_s = Ω · μ_t = −Ω·ln(T)/λ     (Ω is the single-scattering albedo)
```

Matching `μ_s` (λ cancels — the map depends only on `transmission_color`):

* **1.2 → 1.1:** `S = −Ω · ln(T)` per channel. Keeps 1.1's grey-shift
  untriggered, so **exact** — but `S` can exceed 1 for dark `transmission_color`.
  The exact value is emitted (1.1 predates the #277 input clamp) with a
  range-overflow warning.
* **1.1 → 1.2:** `Ω = −S / ln(T)` per channel. Exact when `S ≤ −ln(T)`. When
  `S > −ln(T)` (1.1's grey-shift regime, `μ_s > μ_t`), no exact 1.2 form exists
  → clamp `Ω = 1` and warn.

Edge cases: `transmission_color = 1` (no extinction) — 1.1 can produce a purely
scattering medium that 1.2 cannot represent (warn; albedo 0). Scatter warnings
are suppressed when transmission is inactive (`transmission_weight = 0` or
`transmission_depth = 0`), since the medium is then irrelevant.

### 3.3 `specular_weight` — refraction decoupling (#247, #238)  · Class B

In 1.1 the `specular_weight`-modulated IOR drove **both** the Fresnel factor and
the **refraction direction**. In 1.2 it drives the Fresnel only; refraction uses
the unmodulated `specular_ior`.

* **Opaque** dielectrics: zero difference (only the reflection Fresnel matters,
  computed identically). Pass through.
* **Transmissive** dielectrics with `specular_weight ≠ 1`: 1.1 couples the two,
  so no single `(specular_ior, specular_weight)` reproduces 1.2's decoupling.
  Closest match = **pass `specular_weight` through unchanged** (this preserves
  the reflection highlight, the dominant effect) and **warn** that the refraction
  direction will not match exactly.

The #238 clamp `min(ξ·F₀, 1)` only affects `specular_weight > 1`, outside the
valid `[0,1]` range.

### 3.4 New inert lobes — `specular_haze` / `specular_haze_spread` (#254), `specular_retroreflectivity` (#255)

All default to zero weight, so they contribute nothing at default.

* **1.1 → 1.2:** omit (the 1.2 defaults are inert — Class A).
* **1.2 → 1.1:** drop. If non-default, **warn** (this look has no 1.1
  equivalent — Class B). `specular_haze_spread` is dropped silently once the
  haze weight is gone.

> Note: `specular_haze` (#254) is present in the 1.2 spec but missing from the
> changelog.

### 3.5 Class-C changes (no parameter remap)

Reported as notes, never as parameter edits:

| PR | Change | When it shows |
|----|--------|---------------|
| #253 | Coat-darkening chromaticity fix | coat active **and** `coat_color` non-white (note emitted) |
| #256 | F82 negative-Fresnel clamp | extreme metal parameters |
| #277 | Universal input clamping | inputs outside their valid ranges |
| #240, #251, #250, #292, #293 | Reference MaterialX-graph fixes | renderers using the reference graph |

---

## 4. Plugin author's guide — connected inputs

This section is the source of truth for renderer/DCC plugin authors (Arnold
`mtoa`/`htoa`, etc.) who implement version upgrade/downgrade natively.

A node's parameters are frequently **connected** to upstream node outputs, so
their values are not known until render time. You therefore cannot always
"compute the new value." The right mental model is:

> **A version migration is a per-parameter *transform*. If the input carries a
> literal value, you *fold* the transform to a new constant. If the input is
> *connected*, you realize the same transform as a small node network inserted
> between the upstream output and the shader input.**

Folding and network-insertion are two realizations of the *same* math. The
`convert_params` core does the fold; the math below is what you insert when the
input is connected.

### Operation kinds

Every parameter migration is one of five operations. Only **TRANSFORM** ever
requires a network:

| Op | If the input is **valued** | If the input is **connected** |
|----|----------------------------|-------------------------------|
| **PASS** | leave as-is | leave as-is |
| **SET_CONST** | write the constant | write the constant (no upstream involved) |
| **TRANSFORM** | evaluate the expression numerically | **insert nodes computing the expression**, then rewire |
| **DROP** | remove the input | disconnect, then remove the input |
| **RENAME** | move the value to the new name | move the *connection* to the new name |

### 1.1 ↔ 1.2 operation table

`expr` is over the **source** inputs.

| Parameter | 1.1 → 1.2 | 1.2 → 1.1 | Needs a network when connected? |
|-----------|-----------|-----------|---------------------------------|
| `specular_weight`, and all unaffected params | PASS | PASS | never |
| `emission_weight` | **SET_CONST = 1** | DROP | never (a new constant factor) |
| `emission_luminance` | PASS | **TRANSFORM** `L = emission_weight · emission_luminance` | yes (down) |
| `transmission_scatter` | **TRANSFORM** `Ω = S / (−ln T)`, clamp [0,1] | **TRANSFORM** `S = Ω · (−ln T)` | yes (both directions) |
| `specular_haze`, `specular_haze_spread`, `specular_retroreflectivity` | — (inert defaults) | DROP (+ warn if non-default) | yes → just disconnect |

`T` = `transmission_color`, `S`/`Ω` = `transmission_scatter`.

### The two TRANSFORM networks (MaterialX stdlib nodes)

Port these to your renderer's equivalent shading nodes. All of `ln`, `multiply`,
`divide`, `subtract`, `clamp` exist in the MaterialX standard library.

**`transmission_scatter`, 1.1 → 1.2** — `Ω = S / (−ln T)`:

```
ln_T   = <ln>       in  = transmission_color        # natural log, per channel
negln  = <multiply> in1 = ln_T,  in2 = -1
omega  = <divide>   in1 = transmission_scatter, in2 = negln
omegaC = <clamp>    in  = omega, low = 0, high = 1
         → wire omegaC into open_pbr_surface.transmission_scatter
```

⚠️ Guard `T → 1` (white channel): `−ln T → 0`, so `μ_t = 0` and the divide is
singular. Force `Ω = 0` there (clamp the denominator away from 0, or branch).

**`transmission_scatter`, 1.2 → 1.1** — `S = Ω · (−ln T)`:

```
ln_T  = <ln>       in  = transmission_color
negln = <multiply> in1 = ln_T, in2 = -1
S     = <multiply> in1 = transmission_scatter, in2 = negln
        → wire S into open_pbr_surface.transmission_scatter   (no clamp; 1.1 has none)
```

**`emission_luminance`, 1.2 → 1.1** — `L = emission_weight · emission_luminance`:

```
L = <multiply> in1 = <emission_weight source>, in2 = <emission_luminance source>
    → wire L into open_pbr_surface.emission_luminance ; remove the emission_weight input
```

Each `in*` is the constant if that input was valued, or the upstream output if
it was connected — one `multiply` covers all valued/connected combinations.

### Connected inputs degrade warnings to render-time clamps

The Class-B safeguards that the value path reports as **author-time warnings**
become **in-graph clamps** for a connected input, because the values are dynamic:

* the `transmission_scatter` `clamp(0,1)` node silently absorbs the 1.1
  grey-shift regime per texel — you cannot warn "this texture exceeds the
  single-scattering range" up front; the clamp node *is* the closest match;
* likewise the `T → 1` guard.

So the rule to follow is: **fold when you can read a constant; otherwise insert
the network — and accept that bounded-loss (Class B) warnings become in-graph
clamps.** Class-C differences (§3.5) are unaffected either way: no network can
address them.

### Recipe

```
for each shader input:
    look up its operation in the table above
    if the input is VALUED:     apply the value-path result from convert_params()
    if the input is CONNECTED:  PASS/DROP/SET_CONST directly, or for TRANSFORM
                                insert the network above and rewire
surface any Class-B warnings and Class-C notes to the user
```

---

## 5. Adding a new version (e.g. 1.3)

When 1.3 ships, complete this checklist — **no other code needs to change**;
multi-hop conversions (1.1 ↔ 1.3) compose automatically.

1. **Diff the spec**, don't trust the changelog. From the repo root:
   ```bash
   git show v1.2:index.html | grep -E '^\*\*`[a-z_]+`\*\*' | sort > /tmp/p12.txt
   git show v1.3:index.html | grep -E '^\*\*`[a-z_]+`\*\*' | sort > /tmp/p13.txt
   diff /tmp/p12.txt /tmp/p13.txt          # added / removed / changed rows
   ```
   Classify every difference as A, B, or C (see §1).

2. **Extend the ladder** in `openpbr_version.py`:
   ```python
   VERSION_ORDER = ("1.1", "1.2", "1.3")
   ```

3. **Add `DEFAULTS["1.3"]`** with any parameters the 1.2 ↔ 1.3 rules read for
   unauthored values (new parameters and any whose default changed).

4. **Write the two rule functions** `_upgrade_1_2_to_1_3` and
   `_downgrade_1_3_to_1_2`, following the existing pattern: read `params`,
   mutate `out`, append `warnings` (Class B) / `notes` (Class C). For Class-A
   reparametrizations, derive the closed-form map and its inverse; for new inert
   lobes, omit going up and drop-with-warning going down.

5. **Register the migration:**
   ```python
   MIGRATIONS = [
       Migration("1.1", "1.2", _upgrade_1_1_to_1_2, _downgrade_1_2_to_1_1),
       Migration("1.2", "1.3", _upgrade_1_2_to_1_3, _downgrade_1_3_to_1_2),
   ]
   ```

6. **Add `PARAM_TYPES`** entries for any new parameters the MaterialX wrapper may
   add or remove (so it knows the `float` / `color3` type).

7. **Test:** add per-map numeric tests, both round-trips
   (1.2 → 1.3 → 1.2 and the reverse), and edge/clamp cases. Document this
   mapping in §3, and — if any map is a **TRANSFORM** (a value that depends on
   another parameter) — add its operation row and node network to §4 so plugin
   authors know how to handle the connected case.

---

## 6. API usage

### Core (dependency-free)

```python
from openpbr_version import convert_params

res = convert_params({"emission_luminance": 500.0},
                     from_version="1.1", to_version="1.2")
res.success        # True
res.params_out     # {'emission_luminance': 500.0, 'emission_weight': 1.0}
res.warnings       # []  (Class B)
res.notes          # []  (Class C)
```

`ConversionResult` fields: `success`, `error`, `from_version`, `to_version`,
`material_name`, `params_in`, `params_out`, `warnings`, `notes`, `output_xml`,
`output_path`.

### MaterialX document

```python
from openpbr_version import convert

res = convert(input_path="glass.mtlx", from_version="1.2", to_version="1.1")
if res.success:
    print(res.output_path)      # glass_v1.1.mtlx
    for w in res.warnings:
        print("warn:", w)
else:
    print(res.error)

# In-memory:
res = convert(input_string=xml, from_version="1.1", to_version="1.2")
res.output_xml                  # converted MaterialX XML
```

The wrapper leaves every parameter the conversion did not touch exactly as
authored, and requires an explicit `from_version` (a `.mtlx` document records
the MaterialX spec version, not the OpenPBR version, so there is nothing to
auto-detect).

---

## 7. Command-line usage

```bash
# Upgrade a material 1.1 -> 1.2 (writes glass_v1.2.mtlx)
python openpbr_version.py glass.mtlx --from 1.1 --to 1.2

# Downgrade to an explicit output path
python openpbr_version.py glass.mtlx --from 1.2 --to 1.1 -o glass_legacy.mtlx
```

The CLI prints the changed/added/dropped parameters, Class-B warnings, Class-C
notes, and the output path. Exit code is non-zero on error.

---

## 8. Tests

`test_openpbr_version.py` validates the closed-form maps, both round-trips, the
bounded-loss edge cases, and the chaining architecture (via a synthetic 1.3
migration) — with no rendering and no MaterialX dependency.

```bash
python -m pytest test_openpbr_version.py      # or:  python test_openpbr_version.py
```
