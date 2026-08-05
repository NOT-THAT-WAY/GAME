"""Generic batch runner: executes a repo workflow script inside Blender with UNRECORDED_PARAMS.

Usage:
  Blender --background <blend> --python run_workflow.py -- <script.py> key=value ...
"""
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
script_path = argv[0]
params = {}
for pair in argv[1:]:
    key, _, value = pair.partition("=")
    params[key] = value

with open(script_path, "r", encoding="utf-8") as handle:
    source = handle.read()

globals_dict = {"__name__": "__main__", "__file__": script_path, "UNRECORDED_PARAMS": params}
exec(compile(source, script_path, "exec"), globals_dict)
