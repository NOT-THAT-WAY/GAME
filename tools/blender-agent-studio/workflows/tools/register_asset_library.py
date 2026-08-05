"""Register this project's native Asset Library in Blender preferences."""
import bpy
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
directory = str(ROOT / "asset_library")
library_name = os.environ.get("BLENDER_ASSET_LIBRARY_NAME", "Blender Agent Studio")
libraries = bpy.context.preferences.filepaths.asset_libraries
library = next((item for item in libraries if Path(item.path).expanduser().resolve() == Path(directory).resolve()), None)
if library is None:
    library = next((item for item in libraries if item.name == library_name), None)
if library is None:
    library = libraries.new(name=library_name, directory=directory)
else:
    library.path = directory
    library.name = library_name
bpy.ops.wm.save_userpref()
print("BLENDER_AGENT_STUDIO_ASSET_LIBRARY_REGISTERED=" + library.path)
