"""Read-only presentation of an already authorized native file.edit response.

No filesystem access, subprocesses, requests, independent funcs or save endpoint.
Unknown/error/submission forms are returned unchanged, byte for byte.
Python 3.6 compatible for Rocky Linux 8.
"""

import os
import sys
import xml.etree.ElementTree as ET


MAX_XML_BYTES = 4 * 1024 * 1024
MAX_CONTENT_BYTES = 512 * 1024
FIELD = "ismonaco_preview"
ASSETS = "/manimg/ismonaco-preview-0.1.2"



def transform(data, context):
    # Only native identity is considered. Request parameters cannot grant access.
    if (context.get("PARAM_func") != "file.edit"
            or not context.get("AUTH_USER")
            or context.get("AUTH_LEVEL") not in ("16", "24", "29", "30")
            or len(data) > MAX_XML_BYTES):
        return data
    try:
        text = data.decode("utf-8")
        if "\x00" in text or "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            return data
        root = ET.fromstring(text)
        if (root.tag != "doc" or root.get("func") != "file.edit"
                or root.find(".//error") is not None
                or root.find("ok") is not None
                or root.find("tparams/sok") is not None):
            return data
        metadata = root.findall("metadata")
        contents = root.findall("fdata")
        if (len(metadata) != 1 or metadata[0].get("name") != "file.edit"
                or metadata[0].get("type") != "form" or len(contents) != 1
                or len(contents[0]) != 0 or root.find(FIELD) is not None):
            return data
        form = metadata[0].find("form")
        if form is None or form.find(".//textarea[@name='fdata']") is None:
            return data
        content = contents[0].text or ""
        if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
            return data
        # Phoenix ignores htmldata; use its native frame control. The URL has
        # only a public render nonce, never content, identity or a session token.
        frame_url = ASSETS + "/frame.html?v=" + os.urandom(8).hex()
        field = ET.Element("field", {"name": FIELD, "noname": "yes", "fullwidth": "yes"})
        ET.SubElement(field, "frame", {"name": FIELD, "height": "620px"})
        # Native fields, submit buttons, function, hidden fields and fdata stay intact.
        form.insert(0, field)
        ET.SubElement(root, FIELD).text = frame_url
        # tostring(xml_declaration=...) was added in Python 3.8. The server
        # baseline is 3.6; prepend the fixed declaration without that keyword.
        serialized = ET.tostring(root, encoding="utf-8").replace(b"\r", b"&#13;")
        return b'<?xml version="1.0" encoding="utf-8"?>\n' + serialized
    except Exception:
        # Fail open for presentation only; native access/save behavior is retained.
        return data


def main():
    data = sys.stdin.buffer.read(MAX_XML_BYTES + 1)
    if len(data) > MAX_XML_BYTES:
        # Keep memory bounded and preserve large native responses without parsing.
        sys.stdout.buffer.write(data)
        while True:
            block = sys.stdin.buffer.read(65536)
            if not block:
                break
            sys.stdout.buffer.write(block)
    else:
        sys.stdout.buffer.write(transform(data, os.environ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
