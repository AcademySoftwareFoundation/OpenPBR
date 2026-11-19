#!/usr/bin/env python
"""
Numeric tests for openpbr_version.convert_params.

Validates the closed-form parameter maps between OpenPBR 1.1 and 1.2, their
round-trip identity over the exactly-invertible domain, and the bounded-loss
edge cases (clamping + warnings).  No rendering and no MaterialX dependency.

Run:  python -m pytest test_openpbr_version.py
  or:  python test_openpbr_version.py        (built-in fallback runner)
"""

import math

from openpbr_version import convert_params, _as3

TOL = 1e-9


def approx(a, b, tol=TOL):
    if isinstance(a, (int, float)):
        return abs(a - b) <= tol
    return all(abs(x - y) <= tol for x, y in zip(_as3(a), _as3(b)))


# ---------------------------------------------------------------------------
# emission_weight (#231) + emission_luminance default change
# ---------------------------------------------------------------------------

def test_emission_1_1_to_1_2_sets_weight_one():
    r = convert_params({"emission_luminance": 500.0}, from_version="1.1", to_version="1.2")
    assert r.success
    assert approx(r.params_out["emission_weight"], 1.0)
    assert approx(r.params_out["emission_luminance"], 500.0)


def test_emission_1_2_to_1_1_folds_weight_into_luminance():
    r = convert_params({"emission_weight": 0.5, "emission_luminance": 1000.0},
                       from_version="1.2", to_version="1.1")
    assert r.success
    assert approx(r.params_out["emission_luminance"], 500.0)
    assert "emission_weight" not in r.params_out


def test_emission_1_2_to_1_1_uses_defaults_when_unauthored():
    # emission_weight authored, luminance defaults to 1000 in 1.2.
    r = convert_params({"emission_weight": 0.25}, from_version="1.2", to_version="1.1")
    assert approx(r.params_out["emission_luminance"], 250.0)


def test_emission_round_trip_1_1():
    start = {"emission_luminance": 750.0}
    up = convert_params(start, from_version="1.1", to_version="1.2")
    down = convert_params(up.params_out, from_version="1.2", to_version="1.1")
    assert approx(down.params_out["emission_luminance"], 750.0)
    assert "emission_weight" not in down.params_out


def test_emission_weight_on_1_1_input_warns():
    r = convert_params({"emission_weight": 0.5, "emission_luminance": 100.0},
                       from_version="1.1", to_version="1.2")
    assert any("emission_weight was present" in w for w in r.warnings)
    assert approx(r.params_out["emission_weight"], 1.0)


def test_emission_color_hdr_warns_going_down():
    r = convert_params({"emission_color": (2.0, 1.0, 0.5), "emission_weight": 1.0,
                        "emission_luminance": 10.0}, from_version="1.2", to_version="1.1")
    assert any("emission_color" in w and "HDR" in w for w in r.warnings)


# ---------------------------------------------------------------------------
# transmission_scatter reparametrization (#286)
# ---------------------------------------------------------------------------

def test_scatter_1_2_to_1_1_closed_form():
    # T = 0.5 grey, Omega = 0.6  ->  S = -Omega ln T = 0.6 * ln 2
    T = (0.5, 0.5, 0.5)
    r = convert_params({"transmission_scatter": (0.6, 0.6, 0.6),
                        "transmission_color": T,
                        "transmission_weight": 1.0, "transmission_depth": 0.1},
                       from_version="1.2", to_version="1.1")
    expected = 0.6 * (-math.log(0.5))
    assert approx(r.params_out["transmission_scatter"], expected)


def test_scatter_1_1_to_1_2_closed_form():
    # Inverse of the above: S = 0.6 ln 2 with T=0.5 -> Omega = 0.6
    T = (0.5, 0.5, 0.5)
    S = 0.6 * (-math.log(0.5))
    r = convert_params({"transmission_scatter": (S, S, S),
                        "transmission_color": T,
                        "transmission_weight": 1.0, "transmission_depth": 0.1},
                       from_version="1.1", to_version="1.2")
    assert approx(r.params_out["transmission_scatter"], 0.6)


def test_scatter_round_trip_in_range():
    # Omega in [0,1] with a transmission_color giving -ln T < 1 round-trips exactly.
    T = (0.7, 0.5, 0.9)
    start = {"transmission_scatter": (0.3, 0.8, 0.2), "transmission_color": T,
             "transmission_weight": 1.0, "transmission_depth": 0.2}
    down = convert_params(start, from_version="1.2", to_version="1.1")
    up = convert_params({**down.params_out, "transmission_color": T,
                         "transmission_weight": 1.0, "transmission_depth": 0.2},
                        from_version="1.1", to_version="1.2")
    assert approx(up.params_out["transmission_scatter"], (0.3, 0.8, 0.2))


def test_scatter_independent_of_depth():
    T = (0.5, 0.5, 0.5)
    a = convert_params({"transmission_scatter": (0.6, 0.6, 0.6), "transmission_color": T,
                        "transmission_weight": 1.0, "transmission_depth": 0.05},
                       from_version="1.2", to_version="1.1")
    b = convert_params({"transmission_scatter": (0.6, 0.6, 0.6), "transmission_color": T,
                        "transmission_weight": 1.0, "transmission_depth": 5.0},
                       from_version="1.2", to_version="1.1")
    assert approx(a.params_out["transmission_scatter"],
                  b.params_out["transmission_scatter"])


def test_scatter_dark_color_exceeds_range_warns_but_exact():
    # T = 0.1 -> -ln T = 2.30 > 1, so S = Omega * 2.30 > 1 for Omega near 1.
    T = (0.1, 0.1, 0.1)
    r = convert_params({"transmission_scatter": (1.0, 1.0, 1.0), "transmission_color": T,
                        "transmission_weight": 1.0, "transmission_depth": 0.1},
                       from_version="1.2", to_version="1.1")
    assert r.params_out["transmission_scatter"][0] > 1.0
    assert any("[0,1] range" in w for w in r.warnings)


def test_scatter_1_1_grey_shift_regime_clamps_and_warns():
    # S=1, T=0.9 -> -ln T = 0.105, so S > -ln T : 1.1 grey-shifts, Omega clamps to 1.
    T = (0.9, 0.9, 0.9)
    r = convert_params({"transmission_scatter": (1.0, 1.0, 1.0), "transmission_color": T,
                        "transmission_weight": 1.0, "transmission_depth": 0.1},
                       from_version="1.1", to_version="1.2")
    assert approx(r.params_out["transmission_scatter"], 1.0)
    assert any("grey-shifts" in w for w in r.warnings)


def test_scatter_white_color_no_extinction():
    T = (1.0, 1.0, 1.0)
    r = convert_params({"transmission_scatter": (0.5, 0.5, 0.5), "transmission_color": T,
                        "transmission_weight": 1.0, "transmission_depth": 0.1},
                       from_version="1.1", to_version="1.2")
    assert approx(r.params_out["transmission_scatter"], 0.0)
    assert any("no extinction" in w for w in r.warnings)


def test_scatter_warnings_suppressed_when_transmission_inactive():
    # Same dark-color scatter, but transmission_weight = 0 -> medium irrelevant.
    T = (0.1, 0.1, 0.1)
    r = convert_params({"transmission_scatter": (1.0, 1.0, 1.0), "transmission_color": T,
                        "transmission_weight": 0.0, "transmission_depth": 0.1},
                       from_version="1.2", to_version="1.1")
    assert r.warnings == []


def test_scatter_default_is_noop():
    r = convert_params({"transmission_scatter": (0.0, 0.0, 0.0)},
                       from_version="1.1", to_version="1.2")
    assert approx(r.params_out["transmission_scatter"], 0.0)
    assert r.warnings == []


# ---------------------------------------------------------------------------
# specular_weight refraction decoupling (#247)
# ---------------------------------------------------------------------------

def test_specular_weight_passthrough():
    r = convert_params({"specular_weight": 0.5}, from_version="1.1", to_version="1.2")
    assert approx(r.params_out["specular_weight"], 0.5)


def test_specular_weight_warns_only_with_transmission():
    opaque = convert_params({"specular_weight": 0.5}, from_version="1.1", to_version="1.2")
    assert opaque.warnings == []
    trans = convert_params({"specular_weight": 0.5, "transmission_weight": 1.0,
                            "transmission_depth": 0.1},
                           from_version="1.1", to_version="1.2")
    assert any("refraction direction" in w for w in trans.warnings)


def test_specular_weight_one_never_warns():
    r = convert_params({"specular_weight": 1.0, "transmission_weight": 1.0,
                        "transmission_depth": 0.1},
                       from_version="1.2", to_version="1.1")
    assert not any("refraction direction" in w for w in r.warnings)


# ---------------------------------------------------------------------------
# New 1.2 lobes dropped going down
# ---------------------------------------------------------------------------

def test_haze_non_default_warns_and_dropped():
    r = convert_params({"specular_haze": 0.4, "specular_haze_spread": 0.5},
                       from_version="1.2", to_version="1.1")
    assert "specular_haze" not in r.params_out
    assert "specular_haze_spread" not in r.params_out
    assert any("specular_haze" in w for w in r.warnings)


def test_haze_default_dropped_silently():
    r = convert_params({"specular_haze": 0.0}, from_version="1.2", to_version="1.1")
    assert "specular_haze" not in r.params_out
    assert r.warnings == []


def test_retroreflectivity_non_default_warns():
    r = convert_params({"specular_retroreflectivity": 0.7},
                       from_version="1.2", to_version="1.1")
    assert "specular_retroreflectivity" not in r.params_out
    assert any("retroreflective" in w for w in r.warnings)


def test_new_lobes_absent_going_up_is_clean():
    r = convert_params({"base_color": (0.2, 0.4, 0.6)},
                       from_version="1.1", to_version="1.2")
    assert r.warnings == []
    assert approx(r.params_out["base_color"], (0.2, 0.4, 0.6))


# ---------------------------------------------------------------------------
# Class-C notes
# ---------------------------------------------------------------------------

def test_coat_darkening_note_when_colored_coat_active():
    r = convert_params({"coat_weight": 1.0, "coat_color": (0.8, 0.2, 0.1)},
                       from_version="1.2", to_version="1.1")
    assert any("coat-darkening" in n for n in r.notes)


def test_no_coat_note_for_white_coat():
    r = convert_params({"coat_weight": 1.0, "coat_color": (1.0, 1.0, 1.0)},
                       from_version="1.2", to_version="1.1")
    assert r.notes == []


# ---------------------------------------------------------------------------
# Passthrough / plumbing
# ---------------------------------------------------------------------------

def test_unaffected_params_pass_through_unchanged():
    src = {"base_color": (0.1, 0.6, 0.9), "specular_roughness": 0.25,
           "coat_weight": 0.0}
    r = convert_params(src, from_version="1.1", to_version="1.2")
    for k, v in src.items():
        assert approx(r.params_out[k], v)


def test_same_version_is_identity():
    src = {"base_color": (0.1, 0.6, 0.9), "emission_luminance": 500.0}
    r = convert_params(src, from_version="1.2", to_version="1.2")
    assert r.params_out == src
    assert r.warnings == []


def test_unsupported_version_errors():
    r = convert_params({}, from_version="1.0", to_version="1.2")
    assert not r.success
    assert "Unsupported" in r.error


def test_input_not_mutated():
    src = {"emission_luminance": 500.0}
    convert_params(src, from_version="1.1", to_version="1.2")
    assert src == {"emission_luminance": 500.0}


# ---------------------------------------------------------------------------
# MaterialX wrapper: connected (node-driven) inputs
# (skipped automatically if the MaterialX package is not installed)
# ---------------------------------------------------------------------------

def _materialx_available():
    try:
        import MaterialX  # noqa: F401
        return True
    except ImportError:
        return False


def _openpbr_doc(emission_luminance_input):
    """A minimal OpenPBR doc whose emission_luminance is the given XML snippet."""
    return f"""<?xml version="1.0"?>
<materialx version="1.39">
  <constant name="lum_tex" type="float">
    <input name="value" type="float" value="800"/>
  </constant>
  <open_pbr_surface name="M" type="surfaceshader">
    {emission_luminance_input}
    <input name="emission_color" type="color3" value="1, 0.6, 0.2"/>
  </open_pbr_surface>
  <surfacematerial name="M_mat" type="material">
    <input name="surfaceshader" type="surfaceshader" nodename="M"/>
  </surfacematerial>
</materialx>"""


def test_wrapper_connected_emission_luminance_gets_weight():
    if not _materialx_available():
        return  # skip
    from openpbr_version import convert
    xml = _openpbr_doc('<input name="emission_luminance" type="float" nodename="lum_tex"/>')
    r = convert(input_string=xml, from_version="1.1", to_version="1.2")
    assert r.success
    assert 'name="emission_weight"' in r.output_xml      # authored as a constant
    assert 'value="1"' in r.output_xml
    assert 'nodename="lum_tex"' in r.output_xml          # connection preserved
    assert any("node-connected" in w for w in r.warnings)


def test_wrapper_valued_emission_luminance_gets_weight_via_core():
    if not _materialx_available():
        return  # skip
    from openpbr_version import convert
    xml = _openpbr_doc('<input name="emission_luminance" type="float" value="800"/>')
    r = convert(input_string=xml, from_version="1.1", to_version="1.2")
    assert r.success
    assert 'name="emission_weight"' in r.output_xml
    # The valued path is handled by the core, not the connection fixup:
    assert not any("node-connected" in w for w in r.warnings)


def test_wrapper_no_emission_no_weight_added():
    if not _materialx_available():
        return  # skip
    from openpbr_version import convert
    xml = """<?xml version="1.0"?>
<materialx version="1.39">
  <open_pbr_surface name="M" type="surfaceshader">
    <input name="base_color" type="color3" value="0.2, 0.4, 0.6"/>
  </open_pbr_surface>
  <surfacematerial name="M_mat" type="material">
    <input name="surfaceshader" type="surfaceshader" nodename="M"/>
  </surfacematerial>
</materialx>"""
    r = convert(input_string=xml, from_version="1.1", to_version="1.2")
    assert r.success
    assert "emission_weight" not in r.output_xml         # no emission -> no weight


def test_wrapper_connected_weight_not_added_when_downgrading():
    if not _materialx_available():
        return  # skip
    from openpbr_version import convert
    xml = _openpbr_doc('<input name="emission_luminance" type="float" nodename="lum_tex"/>')
    r = convert(input_string=xml, from_version="1.2", to_version="1.1")
    assert r.success
    assert "emission_weight" not in r.output_xml         # weight doesn't exist in 1.1


# ---------------------------------------------------------------------------
# Chaining architecture: composing adjacent migrations (e.g. 1.1 -> 1.3)
# ---------------------------------------------------------------------------

import contextlib

import openpbr_version as ov


@contextlib.contextmanager
def _synthetic_1_3():
    """Temporarily register a fake 1.3 migration to exercise multi-hop chaining."""
    def up_1_2_to_1_3(params, out, warnings, notes):
        out["lobe_1_3"] = 1.0                       # a new 1.3 parameter
        warnings.append("synthetic upgrade warning")
    def down_1_3_to_1_2(params, out, warnings, notes):
        out.pop("lobe_1_3", None)

    saved_order, saved_migs, saved_defaults = (
        ov.VERSION_ORDER, ov.MIGRATIONS, dict(ov.DEFAULTS))
    ov.VERSION_ORDER = ("1.1", "1.2", "1.3")
    ov.MIGRATIONS = saved_migs + [
        ov.Migration("1.2", "1.3", up_1_2_to_1_3, down_1_3_to_1_2)]
    ov.DEFAULTS["1.3"] = dict(ov.DEFAULTS["1.2"], lobe_1_3=0.0)
    try:
        yield
    finally:
        ov.VERSION_ORDER, ov.MIGRATIONS = saved_order, saved_migs
        ov.DEFAULTS.clear()
        ov.DEFAULTS.update(saved_defaults)


def test_multi_hop_composes_adjacent_steps():
    with _synthetic_1_3():
        r = ov.convert_params({"emission_luminance": 400.0},
                              from_version="1.1", to_version="1.3")
        assert r.success
        # 1.1 -> 1.2 effect (emission_weight) AND 1.2 -> 1.3 effect (lobe_1_3):
        assert approx(r.params_out["emission_weight"], 1.0)
        assert approx(r.params_out["lobe_1_3"], 1.0)


def test_multi_hop_prefixes_warnings_with_hop_label():
    with _synthetic_1_3():
        r = ov.convert_params({"specular_weight": 0.5, "transmission_weight": 1.0,
                               "transmission_depth": 0.1},
                              from_version="1.1", to_version="1.3")
        assert any(w.startswith("[1.1→1.2]") for w in r.warnings)
        assert any(w.startswith("[1.2→1.3]") for w in r.warnings)


def test_multi_hop_downgrade_round_trip():
    with _synthetic_1_3():
        up = ov.convert_params({"emission_luminance": 400.0},
                               from_version="1.1", to_version="1.3")
        down = ov.convert_params(up.params_out, from_version="1.3", to_version="1.1")
        assert "lobe_1_3" not in down.params_out
        assert approx(down.params_out["emission_luminance"], 400.0)


def test_single_hop_warnings_are_unprefixed():
    # Regression: single-hop output must stay clean (no "[a->b]" prefix).
    r = convert_params({"specular_weight": 0.5, "transmission_weight": 1.0,
                        "transmission_depth": 0.1}, from_version="1.1", to_version="1.2")
    assert r.warnings and not any(w.startswith("[") for w in r.warnings)


# ---------------------------------------------------------------------------
# Fallback runner (no pytest required)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed ({len(tests)} total)")
    sys.exit(1 if failed else 0)
