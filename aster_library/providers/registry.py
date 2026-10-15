"""Import optional providers so they register with the build orchestrator."""
import importlib

for _name in ("medlineplus", "openfda_labels", "openstax", "legacy"):
    try:
        importlib.import_module(f"aster_library.providers.{_name}")
    except ModuleNotFoundError as exc:
        if exc.name != f"aster_library.providers.{_name}":
            raise
