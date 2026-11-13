"""Phase 0 lab handler: fixed XML only, no files/API/network/child processes.

This root-only diagnostic is not the editor or a production backend runtime.
Compatible with the observed Python 3.6 syntax/runtime API surface.
"""

import os
import sys
import xml.etree.ElementTree as ET


FUNCTION = "ismonaco.phase0"


def response(environment):
    document = ET.Element("doc", {"lang": "en", "func": FUNCTION})
    # A hidden menu alone is not authorization. Trust only the panel's native
    # AUTH_* context, never PARAM_AUTH_*, PARAM_user, su, headers or request XML.
    if (environment.get("PARAM_func") != FUNCTION
            or environment.get("AUTH_USER") != "root"
            or environment.get("AUTH_LEVEL") != "30"):
        error = ET.SubElement(document, "error", {"type": "access", "code": "1"})
        ET.SubElement(error, "msg").text = "Phase 0 diagnostics require the native root context."
        return document

    metadata = ET.SubElement(document, "metadata", {"name": FUNCTION, "type": "form"})
    form = ET.SubElement(metadata, "form", {"nosubmit": "yes", "nocancel": "yes"})
    messages = ET.SubElement(document, "messages")
    ET.SubElement(messages, "msg", {"name": "title"}).text = "Monaco Phase 0 diagnostics"
    rows = (
        ("context", "Native panel context", "root / AUTH_LEVEL 30"),
        ("mode", "Mode", "Lab diagnostics only"),
        ("file_read", "Site file access", "Disabled"),
        ("file_write", "File saving", "Disabled"),
        ("lsp", "Language server", "Disabled"),
        ("session", "Session and CSRF transport", "Not verified"),
        ("sandbox", "Sandbox enforcement", "Not verified"),
    )
    for name, label, value in rows:
        field = ET.SubElement(form, "field", {"name": name, "fullwidth": "yes"})
        ET.SubElement(field, "textdata", {"name": name + "_value", "type": "msg"})
        ET.SubElement(messages, "msg", {"name": name}).text = label
        ET.SubElement(messages, "msg", {"name": name + "_value"}).text = value
    return document


def main():
    # No STDIN parsing: neither XML entities nor file contents are accepted.
    document = response(os.environ)
    sys.stdout.buffer.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    sys.stdout.buffer.write(ET.tostring(document, encoding="utf-8"))
    sys.stdout.buffer.write(b"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
