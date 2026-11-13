"""Summarize native file.edit XML on stdin without printing values or secrets.

Python 3.6 compatible. No files, network, subprocesses or panel changes.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET


MAX_BYTES = 4 * 1024 * 1024
CONTROL_TAGS = {"field", "textarea", "input", "htmldata", "frame", "select", "page"}
ATTRIBUTES = ("name", "type", "editor", "environ", "readonly", "fullwidth", "noname")


def identifier(value):
    if value is None:
        return None
    return value if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:-]{0,79}", value) else "[redacted]"


def attributes(element, names):
    return {key: identifier(element.get(key)) for key in names if element.get(key) is not None}


def summarize(data):
    if len(data) > MAX_BYTES:
        return {"status": "XML_TOO_LARGE"}
    try:
        text = data.decode("utf-8")
        if "\x00" in text or "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            return {"status": "XML_REJECTED"}
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError, ValueError):
        return {"status": "INVALID_XML"}
    if root.tag != "doc":
        return {"status": "UNEXPECTED_ROOT"}
    if root.find(".//error") is not None:
        return {"status": "NATIVE_ERROR", "metadata_present": root.find("metadata") is not None}
    metadata = root.findall("metadata")
    content = root.findall("fdata")
    controls = [node for item in metadata for node in item.iter() if node.tag in CONTROL_TAGS]
    if len(controls) > 128 or len(metadata) > 8:
        return {"status": "METADATA_TOO_LARGE"}
    sok = root.find("tparams/sok")
    return {
        "status": "OK" if metadata else "METADATA_MISSING",
        "function": identifier(root.get("func")),
        "metadata": [attributes(item, ("name", "type", "mgr")) for item in metadata],
        "controls": [dict({"tag": node.tag}, **attributes(node, ATTRIBUTES)) for node in controls],
        "fdata_nodes": len(content),
        "fdata_is_text": len(content) == 1 and len(content[0]) == 0,
        "fdata_within_preview_limit": (len(content) == 1 and len(content[0]) == 0
                                       and len((content[0].text or "").encode("utf-8")) <= 524288),
        "sok_present": sok is not None,
        "sok_nonempty": sok is not None and bool(sok.text),
        "ok_present": root.find("ok") is not None,
        "monaco_data_present": root.find("ismonaco_preview") is not None,
        "monaco_field_present": any(item.find(".//field[@name='ismonaco_preview']") is not None
                                     for item in metadata),
    }


def main():
    report = summarize(sys.stdin.buffer.read(MAX_BYTES + 1))
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["status"] == "OK" else 2


if __name__ == "__main__":
    sys.exit(main())
