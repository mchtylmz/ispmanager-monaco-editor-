#!/usr/bin/env python3
"""Read-only Phase 0 inventory. No panel calls, installs or file writes.

Uses Python's standard library and Python 3.6-compatible syntax for diagnostics
on existing Rocky 8 installations. This is not the plugin backend runtime.
"""

import argparse
import datetime
import json
import os
import platform
import re
import selectors
import signal
import stat
import subprocess
import sys
import time


SCHEMA_VERSION = 1
MAX_FILE_BYTES = 1024 * 1024
MAX_COMMAND_BYTES = 512 * 1024
COMMAND_TIMEOUT = 5
SAFE_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"}

FILE_PATHS = {
    "os_release": ("/etc/os-release", "/usr/lib/os-release"),
    "memory": ("/proc/meminfo",),
    "panel_config": ("/usr/local/mgr5/etc/ispmgr.conf",),
    "selinux": ("/sys/fs/selinux/enforce",),
    "cgroup_controllers": ("/sys/fs/cgroup/cgroup.controllers",),
    "cgroup_mounts": ("/proc/self/mounts",),
    "cgroup_v1_controllers": ("/proc/cgroups",),
}
PANEL_PATHS = {
    "mgrctl": "/usr/local/mgr5/sbin/mgrctl",
    "xml_directory": "/usr/local/mgr5/etc/xml",
}
PACKAGE_COMMANDS = {
    "rpm": (
        "/usr/bin/rpm", "-qa", "--qf",
        "%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\n",
    ),
    "dpkg": (
        "/usr/bin/dpkg-query", "-W",
        "-f=${Package}\t${Version}\t${Architecture}\n",
    ),
}
PACKAGE_NAME = re.compile(
    r"(?:coremanager|ispmanager(?:-6|-lite|-lite-common|-business|-plugins)?|"
    r"systemd|python3(?:[.][0-9]+)?|php(?:[0-9.]+)?(?:-cli|-fpm)?|"
    r"isp-php[0-9]+(?:-cli|-fpm)?)\Z"
)
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+:~%\-]{0,127}\Z")
REQUIRED_CHECKS = (
    "panel_release_and_edition",
    "file_action_xml",
    "session_and_csrf",
    "native_file_permissions",
    "safe_content_transport",
    "save_conflict_semantics",
    "language_server_provider_review",
    "language_server_sandbox",
)


class ProbeError(Exception):
    """A fixed error code; never expose a command's raw stderr or file data."""


def read_regular_file(path, limit=MAX_FILE_BYTES):
    """Do not follow symlinks or block on special files, even when run as root."""
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        raise ProbeError("not_found") from None
    except OSError:
        raise ProbeError("unreadable_or_symlink") from None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ProbeError("not_regular_file")
        data = bytearray()
        while len(data) <= limit:
            chunk = os.read(descriptor, min(8192, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) > limit:
            raise ProbeError("output_limit")
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            raise ProbeError("invalid_utf8") from None
    except OSError:
        raise ProbeError("unreadable") from None
    finally:
        os.close(descriptor)


def run_bounded(argv, timeout=COMMAND_TIMEOUT, limit=MAX_COMMAND_BYTES):
    """Run a fixed inventory command without shell, inherited env, or stdin."""
    try:
        process = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=SAFE_ENV, cwd="/",
            start_new_session=True,
        )
    except OSError:
        raise ProbeError("command_unavailable") from None
    selector = selectors.DefaultSelector()
    deadline = time.monotonic() + timeout
    output = bytearray()
    exited = False
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProbeError("timeout")
            for key, _ in selector.select(remaining):
                chunk = os.read(key.fd, min(8192, limit + 1 - len(output)))
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                output.extend(chunk)
                if len(output) > limit:
                    raise ProbeError("output_limit")
        try:
            returncode = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise ProbeError("timeout") from None
        exited = True
        if returncode != 0:
            raise ProbeError("command_failed")
        try:
            return output.decode("utf-8")
        except UnicodeDecodeError:
            raise ProbeError("invalid_utf8") from None
    finally:
        selector.close()
        # Also stop children which may still hold stdout open on error/timeout.
        if not exited:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()
        process.stdout.close()


def parse_os_release(text):
    """Parse only two data fields. Never source shell syntax from os-release."""
    result = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or key not in ("ID", "VERSION_ID"):
            continue
        if key in result:
            raise ProbeError("ambiguous_os_release")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.\-]{0,63}", value):
            raise ProbeError("invalid_os_release")
        result[key] = value
    if set(result) != {"ID", "VERSION_ID"}:
        raise ProbeError("incomplete_os_release")
    return {"id": result["ID"], "version_id": result["VERSION_ID"]}


def parse_packages(text):
    """Return allowlisted package metadata; never include other command output."""
    packages = []
    for line in text.splitlines():
        fields = line.split("\t")
        if not fields or not PACKAGE_NAME.fullmatch(fields[0]):
            continue
        if len(fields) != 3 or not all(TOKEN.fullmatch(value) for value in fields):
            raise ProbeError("invalid_package_metadata")
        packages.append(dict(zip(("name", "package_version", "architecture"), fields)))
        if len(packages) > 128:
            raise ProbeError("package_count_limit")
    return sorted(packages, key=lambda item: (item["name"], item["architecture"]))


def parse_file_limit(text):
    values = []
    for line in text.splitlines():
        fields = line.split("#", 1)[0].split()
        if not fields or fields[0] != "FileMaxEditSize":
            continue
        if len(fields) != 2 or not re.fullmatch(r"[0-9]{1,9}", fields[1]):
            raise ProbeError("invalid_file_limit")
        value = int(fields[1])
        if value < 1:
            raise ProbeError("invalid_file_limit")
        values.append(value)
    if len(values) > 1:
        raise ProbeError("ambiguous_file_limit")
    return {
        "configured_kib": values[0] if values else None,
        "effective_value_verified": False,
    }


def parse_memory(text):
    match = re.search(r"^MemTotal:\s+([0-9]{1,15}) kB$", text, re.MULTILINE)
    if not match or int(match.group(1)) < 1:
        raise ProbeError("invalid_memory_metadata")
    return int(match.group(1))


def parse_selinux(text):
    value = text.strip()
    if value not in ("0", "1"):
        raise ProbeError("invalid_selinux_metadata")
    return "enforcing" if value == "1" else "permissive"


def parse_controllers(text):
    allowed = {"cpu", "cpuset", "io", "memory", "pids", "hugetlb", "rdma", "misc", "dmem"}
    values = text.split()
    if any(value not in allowed for value in values):
        raise ProbeError("unknown_cgroup_controller")
    return {"visible_v2_controllers": sorted(set(values)), "isolation_verified": False}


def parse_cgroup_mounts(text):
    """Keep filesystem types/controller options, never other mount paths/data."""
    v1 = False
    v2 = False
    v1_options = set()
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 3 or fields[2] not in ("cgroup", "cgroup2"):
            continue
        if len(fields) != 6:
            raise ProbeError("invalid_cgroup_mount_metadata")
        if fields[2] == "cgroup":
            v1 = True
            v1_options.update(fields[3].split(","))
        else:
            v2 = True
    if not v1 and not v2:
        raise ProbeError("cgroup_mount_not_observed")
    return v1, v2, v1_options


def parse_active_v1_controllers(text):
    active = set()
    seen = set()
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        if (len(fields) != 4
                or not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", fields[0])
                or not all(re.fullmatch(r"[0-9]{1,12}", value) for value in fields[1:3])
                or fields[3] not in ("0", "1")
                or fields[0] in seen):
            raise ProbeError("invalid_v1_controller_metadata")
        seen.add(fields[0])
        if fields[3] == "1" and int(fields[1]) > 0:
            active.add(fields[0])
    return active


def collect_cgroups(host):
    v1, v2, v1_options = parse_cgroup_mounts(host.read("cgroup_mounts"))
    mounted_v1 = set()
    visible_v2 = []
    if v1:
        active = parse_active_v1_controllers(host.read("cgroup_v1_controllers"))
        mounted_v1 = active.intersection(v1_options)
    if v2:
        visible_v2 = parse_controllers(host.read("cgroup_controllers"))["visible_v2_controllers"]
    return {
        "mode": "hybrid" if v1 and v2 else ("v1" if v1 else "v2"),
        "mounted_v1_controllers": sorted(mounted_v1),
        "visible_v2_controllers": visible_v2,
        "isolation_verified": False,
    }


class LinuxHost:
    def system(self):
        return platform.system()

    def machine(self):
        return platform.machine()

    def effective_uid(self):
        return os.geteuid()

    def cpu_count(self):
        return os.cpu_count()

    def read(self, key):
        # os-release is often a symlink. Read the two known standard locations
        # separately; never resolve a link to an arbitrary target.
        last_error = ProbeError("not_found")
        for path in FILE_PATHS[key]:
            try:
                return read_regular_file(path)
            except ProbeError as error:
                last_error = error
        raise last_error

    def panel_path_present(self, key):
        try:
            metadata = os.stat(PANEL_PATHS[key], follow_symlinks=False)
        except FileNotFoundError:
            return False
        except OSError:
            raise ProbeError("unreadable") from None
        if key == "mgrctl":
            return stat.S_ISREG(metadata.st_mode) and bool(metadata.st_mode & 0o111)
        return stat.S_ISDIR(metadata.st_mode)

    def packages(self):
        result = None
        for kind in ("rpm", "dpkg"):
            argv = PACKAGE_COMMANDS[kind]
            try:
                metadata = os.stat(argv[0])
            except FileNotFoundError:
                continue
            except OSError:
                raise ProbeError("unreadable_package_manager") from None
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0
                    or metadata.st_mode & 0o022 or not metadata.st_mode & 0o111):
                raise ProbeError("untrusted_package_manager")
            items = parse_packages(run_bounded(argv))
            candidate = {"manager": kind, "items": items}
            # An RPM utility can coexist with a DEB-owned installation. Prefer
            # the database containing panel metadata over an empty/foreign DB.
            if any(item["name"].startswith("ispmanager") for item in items):
                return candidate
            if result is None:
                result = candidate
        if result is not None:
            return result
        raise ProbeError("package_manager_not_found")


def probe(operation):
    try:
        return {"status": "observed", "value": operation()}
    except ProbeError as error:
        return {"status": "unknown", "reason": str(error)}
    except OSError:
        return {"status": "unknown", "reason": "unavailable"}


def collect_inventory(host):
    checks = {name: "not_verified" for name in REQUIRED_CHECKS}
    report = {
        "schema_version": SCHEMA_VERSION,
        "report_kind": "environment_inventory",
        "collected_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "phase0_complete": False,
        "integration_checks": checks,
        "features": {"panel_integration": False, "file_write": False, "lsp": False},
        "collection_status": "unsupported_platform",
        "facts": {},
    }
    if host.system() != "Linux":
        return report
    facts = report["facts"]
    machine = host.machine()
    facts["architecture"] = machine if TOKEN.fullmatch(machine) else "unknown"
    facts["running_as_root"] = host.effective_uid() == 0
    facts["collector_python"] = ".".join(str(part) for part in sys.version_info[:3])
    facts["logical_cpu_count"] = host.cpu_count()
    facts["os"] = probe(lambda: parse_os_release(host.read("os_release")))
    facts["packages"] = probe(host.packages)
    facts["memory_total_kib"] = probe(lambda: parse_memory(host.read("memory")))
    facts["panel_paths"] = {
        key: probe(lambda key=key: host.panel_path_present(key)) for key in PANEL_PATHS
    }
    facts["file_edit_limit"] = probe(lambda: parse_file_limit(host.read("panel_config")))
    facts["selinux"] = probe(lambda: parse_selinux(host.read("selinux")))
    facts["cgroups"] = probe(lambda: collect_cgroups(host))
    # A complete inventory still cannot verify a browser session, save safety,
    # sandbox enforcement, panel edition, or plugin compatibility.
    required = (facts["os"], facts["packages"], facts["memory_total_kib"])
    report["collection_status"] = (
        "collected" if all(item["status"] == "observed" for item in required) else "partial"
    )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only ISPmanager environment inventory. JSON to stdout only."
    )
    parser.parse_args(argv)
    report = collect_inventory(LinuxHost())
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if report["collection_status"] == "collected" else 2


if __name__ == "__main__":
    sys.exit(main())
