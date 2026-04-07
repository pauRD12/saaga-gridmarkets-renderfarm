"""
Houdini Node Graph Scanner (hython)

This snippet demonstrates a headless approach to parsing a Houdini file (.hip) to find
render nodes (ROPs) and discover their dependencies. This allows us to submit Compositing jobs
to the cloud farm that automatically wait for Render jobs to finish.

Usage: executed via `hython` during the pre-flight phase.
"""

import sys
try:
    import hou
except ImportError:
    print("Error: This script must be run within hython or Houdini.")
    sys.exit(1)

def discover_render_jobs(target_names: list[str] = None) -> list[dict]:
    """
    Discover all render jobs from specified OUT_* targets in the /out network.
    
    This function traverses Houdini's node dependencies backwards starting from our specified 
    OUT targets. It separates standard rendering nodes (Karma) from Fetch/Compositing nodes
    so we can build an accurate cloud submission dependency graph.
    """
    out_node = hou.node("/out")
    if not out_node:
        raise RuntimeError("No /out node found in this HIP file.")

    # Find the specific 'OUT_*' nodes the user requested, skipping bypassed nodes.
    targets = []
    if target_names is None:
        targets = [
            node for node in out_node.children()
            if node.name().startswith("OUT_") and not node.isBypassed()
        ]
    else:
        for name in target_names:
            node = out_node.node(name)
            if node and not node.isBypassed():
                targets.append(node)

    if not targets:
        return []

    # Map paths to node objects to ensure we don't submit the same job twice
    all_deps = {}

    for target in targets:
        # Get all immediate inputs (dependencies) for this target node
        input_deps = target.inputDependencies()
        
        for dep_node, _times in input_deps:
            path = dep_node.path()
            
            # Skip the parent OUT_* wrapper nodes
            if dep_node.name().startswith("OUT_"):
                continue

            # If a dependency is a COP node located in /img (Compositing), 
            # we need to find the Fetch node in /out that references it 
            # so GridMarkets can trigger the composite properly.
            if not path.startswith("/out/"):
                fetch_node = _find_fetch_for_cop(path)
                if fetch_node:
                    path = fetch_node.path()
                    dep_node = fetch_node

            all_deps[path] = dep_node

    # Compile the discovered jobs into a structured dictionary
    jobs = []
    for path, node in all_deps.items():
        # Extrapolate frames to render
        frames = _get_frame_range(node)
        
        job_info = {
            "name": node.name(),
            "path": path,
            "node_type": node.type().name(),
            "frames": frames,
            "dependencies": _get_node_dependencies(node),  # Recursively find what this node waits on
        }
        jobs.append(job_info)

    return jobs

def _get_frame_range(node) -> str:
    """Helper to extract standard 'start end step' from a ROP node."""
    if node.type().name() == "fetch":
        # Follow the fetch reference
        source_parm = node.parm("source")
        if source_parm:
            source_node = hou.node(source_parm.eval())
            if source_node:
                return _get_frame_range(source_node)

    f1, f2, f3 = node.parm("f1"), node.parm("f2"), node.parm("f3")
    if f1 and f2:
        start = int(f1.eval())
        end = int(f2.eval())
        step = int(f3.eval()) if f3 else 1
        return f"{start} {end} {step}"
    
    return "1 1 1"

def _get_node_dependencies(node) -> list:
    """Finds what nodes this node depends on (e.g., A composite depends on 3 renders)."""
    deps = []
    for dep_node, _times in node.inputDependencies():
        if dep_node.path() != node.path():
            deps.append(dep_node.path())
    return deps

def _find_fetch_for_cop(cop_path: str):
    """Finds a fetch node in /out that references a given COP network path."""
    out_node = hou.node("/out")
    if not out_node: return None
    
    for node in out_node.children():
        if node.type().name() == "fetch":
            source_parm = node.parm("source")
            if source_parm and source_parm.eval() == cop_path:
                return node
    return None

if __name__ == "__main__":
    # Example execution when run via hython scene_scanner.py logo.v20.hiplc
    if len(sys.argv) > 1:
        hip_file = sys.argv[1]
        hou.hipFile.load(hip_file, suppress_save_prompt=True, ignore_load_warnings=True)
        jobs = discover_render_jobs()
        for j in jobs:
            print(f"[{j['node_type']}] {j['name']} ({j['frames']}) -> Deps: {len(j['dependencies'])}")
