"""YAML in and out. ruamel.yaml is imported lazily so fast paths never pay for it."""

from io import StringIO

from didact.core.output import JSON


def dump_yaml(data: JSON) -> str:
    """Serialize plain data (dicts, lists, scalars) as block-style YAML 1.2."""
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe", pure=True)
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    # Keep insertion order (ruamel sorts keys by default); its stubs mistype this attribute.
    yaml.sort_base_mapping_type_on_output = False  # type: ignore[assignment]
    buffer = StringIO()
    yaml.dump(data, buffer)
    return buffer.getvalue()
