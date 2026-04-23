#!/usr/bin/env python
"""
MaterialX Document Validator

Validates a MaterialX (.mtlx) file against the MaterialX standard libraries.

Usage:
    python validate_mtlx.py <file.mtlx> [options]

Examples:
    python validate_mtlx.py material.mtlx
    python validate_mtlx.py material.mtlx --verbose
    python validate_mtlx.py material.mtlx --libraries /path/to/libraries

Environment Setup:
    Set MATERIALX_ROOT to your MaterialX build directory:
        export MATERIALX_ROOT=/path/to/MaterialX
"""

import argparse
import sys
import os
import io
import re
import xml.etree.ElementTree as ET

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# MaterialX Specification Constants
VALID_NAME_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
VALID_VERSION_PATTERN = re.compile(r'^\d+\.\d+$')
RESERVED_COLORSPACES = {
    'none', 'srgb_texture', 'lin_rec709', 'g18_rec709', 'g22_rec709',
    'acescg', 'lin_ap1', 'g18_ap1', 'g22_ap1', 'rec2020', 'lin_rec2020',
    'g24_rec2020', 'adobergb', 'lin_adobergb', 'g22_adobergb',
    'lin_srgb', 'srgb_displayp3', 'lin_displayp3'
}
PREDEFINED_UNIT_TYPES = {
    'distance': ['nanometer', 'micron', 'millimeter', 'centimeter', 'inch', 'foot', 'yard', 'meter', 'kilometer', 'mile'],
    'angle': ['degree', 'radian']
}


def find_materialx_python():
    """Find and add MaterialX Python bindings to sys.path."""
    # Already available?
    try:
        import PyMaterialXCore
        return True
    except ImportError:
        pass

    # pip install materialx puts bindings inside the MaterialX package dir.
    # Add that directory to sys.path so PyMaterialXCore is importable directly.
    try:
        import MaterialX as _mx_pkg
        pkg_dir = os.path.dirname(_mx_pkg.__file__)
        sys.path.insert(0, pkg_dir)
        import PyMaterialXCore  # noqa: F401
        return True
    except ImportError:
        pass

    # Check MATERIALX_ROOT environment variable
    mx_root = os.environ.get("MATERIALX_ROOT")
    if mx_root:
        # Try common build output locations
        candidates = [
            os.path.join(mx_root, "build", "bin", "Release"),
            os.path.join(mx_root, "build", "bin", "Debug"),
            os.path.join(mx_root, "build", "bin"),
            os.path.join(mx_root, "bin", "Release"),
            os.path.join(mx_root, "bin"),
            os.path.join(mx_root, "lib", "python"),
            mx_root,
        ]
        for path in candidates:
            if os.path.isdir(path):
                pyd_files = [f for f in os.listdir(path) if f.startswith("PyMaterialX") and f.endswith(".pyd")]
                so_files = [f for f in os.listdir(path) if f.startswith("PyMaterialX") and ".so" in f]
                if pyd_files or so_files:
                    sys.path.insert(0, path)
                    return True

    # Try relative to script location (if script is in MaterialX/scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    build_bin = os.path.join(repo_root, "build", "bin", "Release")
    if os.path.exists(build_bin):
        sys.path.insert(0, build_bin)
        return True

    return False


# Try to find MaterialX Python bindings
if not find_materialx_python():
    print("Error: Could not find MaterialX Python modules.")
    print()
    print("Please set the MATERIALX_ROOT environment variable to your MaterialX directory:")
    print()
    print("  For Git Bash / Linux / macOS:")
    print("    export MATERIALX_ROOT=/path/to/MaterialX")
    print()
    print("  For Windows Command Prompt:")
    print("    set MATERIALX_ROOT=C:\\path\\to\\MaterialX")
    print()
    print("  For Windows PowerShell:")
    print('    $env:MATERIALX_ROOT="C:\\path\\to\\MaterialX"')
    print()
    print("MaterialX must be built with MATERIALX_BUILD_PYTHON=ON")
    sys.exit(1)

try:
    import PyMaterialXCore as mx
    import PyMaterialXFormat as mx_format
except ImportError as e:
    print(f"Error: Could not import MaterialX Python modules: {e}")
    print()
    print("MATERIALX_ROOT is set to:", os.environ.get("MATERIALX_ROOT", "(not set)"))
    print("Ensure MaterialX is built with MATERIALX_BUILD_PYTHON=ON")
    sys.exit(1)

# Store the root for finding libraries
MATERIALX_ROOT = os.environ.get("MATERIALX_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_libraries_path(custom_path=None):
    """Find the MaterialX libraries directory."""
    if custom_path and os.path.isdir(custom_path):
        return custom_path

    # Check MATERIALX_LIBRARIES environment variable
    env_path = os.environ.get("MATERIALX_LIBRARIES")
    if env_path and os.path.isdir(env_path):
        return env_path

    # Check relative to MATERIALX_ROOT
    repo_libraries = os.path.join(MATERIALX_ROOT, "libraries")
    if os.path.isdir(repo_libraries):
        return repo_libraries

    # Check installed location (relative to Python module)
    try:
        module_dir = os.path.dirname(mx.__file__)
        # pip install materialx: libraries/ is alongside the bindings
        for candidate in [
            os.path.join(module_dir, "libraries"),
            os.path.join(module_dir, "..", "libraries"),
        ]:
            if os.path.isdir(candidate):
                return os.path.abspath(candidate)
    except:
        pass

    return None


def validate_xml_structure(filepath):
    """
    Validate XML structure and MaterialX-specific requirements per spec.

    Returns:
        Tuple of (is_valid, warnings_list, errors_list)
    """
    warnings = []
    errors = []

    try:
        # Check file can be parsed as XML
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Check root element is <materialx>
        if root.tag != 'materialx':
            errors.append(f"Root element must be <materialx>, found <{root.tag}>")
            errors.append("  💡 Fix: Change the root element to <materialx> in your XML file")
            return False, warnings, errors

        # Check required version attribute
        if 'version' not in root.attrib:
            errors.append("Root <materialx> element missing required 'version' attribute")
            errors.append("  💡 Fix: Add version=\"1.39\" (or appropriate version) to the <materialx> tag")
            errors.append("         Example: <materialx version=\"1.39\">")
        else:
            version = root.attrib['version']
            if not VALID_VERSION_PATTERN.match(version):
                errors.append(f"Version '{version}' must be in 'major.minor' format (e.g., '1.39')")
                errors.append("  💡 Fix: Use format like version=\"1.39\" or version=\"1.38\"")

        # Check colorspace if specified
        if 'colorspace' in root.attrib:
            colorspace = root.attrib['colorspace']
            if colorspace not in RESERVED_COLORSPACES:
                warnings.append(f"Colorspace '{colorspace}' is not in the reserved colorspace list")
                warnings.append("  💡 Consider using a standard colorspace like:")
                warnings.append("     - 'lin_rec709' (linear color space)")
                warnings.append("     - 'srgb_texture' (sRGB for textures)")
                warnings.append("     - 'acescg' (ACEScg color space)")

        # Validate element names throughout document
        for elem in root.iter():
            if 'name' in elem.attrib:
                name = elem.attrib['name']
                if not VALID_NAME_PATTERN.match(name):
                    errors.append(
                        f"Element <{elem.tag}> name '{name}' violates naming rules: "
                        "must use ASCII letters, numbers, underscores only, and cannot start with a digit"
                    )
                    errors.append(f"  💡 Fix: Rename '{name}' to follow these rules:")
                    errors.append("     - Start with letter or underscore (A-Z, a-z, _)")
                    errors.append("     - Continue with letters, numbers, or underscores")
                    errors.append("     - No spaces or special characters")

                    # Try to suggest a valid name
                    suggested_name = re.sub(r'^[0-9]+', '', name)  # Remove leading digits
                    suggested_name = re.sub(r'[^A-Za-z0-9_]', '_', suggested_name)  # Replace invalid chars
                    if suggested_name and suggested_name != name and VALID_NAME_PATTERN.match(suggested_name):
                        errors.append(f"     - Suggestion: '{suggested_name}'")

        return True, warnings, errors

    except ET.ParseError as e:
        errors.append(f"XML parsing error: {e}")
        errors.append("  💡 Fix: Common XML issues to check:")
        errors.append("     - Ensure all tags are properly closed")
        errors.append("     - Check for unescaped special characters (<, >, &)")
        errors.append("     - Verify quotes around attribute values")
        errors.append("     - Look for mismatched opening/closing tags")
        return False, warnings, errors
    except Exception as e:
        errors.append(f"Error reading file: {e}")
        errors.append("  💡 Check: File exists, is readable, and is a valid text file")
        return False, warnings, errors


def get_error_suggestions(error_text):
    """
    Analyze error text and provide helpful suggestions for fixing common issues.

    Args:
        error_text: The error message string

    Returns:
        String with suggested fix, or None if no specific suggestion available
    """
    error_lower = error_text.lower()

    # Node definition not found
    if "could not find a nodedef" in error_lower or "nodedef" in error_lower and ("not found" in error_lower or "missing" in error_lower):
        return ("💡 Suggestion: This node references a node definition that doesn't exist.\n"
                "      → Check the 'node' attribute matches an available nodedef\n"
                "      → Ensure required libraries are included (pbrlib, stdlib, etc.)\n"
                "      → Verify spelling and capitalization of the node type")

    # Invalid connection/input reference
    if "invalid" in error_lower and ("connection" in error_lower or "input" in error_lower):
        return ("💡 Suggestion: An input connection references a node or output that doesn't exist.\n"
                "      → Check the 'nodename' attribute points to an actual node in the graph\n"
                "      → Verify the 'output' attribute matches an output of the referenced node\n"
                "      → Ensure nodes are defined before they're referenced")

    # Type mismatch
    if "type" in error_lower and ("mismatch" in error_lower or "incompatible" in error_lower or "cannot convert" in error_lower):
        return ("💡 Suggestion: Data types don't match between connected nodes.\n"
                "      → Check input/output types are compatible (e.g., color3 to color3)\n"
                "      → Use conversion nodes if needed (e.g., convert float to color)\n"
                "      → Review the MaterialX type system documentation")

    # Missing required input
    if "required" in error_lower and "input" in error_lower:
        return ("💡 Suggestion: A node is missing a required input parameter.\n"
                "      → Check the nodedef to see which inputs are required\n"
                "      → Add the missing input element with appropriate value or connection\n"
                "      → Review node documentation for default behavior")

    # Output not found
    if "output" in error_lower and ("not found" in error_lower or "does not exist" in error_lower):
        return ("💡 Suggestion: Referenced output doesn't exist on the source node.\n"
                "      → Check the node's available outputs in its nodedef\n"
                "      → Remove the 'output' attribute if connecting to the default output\n"
                "      → Verify spelling of the output name")

    # Cycle/circular dependency
    if "cycle" in error_lower or "circular" in error_lower or "dependency" in error_lower:
        return ("💡 Suggestion: Circular dependency detected in node graph.\n"
                "      → Review node connections to find the loop\n"
                "      → Ensure data flows in one direction only\n"
                "      → Check for nodes that reference each other directly or indirectly")

    # Invalid name
    if "invalid" in error_lower and "name" in error_lower:
        return ("💡 Suggestion: Element name doesn't follow MaterialX naming rules.\n"
                "      → Names must start with a letter or underscore\n"
                "      → Use only letters, numbers, and underscores (no spaces or special chars)\n"
                "      → Avoid starting names with numbers")

    # Duplicate name
    if "duplicate" in error_lower and "name" in error_lower:
        return ("💡 Suggestion: Two elements have the same name in the same scope.\n"
                "      → Rename one of the conflicting elements\n"
                "      → Use more descriptive, unique names\n"
                "      → Check for copy-paste errors")

    # Interface mismatch
    if "interface" in error_lower and ("mismatch" in error_lower or "does not match" in error_lower):
        return ("💡 Suggestion: Node graph interface doesn't match its nodedef.\n"
                "      → Ensure graph inputs/outputs match the nodedef declaration\n"
                "      → Check parameter names and types align exactly\n"
                "      → Verify the 'nodedef' attribute references the correct definition")

    # File not found / include issue
    if "file not found" in error_lower or "include" in error_lower or "xinclude" in error_lower:
        return ("💡 Suggestion: Referenced file cannot be found.\n"
                "      → Check the file path in the xinclude is correct\n"
                "      → Ensure included files exist in the specified location\n"
                "      → Use relative paths from the document's directory")

    # Colorspace issues
    if "colorspace" in error_lower:
        return ("💡 Suggestion: Colorspace issue detected.\n"
                "      → Use standard colorspace names (lin_rec709, srgb_texture, etc.)\n"
                "      → Check colorspace attribute on document or elements\n"
                "      → Ensure colorspace is appropriate for the data type")

    # Unit issues
    if "unit" in error_lower and ("invalid" in error_lower or "unknown" in error_lower):
        return ("💡 Suggestion: Invalid unit specified.\n"
                "      → Use standard units (meter, centimeter, degree, radian, etc.)\n"
                "      → Check unittype attribute matches the expected category\n"
                "      → Review MaterialX units documentation")

    # Version issues
    if "version" in error_lower:
        return ("💡 Suggestion: MaterialX version issue.\n"
                "      → Ensure 'version' attribute is in major.minor format (e.g., '1.39')\n"
                "      → Use a supported MaterialX version\n"
                "      → Check compatibility between document and libraries")

    return None


def format_validation_errors(error_msg):
    """
    Parse and format MaterialX validation error messages with helpful suggestions.

    Returns:
        List of formatted error strings with suggestions
    """
    if not error_msg:
        return []

    errors = []
    # Split by common error delimiters
    for line in error_msg.split('\n'):
        line = line.strip()
        if line:
            errors.append(f"  • {line}")

            # Add suggestion if available
            suggestion = get_error_suggestions(line)
            if suggestion:
                # Indent the suggestion properly
                for suggestion_line in suggestion.split('\n'):
                    errors.append(f"    {suggestion_line}")

    return errors if errors else [f"  • {error_msg}"]


def check_nodename_references(doc):
    """
    Check that all nodename attributes within node graphs resolve to existing nodes.

    MaterialX's built-in validate() will catch dangling nodename references in
    standalone documents, but when a file shares a name with a standard library
    file (e.g. open_pbr_surface.mtlx), the library copy shadows the user's file
    and the with-libraries validation silently tests the library version instead.
    Running this check on the standalone document catches those cases.

    Returns:
        List of error strings, empty if all nodename references are valid.
    """
    errors = []
    for ng in doc.getNodeGraphs():
        node_names = {node.getName() for node in ng.getNodes()}
        for node in ng.getNodes():
            for inp in node.getInputs():
                ref = inp.getNodeName()
                if ref and ref not in node_names:
                    errors.append(
                        f"  • Dangling nodename reference in NodeGraph "
                        f"'{ng.getName()}': node '{node.getName()}' input "
                        f"'{inp.getName()}' references missing node '{ref}'"
                    )
                    errors.append(
                        "    💡 Fix: The referenced node was removed or renamed. "
                        "Either restore the node or update this input to use "
                        "'interfacename' (to connect to the graph interface) or 'value'."
                    )
    return errors


def check_library_shadowing(filepath, lib_path):
    """
    Warn if the user's file has the same basename as a file in the standard libraries.

    When this happens, loadLibraries() loads the library copy first, and the
    subsequent readFromXmlFileBase() for the user's file is effectively ignored
    for any elements whose names already exist in the document — so with-libraries
    validation tests the library version, not the user's edits.

    Returns:
        Warning string, or None if no shadowing detected.
    """
    user_basename = os.path.basename(filepath)
    for dirpath, _, filenames in os.walk(lib_path):
        for fname in filenames:
            if fname == user_basename:
                lib_file = os.path.join(dirpath, fname)
                return (
                    f"  ⚠ File '{user_basename}' also exists in the standard libraries:\n"
                    f"      {lib_file}\n"
                    f"    When libraries are loaded, the library copy is used for validation\n"
                    f"    instead of your file. Nodename reference checks are run on your\n"
                    f"    file directly (standalone) to compensate."
                )
    return None


def generate_material_report(doc, filepath, user_elements=None):
    """
    Generate a detailed report and visualization of the MaterialX document structure.

    Args:
        doc: MaterialX document
        filepath: Path to the .mtlx file
        user_elements: Dict with sets of user-defined element names

    Returns:
        String containing the formatted report
    """
    if user_elements is None:
        user_elements = {'nodedefs': set(), 'nodegraphs': set(), 'materials': set()}
    lines = []
    lines.append("=" * 80)
    lines.append(f"MaterialX Document Report: {os.path.basename(filepath)}")
    lines.append("=" * 80)
    lines.append("")

    # Document overview
    materials = doc.getMaterialNodes()
    all_node_defs = doc.getNodeDefs()
    all_node_graphs = doc.getNodeGraphs()

    # Use tracked user element names
    user_nodedef_names = user_elements.get('nodedefs', set())
    user_nodegraph_names = user_elements.get('nodegraphs', set())
    user_material_names = user_elements.get('materials', set())

    # Filter to user-defined elements
    if user_nodedef_names:
        node_defs = [nd for nd in all_node_defs if nd.getName() in user_nodedef_names]
    else:
        node_defs = [nd for nd in all_node_defs if not nd.hasSourceUri()]

    if user_nodegraph_names:
        impl_node_graphs = [ng for ng in all_node_graphs if ng.getName() in user_nodegraph_names and ng.getNodeDefString()]
        scene_node_graphs = [ng for ng in all_node_graphs if ng.getName() in user_nodegraph_names and not ng.getNodeDefString()]
    else:
        impl_node_graphs = [ng for ng in all_node_graphs if ng.getNodeDefString() and not ng.hasSourceUri()]
        scene_node_graphs = [ng for ng in all_node_graphs if not ng.getNodeDefString() and not ng.hasSourceUri()]

    if user_material_names:
        materials = [m for m in materials if m.getName() in user_material_names]

    shader_nodes = [n for n in doc.getNodes() if n.getType() == 'surfaceshader' or n.getCategory() in ['surface', 'volume', 'displacement']]
    looks = doc.getLooks()

    # Determine file type
    is_library = len(node_defs) > 0 or len(impl_node_graphs) > 0
    is_scene = len(materials) > 0 or len(scene_node_graphs) > 0 or len(looks) > 0

    lines.append("Document Overview:")
    if is_library:
        lines.append(f"  Type: Library/Definition File")
        lines.append(f"  Node Definitions:     {len(node_defs)}")
        lines.append(f"  Implementation Graphs: {len(impl_node_graphs)}")
    if is_scene:
        if is_library:
            lines.append(f"  Type: Also contains Scene Elements")
        else:
            lines.append(f"  Type: Scene/Material File")
        lines.append(f"  Materials:    {len(materials)}")
        lines.append(f"  Node Graphs:  {len(scene_node_graphs)}")
        lines.append(f"  Shader Nodes: {len(shader_nodes)}")
        lines.append(f"  Looks:        {len(looks)}")
    lines.append("")

    # Node Definitions section
    if node_defs:
        lines.append("=" * 80)
        lines.append("NODE DEFINITIONS")
        lines.append("=" * 80)
        for nodedef in node_defs:
            lines.append("")
            lines.append(f"NodeDef: {nodedef.getName()}")
            lines.append(f"  Node Type: {nodedef.getNodeString()}")
            if nodedef.getNodeGroup():
                lines.append(f"  Node Group: {nodedef.getNodeGroup()}")
            if nodedef.getVersionString():
                lines.append(f"  Version: {nodedef.getVersionString()}")

            # Show inputs
            inputs = nodedef.getInputs()
            if inputs:
                lines.append(f"  Inputs ({len(inputs)}):")
                for inp in inputs[:10]:  # Limit to first 10 to avoid huge output
                    value_str = ""
                    if inp.hasValueString():
                        value_str = f" = {inp.getValueString()}"
                    lines.append(f"    • {inp.getName()} ({inp.getType()}){value_str}")
                if len(inputs) > 10:
                    lines.append(f"    ... and {len(inputs) - 10} more inputs")

            # Show outputs
            outputs = nodedef.getOutputs()
            if outputs:
                lines.append(f"  Outputs:")
                for out in outputs:
                    lines.append(f"    • {out.getName()} ({out.getType()})")

            # Find implementation
            impl_graph = doc.getNodeGraph(f"NG_{nodedef.getNodeString()}_{outputs[0].getType() if outputs else 'shader'}")
            if not impl_graph:
                # Try alternative naming
                for ng in impl_node_graphs:
                    if ng.getNodeDefString() == nodedef.getName():
                        impl_graph = ng
                        break

            if impl_graph:
                lines.append(f"  Implementation: {impl_graph.getName()}")
                impl_nodes = impl_graph.getNodes()
                lines.append(f"    Nodes in implementation: {len(impl_nodes)}")

    # Implementation Node Graphs section
    if impl_node_graphs:
        lines.append("")
        lines.append("=" * 80)
        lines.append("IMPLEMENTATION NODE GRAPHS")
        lines.append("=" * 80)

        for ng in impl_node_graphs:
            lines.append("")
            lines.append(f"NodeGraph: {ng.getName()}")
            nodedef_name = ng.getNodeDefString()
            if nodedef_name:
                lines.append(f"  Implements NodeDef: {nodedef_name}")

            # Get nodes
            nodes = ng.getNodes()
            lines.append(f"  Total Nodes: {len(nodes)}")

            # Sample some key nodes (first few and last few)
            if len(nodes) > 0:
                lines.append(f"  Sample Nodes:")
                sample_count = min(5, len(nodes))
                for node in nodes[:sample_count]:
                    lines.append(f"    • {node.getName()} [{node.getType()}]")
                if len(nodes) > sample_count:
                    lines.append(f"    ... and {len(nodes) - sample_count} more nodes")

    # Materials section
    if materials:
        lines.append("")
        lines.append("=" * 80)
        lines.append("MATERIALS")
        lines.append("=" * 80)
        for material in materials:
            lines.append("")
            lines.append(f"Material: {material.getName()}")
            lines.append(f"  Type: {material.getType()}")

            # Get shader references from inputs
            inputs = material.getInputs()
            shader_inputs = [inp for inp in inputs if 'shader' in inp.getName().lower()]

            for shader_input in shader_inputs:
                lines.append(f"  Shader Input: {shader_input.getName()}")

                # Check for node name reference
                node_name = shader_input.getNodeName()
                if node_name:
                    lines.append(f"    → References Node: {node_name}")

                    # Try to find the referenced node
                    ref_node = doc.getNode(node_name)
                    if ref_node:
                        lines.append(f"      Type: {ref_node.getType()}")
                        lines.append(f"      Category: {ref_node.getCategory()}")

                # Check for nodegraph reference
                nodegraph_name = shader_input.getNodeGraphString()
                if nodegraph_name:
                    lines.append(f"    → References NodeGraph: {nodegraph_name}")

    # Scene Node Graphs section
    if scene_node_graphs:
        lines.append("")
        lines.append("=" * 80)
        lines.append("SCENE NODE GRAPHS")
        lines.append("=" * 80)

        for ng in scene_node_graphs:
            lines.append("")
            lines.append(f"NodeGraph: {ng.getName()}")

            # Get outputs
            outputs = ng.getOutputs()
            if outputs:
                lines.append(f"  Outputs: {', '.join([o.getName() for o in outputs])}")

            # Get nodes
            nodes = ng.getNodes()
            if nodes:
                lines.append(f"  Nodes ({len(nodes)}):")
                lines.append("")

                # Display each node
                for node in nodes:
                    lines.append(f"    [{node.getName()}]")
                    lines.append(f"      Type: {node.getType()}")
                    lines.append(f"      Category: {node.getCategory()}")

                    # Show inputs
                    inputs = node.getInputs()
                    if inputs:
                        lines.append(f"      Inputs:")
                        for inp in inputs:
                            value_str = ""
                            if inp.hasValueString():
                                value_str = f" = {inp.getValueString()}"

                            node_ref = inp.getNodeName()
                            if node_ref:
                                output_ref = inp.getOutputString()
                                ref_str = node_ref
                                if output_ref:
                                    ref_str += f".{output_ref}"
                                lines.append(f"        • {inp.getName()} ← {ref_str}")
                            else:
                                lines.append(f"        • {inp.getName()}{value_str}")

                    # Show outputs
                    outputs = node.getOutputs()
                    if outputs:
                        lines.append(f"      Outputs:")
                        for out in outputs:
                            lines.append(f"        • {out.getName()} ({out.getType()})")

                    lines.append("")

    # Standalone shader nodes
    if shader_nodes:
        lines.append("=" * 80)
        lines.append("SHADER NODES")
        lines.append("=" * 80)
        for shader in shader_nodes:
            lines.append("")
            lines.append(f"Shader: {shader.getName()}")
            lines.append(f"  Type: {shader.getType()}")
            lines.append(f"  Category: {shader.getCategory()}")

            inputs = shader.getInputs()
            if inputs:
                lines.append(f"  Inputs:")
                for inp in inputs:
                    node_ref = inp.getNodeName()
                    ng_ref = inp.getNodeGraphString()

                    if node_ref:
                        lines.append(f"    • {inp.getName()} ← Node: {node_ref}")
                    elif ng_ref:
                        lines.append(f"    • {inp.getName()} ← NodeGraph: {ng_ref}")
                    elif inp.hasValueString():
                        lines.append(f"    • {inp.getName()} = {inp.getValueString()}")

    # Looks section
    if looks:
        lines.append("")
        lines.append("=" * 80)
        lines.append("LOOKS")
        lines.append("=" * 80)
        for look in looks:
            lines.append("")
            lines.append(f"Look: {look.getName()}")

            material_assigns = look.getMaterialAssigns()
            if material_assigns:
                lines.append(f"  Material Assignments:")
                for assign in material_assigns:
                    lines.append(f"    • {assign.getName()}")
                    lines.append(f"      Material: {assign.getMaterial()}")
                    geom = assign.getGeom()
                    if geom:
                        lines.append(f"      Geometry: {geom}")

    # Visual tree representation
    if materials or scene_node_graphs or impl_node_graphs:
        lines.append("")
        lines.append("=" * 80)
        lines.append("VISUAL STRUCTURE")
        lines.append("=" * 80)
        lines.append("")

        # Show node definitions
        if node_defs:
            for nodedef in node_defs:
                lines.append(f"📚 NodeDef: {nodedef.getName()}")
                lines.append(f"  └── 🏷️  Node Type: {nodedef.getNodeString()}")

                # Find implementation
                impl_graph = None
                for ng in impl_node_graphs:
                    if ng.getNodeDefString() == nodedef.getName():
                        impl_graph = ng
                        break

                if impl_graph:
                    lines.append(f"      └── 🔶 Implementation: {impl_graph.getName()}")
                    nodes = impl_graph.getNodes()
                    lines.append(f"          └── 📊 {len(nodes)} nodes in graph")
                lines.append("")

        # Show material hierarchy
        for material in materials:
            lines.append(f"📦 Material: {material.getName()}")

            # Get shader references from inputs
            inputs = material.getInputs()
            shader_inputs = [inp for inp in inputs if 'shader' in inp.getName().lower()]

            for i, shader_input in enumerate(shader_inputs):
                is_last_input = (i == len(shader_inputs) - 1)
                prefix = "└──" if is_last_input else "├──"

                node_name = shader_input.getNodeName()
                nodegraph_name = shader_input.getNodeGraphString()

                if node_name:
                    lines.append(f"  {prefix} 🔗 {shader_input.getName()} → Node: {node_name}")
                    ref_node = doc.getNode(node_name)
                    if ref_node:
                        indent = "      " if is_last_input else "  │   "
                        lines.append(f"{indent}└── 🔷 Type: {ref_node.getType()}")

                elif nodegraph_name:
                    lines.append(f"  {prefix} 🔗 {shader_input.getName()} → NodeGraph: {nodegraph_name}")

            lines.append("")

        # Show scene node graph hierarchy
        for ng in scene_node_graphs:
            lines.append(f"🔶 NodeGraph: {ng.getName()}")

            # Get outputs first
            outputs = ng.getOutputs()
            if outputs:
                for output in outputs:
                    lines.append(f"  ├── 📤 Output: {output.getName()} ({output.getType()})")

            # Build dependency order for visualization
            nodes = ng.getNodes()
            node_deps = {}

            for node in nodes:
                deps = set()
                for inp in node.getInputs():
                    node_name = inp.getNodeName()
                    if node_name:
                        deps.add(node_name)
                node_deps[node.getName()] = deps

            # Simple topological ordering (nodes with no deps first)
            displayed = set()
            levels = []

            while len(displayed) < len(nodes):
                current_level = []
                for node_name, deps in node_deps.items():
                    if node_name not in displayed and deps.issubset(displayed):
                        current_level.append(node_name)

                if not current_level:
                    # Circular dependency or remaining nodes
                    current_level = [name for name in node_deps.keys() if name not in displayed]

                levels.append(current_level)
                displayed.update(current_level)

            # Display nodes by level
            for level_idx, level_nodes in enumerate(levels):
                for node_idx, node_name in enumerate(level_nodes):
                    node = ng.getNode(node_name)
                    if node:
                        is_last = (level_idx == len(levels) - 1) and (node_idx == len(level_nodes) - 1)
                        prefix = "└──" if is_last else "├──"

                        lines.append(f"  {prefix} 🔷 {node_name} [{node.getType()}]")

                        # Show connections
                        indent = "      " if is_last else "  │   "
                        for inp in node.getInputs():
                            node_ref = inp.getNodeName()
                            if node_ref:
                                output_ref = inp.getOutputString()
                                ref_str = node_ref
                                if output_ref:
                                    ref_str += f".{output_ref}"
                                lines.append(f"{indent}↳ {inp.getName()} ← {ref_str}")

            lines.append("")

    lines.append("=" * 80)
    lines.append("✓ Document is VALID")
    lines.append("=" * 80)

    return "\n".join(lines)


def validate_mtlx(filepath, libraries_path=None, verbose=False):
    """
    Validate a MaterialX file according to the MaterialX specification.

    Args:
        filepath: Path to the .mtlx file
        libraries_path: Optional path to MaterialX libraries
        verbose: Print detailed information

    Returns:
        Tuple of (is_valid, error_message, document, user_elements_dict, validation_details)
    """
    validation_details = {
        'xml_valid': False,
        'xml_warnings': [],
        'xml_errors': [],
        'standalone_valid': False,
        'standalone_errors': [],
        'nodename_errors': [],
        'shadowing_warning': None,
        'with_libs_valid': False,
        'with_libs_errors': []
    }

    # Check file exists
    if not os.path.isfile(filepath):
        error_msg = (f"File not found: {filepath}\n\n"
                    "💡 Troubleshooting:\n"
                    "  • Check the file path is correct\n"
                    "  • Ensure the file exists in the specified location\n"
                    "  • Use absolute path or path relative to current directory\n"
                    "  • Check for typos in the filename")
        return False, error_msg, None, None, validation_details

    # Find libraries
    lib_path = find_libraries_path(libraries_path)
    if not lib_path:
        error_msg = ("Could not find MaterialX libraries directory.\n\n"
                    "💡 Solutions:\n"
                    "  1. Use the --libraries option:\n"
                    "     python validate_mtlx.py file.mtlx --libraries /path/to/libraries\n\n"
                    "  2. Set MATERIALX_LIBRARIES environment variable:\n"
                    "     export MATERIALX_LIBRARIES=/path/to/MaterialX/libraries\n\n"
                    "  3. Set MATERIALX_ROOT to your MaterialX installation:\n"
                    "     export MATERIALX_ROOT=/path/to/MaterialX")
        return False, error_msg, None, None, validation_details

    # Step 1: Validate XML structure and spec compliance
    if verbose:
        print("Step 1: Validating XML structure and naming conventions...")

    xml_valid, xml_warnings, xml_errors = validate_xml_structure(filepath)
    validation_details['xml_valid'] = xml_valid
    validation_details['xml_warnings'] = xml_warnings
    validation_details['xml_errors'] = xml_errors

    if not xml_valid:
        error_msg = "XML validation failed:\n" + "\n".join(xml_errors)
        return False, error_msg, None, None, validation_details

    if verbose and xml_warnings:
        print("  Warnings:")
        for warning in xml_warnings:
            print(f"    • {warning}")
    if verbose:
        print("  ✓ XML structure valid")
        print()

    if verbose:
        print(f"MaterialX Version: {mx.getVersionString()}")
        print(f"Libraries path: {lib_path}")
        print(f"Input file: {filepath}")
        print()

    try:
        file_dir = os.path.dirname(os.path.abspath(filepath))

        # Step 2: Validate standalone document (per spec: "XIncluded documents must themselves be valid")
        if verbose:
            print("Step 2: Validating standalone document...")

        standalone_doc = mx.createDocument()
        standalone_search_path = mx_format.FileSearchPath(file_dir)
        mx_format.readFromXmlFileBase(standalone_doc, filepath, standalone_search_path)

        standalone_valid, standalone_error = standalone_doc.validate()
        validation_details['standalone_valid'] = standalone_valid

        if not standalone_valid:
            validation_details['standalone_errors'] = format_validation_errors(standalone_error)
            if verbose:
                print("  ✗ Standalone validation failed")
                for err in validation_details['standalone_errors']:
                    print(f"    {err}")
        else:
            if verbose:
                print("  ✓ Standalone document valid")

        if verbose:
            print()

        # Step 2b: Check nodename references in the standalone document.
        # This catches dangling references that with-libraries validation misses
        # when the user's file is shadowed by a same-named standard library file.
        nodename_errors = check_nodename_references(standalone_doc)
        validation_details['nodename_errors'] = nodename_errors
        if nodename_errors:
            if verbose:
                print("  ✗ Nodename reference check failed:")
                for err in nodename_errors:
                    print(f"    {err}")
        else:
            if verbose:
                print("  ✓ All nodename references resolve")
        if verbose:
            print()

        # Step 2c: Warn if this file is shadowed by a standard library file.
        shadowing_warning = check_library_shadowing(filepath, lib_path)
        validation_details['shadowing_warning'] = shadowing_warning
        if shadowing_warning and verbose:
            print(shadowing_warning)
            print()

        # Step 3: Load user file to track user-defined elements
        user_doc = mx.createDocument()
        user_search_path = mx_format.FileSearchPath(file_dir)
        mx_format.readFromXmlFileBase(user_doc, filepath, user_search_path)

        # Track user-defined elements
        user_nodedef_names = {nd.getName() for nd in user_doc.getNodeDefs()}
        user_nodegraph_names = {ng.getName() for ng in user_doc.getNodeGraphs()}
        user_material_names = {m.getName() for m in user_doc.getMaterialNodes()}

        # Now create document with standard libraries for validation
        doc = mx.createDocument()

        # Search path should be parent of 'libraries' folder
        lib_parent = os.path.dirname(lib_path)
        search_path = mx_format.FileSearchPath(lib_parent)

        # Step 4: Load standard libraries
        stdlib_files = [
            "libraries/stdlib",
            "libraries/pbrlib",
            "libraries/bxdf",
            "libraries/lights"
        ]

        if verbose:
            print("Step 3: Loading standard libraries for reference validation...")

        mx_format.loadLibraries(stdlib_files, search_path, doc)

        if verbose:
            print(f"  Loaded {len(doc.getNodeDefs())} node definitions")
            print()

        # Add the file's directory to search path for resolving includes
        search_path.append(mx_format.FilePath(file_dir))

        # Load the user's document
        if verbose:
            print(f"  Loading {os.path.basename(filepath)}...")

        mx_format.readFromXmlFileBase(doc, filepath, search_path)

        # Store user element names for report generation
        user_elements = {
            'nodedefs': user_nodedef_names,
            'nodegraphs': user_nodegraph_names,
            'materials': user_material_names
        }

        if verbose:
            # Print document summary
            materials = doc.getMaterialNodes()
            node_graphs = [ng for ng in doc.getNodeGraphs() if not ng.hasSourceUri()]
            looks = doc.getLooks()

            print(f"  Materials: {len(materials)}")
            print(f"  Node graphs: {len(node_graphs)}")
            print(f"  Looks: {len(looks)}")

            if materials:
                print(f"  Material names: {[m.getName() for m in materials]}")
            print()

        # Step 5: Validate with libraries (full validation)
        if verbose:
            print("Step 4: Validating with standard libraries...")

        with_libs_valid, with_libs_error = doc.validate()
        validation_details['with_libs_valid'] = with_libs_valid

        if not with_libs_valid:
            validation_details['with_libs_errors'] = format_validation_errors(with_libs_error)
            if verbose:
                print("  ✗ Validation failed")
                for err in validation_details['with_libs_errors']:
                    print(f"    {err}")
        else:
            if verbose:
                print("  ✓ Document valid with libraries")

        if verbose:
            print()

        # Determine overall validity.
        # nodename_errors are always fatal — they represent broken connections in
        # the user's file that with-libraries validation cannot see when the file
        # is shadowed by a same-named standard library file.
        # Standalone validation failures (e.g. missing defaultgeomprops that only
        # exist in the stdlib) are treated as warnings, not errors.
        overall_valid = with_libs_valid and not nodename_errors

        if overall_valid:
            if not standalone_valid or shadowing_warning:
                validation_details['has_warnings'] = True
            return True, None, doc, user_elements, validation_details
        else:
            error_parts = []
            if nodename_errors:
                error_parts.append("Nodename reference errors (broken connections in your file):")
                error_parts.extend(nodename_errors)
            if not with_libs_valid:
                if error_parts:
                    error_parts.append("")
                error_parts.append("Validation errors:")
                error_parts.extend(validation_details['with_libs_errors'])

            error_msg = "\n".join(error_parts)
            return False, error_msg, None, None, validation_details

    except Exception as e:
        validation_details['exception'] = str(e)
        return False, f"Error loading file: {str(e)}", None, None, validation_details


def main():
    parser = argparse.ArgumentParser(
        description="Validate a MaterialX (.mtlx) file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s material.mtlx
  %(prog)s material.mtlx --verbose
  %(prog)s material.mtlx --libraries /path/to/materialx/libraries

Environment Variables:
  MATERIALX_LIBRARIES  Path to MaterialX libraries directory
        """
    )

    parser.add_argument(
        "file",
        help="Path to the .mtlx file to validate"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed information during validation"
    )

    parser.add_argument(
        "-l", "--libraries",
        metavar="PATH",
        help="Path to MaterialX libraries directory"
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Print MaterialX version and exit"
    )

    args = parser.parse_args()

    if args.version:
        print(f"MaterialX {mx.getVersionString()}")
        sys.exit(0)

    # Validate the file
    is_valid, error_msg, doc, user_elements, validation_details = validate_mtlx(
        args.file,
        libraries_path=args.libraries,
        verbose=args.verbose
    )

    # Print result
    if is_valid:
        if not args.verbose:
            print()
            print("=" * 80)
            print("VALIDATION SUMMARY")
            print("=" * 80)
            print(f"File: {args.file}")
            print("Status: ✓ VALID")

            # Show warnings
            has_warnings = False

            if validation_details.get('xml_warnings'):
                has_warnings = True
                print("\nXML Warnings:")
                for warning in validation_details['xml_warnings']:
                    print(f"  • {warning}")

            if validation_details.get('shadowing_warning'):
                has_warnings = True
                print()
                print(validation_details['shadowing_warning'])

            if not validation_details.get('standalone_valid') and validation_details.get('standalone_errors'):
                has_warnings = True
                print("\nStandalone Validation Warnings:")
                print("  (File depends on standard libraries - this is normal for most MaterialX files)")
                for error in validation_details['standalone_errors'][:5]:  # Show first 5
                    print(f"  {error}")
                if len(validation_details['standalone_errors']) > 5:
                    print(f"  ... and {len(validation_details['standalone_errors']) - 5} more")

            if has_warnings:
                print()
            else:
                print("No warnings")
            print()

        # Generate and print detailed report
        report = generate_material_report(doc, args.file, user_elements)
        print(report)
        print()
        sys.exit(0)
    else:
        print()
        print("=" * 80)
        print("❌ VALIDATION FAILED")
        print("=" * 80)
        print(f"File: {args.file}")
        print()

        has_errors = False

        if validation_details.get('xml_errors'):
            has_errors = True
            print("📋 XML Structure Errors:")
            print("─" * 80)
            for error in validation_details['xml_errors']:
                print(f"  {error}")
            print()

        if validation_details.get('nodename_errors'):
            has_errors = True
            print("🔗 Broken Node References:")
            print("─" * 80)
            print("These inputs reference nodes that no longer exist in the graph:")
            print()
            for error in validation_details['nodename_errors']:
                print(error)
            print()
            if validation_details.get('shadowing_warning'):
                print(validation_details['shadowing_warning'])
                print()

        if validation_details.get('with_libs_errors'):
            has_errors = True
            print("🔍 MaterialX Validation Errors:")
            print("─" * 80)
            print("These errors were found when validating against MaterialX standards:")
            print()
            for error in validation_details['with_libs_errors']:
                print(error)
            print()

        if error_msg and not validation_details.get('with_libs_errors') and not validation_details.get('xml_errors') and not validation_details.get('nodename_errors'):
            has_errors = True
            print("❌ Errors:")
            print("─" * 80)
            print(error_msg)
            print()

        # Show standalone errors as additional context (not primary failure reason)
        if validation_details.get('standalone_errors') and not validation_details.get('with_libs_errors'):
            print("📝 Additional Information (Standalone Validation):")
            print("─" * 80)
            for error in validation_details['standalone_errors']:
                print(error)
            print()

        # Add helpful summary footer
        if has_errors:
            print("─" * 80)
            print("💡 Quick Tips:")
            print("  • Review error messages above for specific suggestions")
            print("  • Check MaterialX documentation: https://materialx.org")
            print("  • Validate incrementally as you make changes")
            print("  • Use --verbose flag for more detailed validation steps")
            print("=" * 80)

        sys.exit(1)


if __name__ == "__main__":
    main()
