#!/usr/bin/env python
"""
OpenPBR Version Converter
=========================

Converts an OpenPBR Surface parameter set between specification versions
**1.1** and **1.2**, in either direction, choosing the parameter
correspondence that yields the *closest match of the resulting appearance*.

Two layers are provided:

* :func:`convert_params` -- a dependency-free core that maps a plain
  ``{parameter_name: value}`` dict.  This is the piece an application or
  renderer embeds; it imports nothing beyond the standard library.
* :func:`convert` -- a MaterialX (.mtlx) document wrapper that reads a shader
  instance, converts its authored inputs, and writes the result back.  This
  layer requires the ``MaterialX`` Python package; it is otherwise
  self-contained.

What a version converter can and cannot do
------------------------------------------
Parameter remapping can only compensate for differences that are themselves
*parameterized*.  The 1.1 -> 1.2 changes fall into three classes:

A. **Exactly invertible** reparametrizations -- appearance is identical after
   the remap (``emission_weight``; the inert new lobes at their defaults).
B. **Lossy / bounded** -- mappable over part of the domain, clamped + warned
   elsewhere (``transmission_scatter`` albedo reinterpretation; the
   ``specular_weight`` refraction decoupling).
C. **Not parameter-correctable** -- internal BSDF / MaterialX-graph fixes that
   no parameter controls (coat-darkening color fix #253, F82 negative-Fresnel
   clamp #256, universal input clamping #277, graph fixes #240/#251/#250/#292/
   #293).  These are reported as *notes*; the converter makes no parameter
   change for them.

The precise per-parameter logic is documented inline in ``_rules_*`` below.

Usage (CLI)
-----------
    python openpbr_version.py material.mtlx --from 1.1 --to 1.2 [-o out.mtlx]
    python openpbr_version.py material.mtlx --from 1.2 --to 1.1

Usage (API)
-----------
    from openpbr_version import convert_params, convert

    res = convert_params({"emission_luminance": 500.0}, from_version="1.1", to_version="1.2")
    res.params_out   # {'emission_luminance': 500.0, 'emission_weight': 1.0}

    res = convert(input_path="glass.mtlx", from_version="1.2", to_version="1.1")
    res.output_xml   # converted MaterialX XML
"""

import argparse
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

# The ordered version ladder.  Conversions chain through adjacent steps, so a
# new release only needs to (1) be appended here, (2) gain a DEFAULTS entry, and
# (3) register one Migration with its adjacent neighbour (see MIGRATIONS below).
# A multi-hop conversion (e.g. 1.1 -> 1.3) is composed automatically from the
# adjacent steps.  See VERSIONING.md for the full "adding a version" checklist.
VERSION_ORDER = ("1.1", "1.2")

# Backwards-compatible alias; kept as the public "is this a known version" set.
SUPPORTED_VERSIONS = VERSION_ORDER

# Tolerance for "is this value at its default" comparisons.
_EPS = 1e-9
# Floor for transmission_color before taking a logarithm.
_T_FLOOR = 1e-6

# MaterialX input types for parameters the converter may add/remove.
PARAM_TYPES = {
    "emission_weight": "float",
    "emission_luminance": "float",
    "emission_color": "color3",
    "transmission_scatter": "color3",
    "transmission_color": "color3",
    "transmission_depth": "float",
    "transmission_weight": "float",
    "specular_weight": "float",
    "specular_haze": "float",
    "specular_haze_spread": "float",
    "specular_retroreflectivity": "float",
    "coat_weight": "float",
    "coat_color": "color3",
}

# Defaults needed by the maps when a value is unauthored, per version.
DEFAULTS = {
    "1.1": {
        "emission_luminance": 0.0,
        "emission_color": (1.0, 1.0, 1.0),
        "transmission_scatter": (0.0, 0.0, 0.0),
        "transmission_color": (1.0, 1.0, 1.0),
        "transmission_depth": 0.0,
        "transmission_weight": 0.0,
        "specular_weight": 1.0,
        "coat_weight": 0.0,
        "coat_color": (1.0, 1.0, 1.0),
    },
    "1.2": {
        "emission_weight": 0.0,
        "emission_luminance": 1000.0,
        "emission_color": (1.0, 1.0, 1.0),
        "transmission_scatter": (0.0, 0.0, 0.0),
        "transmission_color": (1.0, 1.0, 1.0),
        "transmission_depth": 0.0,
        "transmission_weight": 0.0,
        "specular_weight": 1.0,
        "specular_haze": 0.0,
        "specular_haze_spread": 0.3,
        "specular_retroreflectivity": 0.0,
        "coat_weight": 0.0,
        "coat_color": (1.0, 1.0, 1.0),
    },
}


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ConversionResult:
    """Result of a version conversion (mirrors translate_mtlx.TranslationResult)."""

    success: bool = False
    error: Optional[str] = None

    from_version: Optional[str] = None
    to_version: Optional[str] = None
    material_name: Optional[str] = None

    params_in: dict = field(default_factory=dict)
    """The authored input parameters that were converted."""

    params_out: dict = field(default_factory=dict)
    """The converted parameter set."""

    warnings: list = field(default_factory=list)
    """Class-B degradation: where the closest match is not exact."""

    notes: list = field(default_factory=list)
    """Class-C information: appearance differences no parameter remap can fix."""

    output_xml: Optional[str] = None
    output_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Value helpers (pure)
# ---------------------------------------------------------------------------

def _as3(v):
    """Coerce a scalar or 3-sequence to a 3-tuple of floats."""
    if isinstance(v, (int, float)):
        f = float(v)
        return (f, f, f)
    seq = tuple(float(x) for x in v)
    if len(seq) == 1:
        return (seq[0], seq[0], seq[0])
    if len(seq) != 3:
        raise ValueError(f"expected a scalar or 3 components, got {v!r}")
    return seq


def _as_float(v):
    if isinstance(v, (int, float)):
        return float(v)
    return float(v)


def _get(params, defaults, name):
    """Authored value if present, else the version default."""
    if name in params:
        return params[name]
    return defaults[name]


def _is_default(value, default, is_color):
    try:
        if is_color:
            a, b = _as3(value), _as3(default)
        else:
            a, b = (_as_float(value),), (_as_float(default),)
    except (TypeError, ValueError):
        return False
    return all(abs(x - y) <= _EPS for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# transmission_scatter reparametrization (#286)
# ---------------------------------------------------------------------------
# Per channel, both versions share mu_t = -ln(T)/lambda (T = transmission_color,
# lambda = transmission_depth).  The scatter parameter sets the scattering
# coefficient mu_s differently:
#     1.1:  mu_s = S / lambda                 (S is a coefficient, "x 1/depth")
#     1.2:  mu_s = Omega * mu_t = -Omega ln(T)/lambda   (Omega is the albedo)
# Matching mu_s (lambda cancels -- the map depends only on transmission_color):
#     1.2 -> 1.1:  S     = -Omega * ln(T)        (always >= 0; may exceed 1)
#     1.1 -> 1.2:  Omega = -S / ln(T)            (clamped to [0,1])

def _scatter_1_1_to_1_2(S, T):
    """1.1 scattering coefficient S -> 1.2 single-scattering albedo Omega."""
    omega, warnings = [], []
    for c, (s, t) in enumerate(zip(_as3(S), _as3(T))):
        if t >= 1.0 - _EPS:                       # mu_t = 0: no extinction
            if s > _EPS:
                warnings.append(
                    f"transmission_scatter[{c}]: transmission_color is 1 (no "
                    f"extinction), so the 1.1 purely-scattering medium has no "
                    f"1.2 single-scattering-albedo equivalent; set albedo 0.")
            omega.append(0.0)
            continue
        lt = -math.log(max(t, _T_FLOOR))          # = -ln(T) > 0
        o = s / lt
        if o > 1.0 + _EPS:
            warnings.append(
                f"transmission_scatter[{c}] = {s:g} exceeds the 1.1 single-"
                f"scattering regime (S > -ln T); 1.1 grey-shifts absorption "
                f"here, which 1.2 cannot represent. Clamped albedo to 1.")
            o = 1.0
        omega.append(min(max(o, 0.0), 1.0))
    return tuple(omega), warnings


def _scatter_1_2_to_1_1(Omega, T):
    """1.2 single-scattering albedo Omega -> 1.1 scattering coefficient S."""
    S, warnings = [], []
    for c, (o, t) in enumerate(zip(_as3(Omega), _as3(T))):
        if t >= 1.0 - _EPS:                       # mu_t = 0: mu_s = 0 in 1.2
            S.append(0.0)
            continue
        lt = -math.log(max(t, _T_FLOOR))
        s = o * lt                                # exact; >= 0
        if s > 1.0 + _EPS:
            warnings.append(
                f"transmission_scatter[{c}] = {s:g} exceeds the documented "
                f"[0,1] range. The value reproduces 1.2 exactly, but predates "
                f"1.1's input clamping; renderers that clamp will scatter less.")
        S.append(s)
    return tuple(S), warnings


# ---------------------------------------------------------------------------
# Conversion rules
# ---------------------------------------------------------------------------

def _transmission_active(params, defaults):
    tw = _as_float(_get(params, defaults, "transmission_weight"))
    td = _as_float(_get(params, defaults, "transmission_depth"))
    return tw > _EPS and td > _EPS


def _coat_notes(params, defaults, notes):
    """Class-C: coat-darkening color fix #253 only bites with a colored coat."""
    cw = _as_float(_get(params, defaults, "coat_weight"))
    cc = _as3(_get(params, defaults, "coat_color"))
    if cw > _EPS and any(abs(x - 1.0) > _EPS for x in cc):
        notes.append(
            "coat is active with a non-white coat_color: the coat-darkening "
            "chromaticity fix (#253) changes the look between 1.1 and 1.2; no "
            "parameter remap can reconcile this (Class C).")


def _upgrade_1_1_to_1_2(params, out, warnings, notes):
    d11 = DEFAULTS["1.1"]

    # --- emission_weight (#231) + emission_luminance default 0 -> 1000 --------
    # 1.2 emission = emission_weight * emission_color * emission_luminance.
    # 1.2's emission_weight defaults to 0, so to preserve a 1.1 material's
    # emission we MUST author emission_weight = 1 whenever luminance is set.
    if "emission_weight" in params:
        warnings.append(
            "emission_weight was present on a 1.1 input (it does not exist in "
            "1.1) and has been ignored.")
        out.pop("emission_weight", None)
    if "emission_luminance" in params:
        out["emission_weight"] = 1.0   # luminance carried through unchanged

    # --- transmission_scatter: coefficient -> albedo (#286) ------------------
    if "transmission_scatter" in params:
        T = _get(params, d11, "transmission_color")
        omega, w = _scatter_1_1_to_1_2(params["transmission_scatter"], T)
        out["transmission_scatter"] = omega
        if _transmission_active(params, d11):
            warnings.extend(w)

    # --- specular_weight refraction decoupling (#247) ------------------------
    # Value passes through unchanged (it matches the reflection highlight, the
    # dominant effect). Only the refraction *direction* differs, and only when
    # specular_weight != 1 and transmission is active.
    _specular_weight_note(params, d11, warnings)

    # New 1.2 lobes (specular_haze/_spread, specular_retroreflectivity) do not
    # exist in 1.1 input; they take their inert 1.2 defaults -> nothing to do.

    _coat_notes(params, d11, notes)


def _downgrade_1_2_to_1_1(params, out, warnings, notes):
    d12 = DEFAULTS["1.2"]

    # --- emission: fold weight into luminance --------------------------------
    if "emission_weight" in params or "emission_luminance" in params:
        w = _as_float(_get(params, d12, "emission_weight"))
        lum = _as_float(_get(params, d12, "emission_luminance"))
        out["emission_luminance"] = w * lum
        out.pop("emission_weight", None)
    # emission_color HDR range [0,inf) -> [0,1] in 1.1
    if "emission_color" in params:
        ec = _as3(params["emission_color"])
        if any(x > 1.0 + _EPS for x in ec):
            warnings.append(
                "emission_color has component(s) > 1 (HDR), outside 1.1's "
                "[0,1] range; renderers that clamp inputs will differ.")

    # --- transmission_scatter: albedo -> coefficient (#286) ------------------
    if "transmission_scatter" in params:
        T = _get(params, d12, "transmission_color")
        S, w = _scatter_1_2_to_1_1(params["transmission_scatter"], T)
        out["transmission_scatter"] = S
        if _transmission_active(params, d12):
            warnings.extend(w)

    # --- specular_weight refraction decoupling (#247) ------------------------
    _specular_weight_note(params, d12, warnings)

    # --- new 1.2 lobes that have no 1.1 equivalent: drop, warn if non-default -
    for name, label in (("specular_haze", "specular haze lobe"),
                        ("specular_retroreflectivity", "retroreflective lobe")):
        if name in params:
            if not _is_default(params[name], DEFAULTS["1.2"][name], is_color=False):
                warnings.append(
                    f"{name} = {params[name]} has no 1.1 equivalent ({label} "
                    f"is new in 1.2); dropped. This look cannot be reproduced "
                    f"in 1.1.")
            out.pop(name, None)
    # specular_haze_spread is only meaningful alongside specular_haze; drop it
    # silently (it has no effect once the haze weight is gone).
    out.pop("specular_haze_spread", None)

    _coat_notes(params, d12, notes)


def _specular_weight_note(params, defaults, warnings):
    sw = _as_float(_get(params, defaults, "specular_weight"))
    if abs(sw - 1.0) > _EPS and _transmission_active(params, defaults):
        warnings.append(
            f"specular_weight = {sw:g} with active transmission: 1.1 and 1.2 "
            f"compute the refraction direction from different IORs (#247). The "
            f"reflection highlight matches, but the refraction direction will "
            f"not match exactly (Class B; value passed through unchanged).")


# ---------------------------------------------------------------------------
# Migration registry
# ---------------------------------------------------------------------------
# Each Migration describes the conversion between one *adjacent* pair of
# versions, in both directions.  A conversion across several versions is built
# by composing the adjacent steps (see _build_chain / convert_params).
#
# Each direction is a callable ``rule(params, out, warnings, notes)`` that reads
# the source ``params`` dict and mutates ``out`` (a shallow copy of ``params``),
# appending any degradation ``warnings`` (Class B) and ``notes`` (Class C).

@dataclass
class Migration:
    older: str
    newer: str
    upgrade: object     # rule(params, out, warnings, notes): older -> newer
    downgrade: object   # rule(params, out, warnings, notes): newer -> older


MIGRATIONS = [
    Migration("1.1", "1.2", _upgrade_1_1_to_1_2, _downgrade_1_2_to_1_1),
    # When 1.3 lands, append:  ("1.2", "1.3") to VERSION_ORDER, a DEFAULTS["1.3"]
    # entry, and:  Migration("1.2", "1.3", _upgrade_1_2_to_1_3, _downgrade_1_3_to_1_2)
]


def _build_chain(from_version, to_version):
    """Ordered list of ``(rule, label)`` adjacent steps from *from* to *to*.

    Returns ``None`` if any adjacent step on the path is missing.  Versions are
    linearly ordered, so the path is an unambiguous walk up or down the ladder.
    """
    index = {(m.older, m.newer): m for m in MIGRATIONS}
    i_from, i_to = VERSION_ORDER.index(from_version), VERSION_ORDER.index(to_version)
    steps = []
    if i_to > i_from:                                  # upgrade: walk up
        for i in range(i_from, i_to):
            older, newer = VERSION_ORDER[i], VERSION_ORDER[i + 1]
            m = index.get((older, newer))
            if m is None or m.upgrade is None:
                return None
            steps.append((m.upgrade, f"{older}→{newer}"))
    else:                                              # downgrade: walk down
        for i in range(i_from, i_to, -1):
            older, newer = VERSION_ORDER[i - 1], VERSION_ORDER[i]
            m = index.get((older, newer))
            if m is None or m.downgrade is None:
                return None
            steps.append((m.downgrade, f"{newer}→{older}"))
    return steps


# ---------------------------------------------------------------------------
# Public core API (dependency-free)
# ---------------------------------------------------------------------------

def convert_params(params, *, from_version, to_version):
    """Convert a plain ``{name: value}`` OpenPBR parameter dict between versions.

    *params* values may be Python numbers (floats) or 3-sequences (for
    ``color3`` parameters).  Only authored parameters need be supplied;
    unauthored ones are assumed to be at their *from_version* default.

    Conversions across non-adjacent versions (e.g. ``"1.1"`` -> ``"1.3"``) are
    composed automatically from the adjacent :data:`MIGRATIONS` steps; the
    intermediate parameter set produced by each step is fed to the next.  When
    more than one step runs, each warning/note is prefixed with its hop label.

    Returns a :class:`ConversionResult`.  Parameters not affected by the
    version change are copied through unchanged.  ``result.params_out`` holds
    the full converted set.
    """
    result = ConversionResult(from_version=from_version, to_version=to_version)

    if from_version not in VERSION_ORDER or to_version not in VERSION_ORDER:
        result.error = (f"Unsupported version pair {from_version!r} -> "
                        f"{to_version!r}. Supported: {VERSION_ORDER}.")
        return result

    result.params_in = dict(params)

    if from_version == to_version:
        result.params_out = dict(params)
        result.success = True
        return result

    chain = _build_chain(from_version, to_version)
    if chain is None:
        result.error = (f"No conversion path defined for {from_version} -> "
                        f"{to_version} (a migration step on the ladder is "
                        f"missing).")
        return result

    multi_hop = len(chain) > 1
    current = dict(params)
    for rule, label in chain:
        out = dict(current)             # passthrough by default
        step_warnings, step_notes = [], []
        rule(current, out, step_warnings, step_notes)
        prefix = f"[{label}] " if multi_hop else ""
        result.warnings.extend(prefix + w for w in step_warnings)
        result.notes.extend(prefix + n for n in step_notes)
        current = out

    result.params_out = current
    result.success = True
    return result


# ---------------------------------------------------------------------------
# MaterialX wrapper (requires the MaterialX package)
# ---------------------------------------------------------------------------

_OPENPBR_CATEGORY = "open_pbr_surface"


def _require_materialx():
    try:
        import MaterialX as mx  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "The MaterialX Python package is required for document conversion "
            "(pip install MaterialX). The convert_params() core has no such "
            "dependency.") from e
    return mx


def _mx_write_options(mx):
    """XmlWriteOptions that exclude imported library definitions."""
    opts = mx.XmlWriteOptions()
    opts.writeXIncludeEnable = False
    opts.elementPredicate = lambda elem: not elem.hasSourceUri()
    return opts


def _mx_load_document(mx, input_path=None, input_string=None):
    """Load a MaterialX document with the standard libraries imported."""
    doc = mx.createDocument()
    stdlib = mx.createDocument()
    mx.loadLibraries(mx.getDefaultDataLibraryFolders(),
                     mx.getDefaultDataSearchPath(), stdlib)
    if input_path:
        mx.readFromXmlFile(doc, input_path)
    else:
        mx.readFromXmlString(doc, input_string)
    doc.importLibrary(stdlib)
    return doc


def _parse_mtlx_value(value_string, mtype):
    """Parse a MaterialX input value string into a float or 3-tuple."""
    if mtype in ("color3", "vector3"):
        return tuple(float(x) for x in value_string.replace(",", " ").split())
    return float(value_string)


def _format_mtlx_value(value, mtype):
    if mtype in ("color3", "vector3"):
        return ", ".join(f"{x:g}" for x in _as3(value))
    return f"{_as_float(value):g}"


def _input_is_connected(inp):
    """True if a MaterialX input draws from a node/graph rather than a literal.

    Connectivity is read from the document — the caller never specifies it.  An
    input is "valued" when it has a ``value`` attribute and "connected" when it
    instead references a ``nodename`` / ``nodegraph`` / ``output`` /
    ``interfacename``; in the latter case ``getValueString()`` is empty.
    """
    return bool(inp.getNodeName() or inp.getNodeGraphString()
                or inp.getInterfaceName() or inp.getOutputString())


def _emission_weight_introduced(from_version, to_version):
    """True if the conversion is an upgrade that first introduces emission_weight."""
    fi, ti = VERSION_ORDER.index(from_version), VERSION_ORDER.index(to_version)
    return (ti > fi
            and "emission_weight" in DEFAULTS.get(to_version, {})
            and "emission_weight" not in DEFAULTS.get(from_version, {}))


def _fixup_connected_inputs(shader, from_version, to_version, warnings):
    """Document-level fixups for *connected* inputs the value-only core can't see.

    The core (``convert_params``) only sees literal values, so a node-connected
    input is invisible to it.  Most connected inputs need no action (they pass
    through untouched), but the emission reparametrization is an exception:

    Upgrading across the boundary that introduces ``emission_weight`` (1.1 ->
    1.2), a node-connected ``emission_luminance`` must still get
    ``emission_weight = 1``.  The new weight defaults to 0, so a textured
    emission would otherwise go dark.  ``weight = 1`` is a constant and exact
    regardless of how luminance is driven, since 1.2 emission is
    ``emission_weight * emission_color * emission_luminance``.  (The valued case
    is already handled by the core.)

    Other connection-sensitive maps (e.g. the ``transmission_scatter`` albedo
    remap when ``transmission_color`` is textured) cannot be reduced to a
    constant and are left to the integrating application; see VERSIONING.md.
    """
    if _emission_weight_introduced(from_version, to_version):
        lum = shader.getInput("emission_luminance")
        if (lum is not None and _input_is_connected(lum)
                and shader.getInput("emission_weight") is None):
            shader.addInput("emission_weight", "float").setValueString("1")
            warnings.append(
                "emission_luminance is node-connected: authored emission_weight "
                "= 1 so the textured emission is preserved (it would otherwise "
                "default to 0 in the target version).")


def convert(*, input_path=None, input_string=None, from_version, to_version,
            output_path=None):
    """Convert an OpenPBR Surface MaterialX document between versions.

    Provide **either** *input_path* (a ``.mtlx`` file) or *input_string* (raw
    MaterialX XML).  Returns a :class:`ConversionResult` with ``output_xml``
    populated (and ``output_path`` if written to disk).
    """
    result = ConversionResult(from_version=from_version, to_version=to_version)

    if input_path and input_string:
        raise ValueError("Provide either input_path or input_string, not both.")
    if not input_path and not input_string:
        raise ValueError("Provide input_path or input_string.")
    if from_version not in SUPPORTED_VERSIONS or to_version not in SUPPORTED_VERSIONS:
        raise ValueError(f"Supported versions are {SUPPORTED_VERSIONS}.")

    mx = _require_materialx()

    try:
        doc = _mx_load_document(mx, input_path=input_path, input_string=input_string)
    except Exception as e:
        result.error = f"Failed to load document: {e}"
        return result

    # Find the OpenPBR shader node.
    shader = None
    for node in doc.getNodes():
        if node.getCategory() == _OPENPBR_CATEGORY and node.getType() == "surfaceshader":
            shader = node
            break
    if shader is None:
        result.error = ("No open_pbr_surface shader instance found in the "
                        "document; nothing to convert.")
        return result
    result.material_name = shader.getName()

    # Read authored inputs into a plain dict.
    params = {}
    for inp in shader.getInputs():
        name = inp.getName()
        vs = inp.getValueString()
        if not vs:
            continue
        mtype = inp.getType()
        try:
            params[name] = _parse_mtlx_value(vs, mtype)
        except (TypeError, ValueError):
            params[name] = vs   # leave non-numeric (e.g. connected) values alone

    core = convert_params(params, from_version=from_version, to_version=to_version)
    if not core.success:
        result.error = core.error
        return result

    result.params_in = core.params_in
    result.params_out = core.params_out
    result.warnings = core.warnings
    result.notes = core.notes

    # Apply the converted parameters back onto the shader node.
    converted_names = set(core.params_out) | set(core.params_in)
    for name in converted_names:
        in_out = name in core.params_out
        if not in_out:
            # Parameter was dropped by the conversion.
            if shader.getInput(name) is not None:
                shader.removeInput(name)
            continue
        value = core.params_out[name]
        # Only write parameters the converter actually touched (changed/added);
        # leave everything else exactly as authored.
        if name in core.params_in and core.params_in[name] == value:
            continue
        mtype = PARAM_TYPES.get(name) or (
            shader.getInput(name).getType() if shader.getInput(name) else "float")
        inp = shader.getInput(name) or shader.addInput(name, mtype)
        inp.setValueString(_format_mtlx_value(value, mtype))

    # Handle connected inputs the value-only core could not see.
    _fixup_connected_inputs(shader, from_version, to_version, result.warnings)

    try:
        result.output_xml = mx.writeToXmlString(doc, _mx_write_options(mx))
    except Exception as e:
        result.error = f"Conversion succeeded but failed to serialize: {e}"
        return result
    result.success = True

    should_write = output_path is not None or input_path is not None
    if should_write:
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_v{to_version}{ext}"
        try:
            mx.writeToXmlFile(doc, output_path, _mx_write_options(mx))
            result.output_path = output_path
        except Exception as e:
            result.error = f"Conversion succeeded but failed to write: {e}"
            result.success = False
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_result(result):
    if not result.success:
        print(f"Error: {result.error}")
        return
    print()
    print(f"  OpenPBR version conversion: {result.from_version} -> {result.to_version}")
    if result.material_name:
        print(f"  Material: {result.material_name}")
    print()
    changed = {k: v for k, v in result.params_out.items()
               if k not in result.params_in or result.params_in[k] != v}
    dropped = [k for k in result.params_in if k not in result.params_out]
    if changed:
        print("  Changed / added parameters:")
        for k, v in sorted(changed.items()):
            print(f"    {k:<32s} = {v}")
        print()
    if dropped:
        print("  Dropped parameters:")
        for k in sorted(dropped):
            print(f"    {k}")
        print()
    if result.warnings:
        print("  Warnings (closest match is not exact):")
        for w in result.warnings:
            print(f"    - {w}")
        print()
    if result.notes:
        print("  Notes (appearance differences no remap can fix):")
        for n in result.notes:
            print(f"    - {n}")
        print()
    if result.output_path:
        print(f"  Output: {result.output_path}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Convert an OpenPBR Surface material between spec versions "
                    "1.1 and 1.2 (closest appearance match).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="Input .mtlx file")
    parser.add_argument("--from", dest="from_version", required=True,
                        choices=list(SUPPORTED_VERSIONS),
                        help="Source OpenPBR version")
    parser.add_argument("--to", dest="to_version", required=True,
                        choices=list(SUPPORTED_VERSIONS),
                        help="Target OpenPBR version")
    parser.add_argument("--output", "-o", help="Output .mtlx path")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    try:
        result = convert(input_path=args.input, from_version=args.from_version,
                         to_version=args.to_version, output_path=args.output)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    _print_result(result)
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
