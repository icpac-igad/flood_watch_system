"""
This script generates a MapCache XML configuration file from a structured JSON input.
It automates the creation of various MapCache elements such as metadata, caches,
grids, image formats, data sources, tilesets, error handling, and services,
ensuring a well-formed XML output.
"""

import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys, os
from datetime import date


def _resolve_dynamic_default(dim_data):
    """Use today's date as default for time dimensions so MapCache never uses a stale date."""
    if dim_data.get("name") == "time":
        return date.today().isoformat()
    return dim_data["default"]
from lxml import etree  # Used specifically for robust XML well-formedness checking


def prettify_xml(elem):
    """
    Returns a pretty-printed XML string for the given ElementTree element.
    This function enhances readability of the generated XML by adding indentation.

    Args:
        elem (xml.etree.ElementTree.Element): The root element of the XML tree.

    Returns:
        str: A string containing the pretty-printed XML.
    """
    # Convert the ElementTree element to a raw XML string
    rough_string = ET.tostring(elem, "utf-8")
    # Parse the raw string using minidom for pretty printing
    reparsed = minidom.parseString(rough_string)
    # Return the pretty-printed XML with a 2-space indent
    return reparsed.toprettyxml(indent="  ")


def create_element(parent, tag, text=None, attrib=None):
    """
    Helper function to create a new XML sub-element and append it to a parent element.
    It optionally sets the element's text content and attributes.

    Args:
        parent (xml.etree.ElementTree.Element): The parent element to which the new element will be added.
        tag (str): The XML tag name for the new element (e.g., "cache", "source").
        text (str, optional): The text content of the element. Defaults to None.
        attrib (dict, optional): A dictionary of attributes for the element (e.g., {"name": "mycache"}).
                                 Defaults to None.

    Returns:
        xml.etree.ElementTree.Element: The newly created XML element.
    """
    # Create the sub-element with provided tag and attributes
    element = ET.SubElement(parent, tag, attrib=attrib or {})
    if text is not None:
        element.text = str(text)  # Ensure text is converted to string
    return element


def check_xml_well_formedness(xml_file_path):
    """
    Checks if an XML file is well-formed using lxml. This function
    only verifies the XML's syntax and structure, not against any specific schema (DTD/XSD).

    Args:
        xml_file_path (str): Path to the XML file to check.

    Returns:
        bool: True if the XML is well-formed, False otherwise. Error messages are printed to stderr.
    """
    try:
        etree.parse(xml_file_path)
        print(f"XML file '{xml_file_path}' is well-formed.")
        return True
    except FileNotFoundError:
        print(
            f"Error: XML file '{xml_file_path}' not found for well-formedness check.",
            file=sys.stderr,
        )
        return False
    except etree.XMLSyntaxError as e:
        print(
            f"Error: XML file '{xml_file_path}' has syntax errors and is not well-formed.",
            file=sys.stderr,
        )
        print(f"Details: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(
            f"An unexpected error occurred during XML well-formedness check: {e}",
            file=sys.stderr,
        )
        return False


def generate_mapcache_xml(
    json_config_path, output_xml_path="mapcache.xml", check_xml=True
):
    """
    Generates a MapCache XML configuration file from a JSON configuration file.

    Args:
        json_config_path (str): Path to the input JSON configuration file.
        output_xml_path (str): Path where the generated XML file will be saved.
        check_xml (bool): If True, a basic XML well-formedness
                                               check is performed after generation.
    """
    # --- Load JSON Configuration ---
    try:
        with open(json_config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(
            f"Error: JSON config file not found at '{json_config_path}'",
            file=sys.stderr,
        )
        return
    except json.JSONDecodeError:
        print(
            f"Error: Could not decode JSON from '{json_config_path}'. Check for syntax errors.",
            file=sys.stderr,
        )
        return

    # Extract global URL definitions for later reference in sources
    global_urls = config.get("global_url_definitions", {})

    # Create the root <mapcache> element, which is the top-level tag for MapCache configuration
    mapcache_root = ET.Element("mapcache")

    # Process mapcache metadata
    # Adds descriptive metadata for the MapCache service.
    if "metadata" in config:
        metadata_elem = create_element(mapcache_root, "metadata")
        for key, value in config["metadata"].items():
            # Dynamically creates child elements for each metadata key-value pair.
            create_element(metadata_elem, key, os.path.expandvars(value))

    # --- Process Global Options ---
    if "global_options" in config:
        for key, value in config["global_options"].items():
            create_element(mapcache_root, key, os.path.expandvars(value))

    # --- Process Image Formats ---
    # Defines image output formats available for tilesets.
    if "image_formats" in config:
        for img_format_data in config["image_formats"]:
            if (
                "name" in img_format_data
                and "type" in img_format_data
                and "details" in img_format_data
            ):
                # Create the <format> XML tag
                image_elem = create_element(
                    mapcache_root,
                    "format",
                    attrib={
                        "name": img_format_data["name"],
                        "type": img_format_data["type"],
                    },
                )
                # Add tile format detail tags directly under <format>
                for key, value in img_format_data["details"].items():
                    create_element(image_elem, key, value)
            else:
                print(
                    f"Warning: Invalid image_format entry found: {img_format_data}. Skipping.",
                    file=sys.stderr,
                )

    # --- Process Caches ---
    # Defines different caching mechanisms used by tilesets.
    if "caches" in config:
        for cache_data in config["caches"]:
            if cache_data.get("type") != "disk":
                print(
                    f"Warning: Cache '{cache_data.get('name')}' is not of type 'disk'. Forcing to 'disk'.",
                    file=sys.stderr,
                )
                cache_data["type"] = "disk"

            # Create the <cache> element with its name and type attributes.
            cache_attribs = {}
            for key, value in cache_data.items():
                if key != "options":
                    cache_attribs[key] = value
            cache_elem = create_element(mapcache_root, "cache", attrib=cache_attribs)

            # Add cache child elements.
            if "options" in cache_data:
                for key, value in cache_data["options"].items():
                    if value is None:
                        create_element(cache_elem, key)
                    else:
                        create_element(cache_elem, key, os.path.expandvars(value))

    # --- Process Locker Directive ---
    #  location to put lockfiles (to block other clients while a metatile is being rendered.
    if "locker" in config:
        locker_elem = create_element(
            mapcache_root, "locker", attrib={"type": config["locker"]["type"]}
        )
        for key, value in config["locker"].items():
            if key != "type":
                if not isinstance(value, int) and not isinstance(value, float):
                    value = os.path.expandvars(value)
                create_element(locker_elem, key, value)

    # --- Process Connection Pool ---
    #  Parameters for fine tuning connection_pool component, used for connections to caches
    # - max_connections: maximum number of open connections at the same time
    #   (default: 1024)
    # - time_to_live_us: maximum amount of time in microseconds an unused
    #   connection is valid (default 60s)
    if "connection_pool" in config:
        locker_elem = create_element(mapcache_root, "connection_pool")
        for key, value in config["connection_pool"].items():
            create_element(locker_elem, key, value)

    # Add custom <grids>
    if "grids" in config:
        for grid_data in config["grids"]:
            grid_elem = create_element(
                mapcache_root,
                "grid",
                attrib={
                    k: v
                    for k, v in grid_data.items()
                    if k not in ["resolutions", "srs"]
                },
            )

            if "srs" in grid_data:
                create_element(grid_elem, "srs", grid_data["srs"])

            if "extent" in grid_data:
                create_element(grid_elem, "extent", grid_data["extent"])
            if "resolutions" in grid_data:
                resolutions_elem = create_element(grid_elem, "resolutions")
                resolutions_elem.text = " ".join(map(str, grid_data["resolutions"]))
            if "units" in grid_data:
                create_element(grid_elem, "units", grid_data["units"])
            if "size" in grid_data:
                create_element(grid_elem, "size", grid_data["size"])

    # --- Process Sources ---
    # Defines backend data sources (e.g., WMS, WMTS services) from which MapCache fetches data.
    if "sources" in config:
        for source_data in config["sources"]:
            source_elem = create_element(
                mapcache_root,
                "source",
                attrib={"name": source_data["name"], "type": source_data["type"]},
            )

            source_url = None
            # Determine the source URL, either directly provided or referenced from global_url_definitions.
            if "url_ref" in source_data:
                url_key = source_data["url_ref"]
                if url_key in global_urls:
                    source_url = global_urls[url_key]
                else:
                    print(
                        f"Warning: url_ref '{url_key}' not found in global_url_definitions for source '{source_data['name']}'. Skipping this source.",
                        file=sys.stderr,
                    )
                    continue
            elif "url" in source_data:
                source_url = source_data["url"]
            else:
                print(
                    f"Warning: No 'url' or 'url_ref' specified for source '{source_data['name']}'. Skipping this source.",
                    file=sys.stderr,
                )
                continue

            # Configure WMS GetMap request parameters.
            getmap_elem = create_element(source_elem, "getmap")
            params_elem = create_element(getmap_elem, "params")
            create_element(
                params_elem, "FORMAT", source_data.get("format", "image/png")
            )
            create_element(params_elem, "LAYERS", source_data["layers"])
            create_element(
                params_elem, "TRANSPARENT", source_data.get("transparent", True)
            )
            if "additional_params" in source_data:
                # Add any other custom WMS parameters.
                for key, value in source_data["additional_params"].items():
                    create_element(params_elem, key, value)

            # Configure HTTP connection settings for the source.
            http_elem = create_element(source_elem, "http")
            create_element(http_elem, "url", os.path.expandvars(source_url))

            # Set connection and request timeouts for the backend service.
            connection_timeout_value = source_data.get("connection_timeout", 120)
            create_element(http_elem, "connection_timeout", connection_timeout_value)

            timeout_value = source_data.get("timeout", 600)
            create_element(http_elem, "timeout", timeout_value)

    # --- Process Tilesets ---
    # Defines individual map layers that can be served, linking sources, caches, and grids.
    if "tilesets" in config:
        for tileset_data in config["tilesets"]:
            tileset_elem = create_element(
                mapcache_root, "tileset", attrib={"name": tileset_data["name"]}
            )
            create_element(tileset_elem, "source", tileset_data["source"])

            if "format_ref" not in tileset_data:
                print(
                    f"Warning: tileset image format for {tileset_data['name']} is not defined. Defaulting to {config['image_formats'][0]['name']}"
                )
                create_element(
                    tileset_elem, "format", config["image_formats"][0]["name"]
                )
            else:
                create_element(tileset_elem, "format", tileset_data["format_ref"])

            # Add shared tileset attributes (per-tileset values override shared defaults)
            if "tileset_attrs" in config:
                for key in config["tileset_attrs"].keys():
                    if key == "grids":
                        for grid_name, grid_props in config["tileset_attrs"][
                            "grids"
                        ].items():
                            create_element(
                                tileset_elem,
                                "grid",
                                grid_name,
                                attrib={
                                    k: os.path.expandvars(v)
                                    for k, v in grid_props.items()
                                },
                            )
                    elif key != "dimensions":
                        # Per-tileset value wins over shared default
                        value = tileset_data.get(key, config["tileset_attrs"][key])
                        create_element(
                            tileset_elem,
                            key,
                            (
                                value
                                if isinstance(value, int)
                                else os.path.expandvars(str(value))
                            ),
                        )

            # Add <dimensions> if specified, allowing for dynamic tile requests (e.g., time, scenario).
            # Tilesets with "no_dimensions": true skip all dimensions (useful for static layers).
            # Tilesets with "own_dimensions_only": true use only their own dimensions, not shared ones.
            if not tileset_data.get("no_dimensions", False) and (
                "dimensions" in tileset_data or "dimensions" in config["tileset_attrs"]
            ):
                tileset_dims = list(tileset_data.get("dimensions", []))
                if not tileset_data.get("own_dimensions_only", False):
                    tileset_dims.extend(config["tileset_attrs"].get("dimensions", []))
                dimensions_elem = create_element(tileset_elem, "dimensions")
                for dim_data in tileset_dims:
                    dimension_attribs = {
                        "name": dim_data["name"],
                        "type": dim_data["type"],
                        "default": _resolve_dynamic_default(dim_data),
                    }

                    dimension_elem = create_element(
                        dimensions_elem, "dimension", attrib=dimension_attribs
                    )

                    # Handle specific dimension types and their child elements.
                    if dim_data["type"] == "values" and "values" in dim_data:
                        # For 'values' type, list all allowed discrete values.
                        for value in dim_data["values"]:
                            create_element(dimension_elem, "value", value)
                    elif dim_data["type"] == "regex" and "regex" in dim_data:
                        # For 'regex' type, provide a regular expression for validation.
                        create_element(dimension_elem, "regex", dim_data["regex"])

            if "metadata" in tileset_data:
                tileset_metadata_elem = create_element(tileset_elem, "metadata")
                for key, value in tileset_data["metadata"].items():
                    create_element(tileset_metadata_elem, key, value)

    # --- Process Services ---
    # Enables and configures the OGC services MapCache will expose (e.g., WMS, WMTS, TMS).
    for service_data in config.get("services", []):
        create_element(mapcache_root, "service", attrib=service_data)

    # --- Write XML to File ---
    # Convert the ElementTree object to a pretty-printed XML string and save it.
    pretty_xml_string = prettify_xml(mapcache_root)
    try:
        with open(output_xml_path, "w") as f:
            f.write(pretty_xml_string)
        print(
            f"MapCache XML configuration successfully generated at '{output_xml_path}'"
        )
    except IOError:
        print(
            f"Error: Could not write to output file '{output_xml_path}'",
            file=sys.stderr,
        )
        return

    # --- XML Well-formedness Check ---
    # Perform a final check on the generated XML file for syntax validity.
    if check_xml:
        print(f"Performing basic XML well-formedness check on '{output_xml_path}'...")
        check_xml_well_formedness(output_xml_path)
        print(f"xml formart check for {output_xml_path} passed")
    else:
        print("Skipping XML well-formedness check (disabled).")


if __name__ == "__main__":
    # This block executes when the script is run directly from the command line.

    # Check for minimum required command-line arguments.
    if len(sys.argv) < 2:
        print(
            "Usage: python generate_mapcache_config.py <input_json_file> [output_xml_file] [check_xml (true/false)]"
        )
        print(
            "Example: python generate_mapcache_config.py config.json mapcache.xml true"
        )
        sys.exit(1)  # Exit with an error code if arguments are insufficient.

    # Parse command-line arguments.
    input_json = sys.argv[1]  # First argument is the path to the input JSON file.
    output_xml = (
        sys.argv[2] if len(sys.argv) > 2 else "mapcache.xml"
    )  # Second argument (optional) is output XML path.
    # Third argument (optional) determines whether to perform XML well-formedness check.
    perform_check_str = sys.argv[3].lower() if len(sys.argv) > 3 else "true"
    perform_check = perform_check_str == "true"  # Convert string to boolean.

    # Call the main function to generate the MapCache XML.
    generate_mapcache_xml(input_json, output_xml, perform_check)
