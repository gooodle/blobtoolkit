#!/usr/bin/env python3

# pylint: disable=no-member, too-many-branches, too-many-statements, too-many-locals, W0603, W0703

"""
Host a collection of BlobDirs.

Usage:
    blobtools host [--port INT]  [--api-port INT]
                   [--hostname STRING] DIRECTORY

Arguments:
    DIRECTORY             Directory containing one or more BlobDirs.

Options:
    --port INT            HTTP port number. [Default: 8080]
    --api-port INT        API port number. [Default: 8000]
    --hostname STRING     Hostname used to connect to API. [Default: localhost]
"""

import os
import platform
import shlex
import signal
import socket
import sys
import time
from pathlib import Path
from shutil import which
from subprocess import PIPE
from subprocess import Popen

import psutil
from docopt import docopt

from .version import __version__

PIDS = []


def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    """Kill all child processes."""
    try:
        parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for process in children:
        process.send_signal(sig)
    parent.send_signal(sig)


def test_port(port, service):
    """Exit if port is already in use."""
    port = int(port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as skt:
        try:
            skt.bind(("", port))
        except OSError:
            if service == "test":
                return False
            print("ERROR: Port %d already in use, unable to host %s." % (port, service))
            print(
                "       Use: `lsof -nP -iTCP:%d | grep LISTEN` to find the associated process."
                % port
            )
            print(
                "       It may take ~30s for this port to become available when restarting %s."
                % service
            )
            sys.exit(1)
    return True


def find_binary(tool):
    """Find a binary executable for the blobtoolkit viewer or API."""
    script_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    system = platform.system()
    # arch, _ = platform.architecture()
    default_binaries = {"api": "blobtoolkit-api", "viewer": "blobtoolkit-viewer"}
    if system == "Linux":
        binaries = {
            "api": "blobtoolkit-api-linux",
            "viewer": "blobtoolkit-viewer-linux",
        }
    if system == "Windows":
        binaries = {
            "api": "blobtoolkit-api-win.exe",
            "viewer": "blobtoolkit-viewer-win.exe",
        }
        default_binaries = {
            "api": "blobtoolkit-api.exe",
            "viewer": "blobtoolkit-viewer.exe",
        }
    if system == "Darwin":
        binaries = {
            "api": "blobtoolkit-api-macos",
            "viewer": "blobtoolkit-viewer-macos",
        }
    if which(default_binaries[tool]) is not None:
        return default_binaries[tool]
    if which(binaries[tool]) is not None:
        return default_binaries[tool]
    executable = binaries[tool]
    executable_path = os.path.join(script_dir, "bin", executable)
    if os.path.isfile(executable_path):
        return executable_path
    else:
        print(
            "ERROR: %s executable was not found. Please add %s to your PATH."
            % (default_binaries[tool], default_binaries[tool])
        )
        sys.exit(1)


def start_api(port, api_port, hostname, directory):
    """Start BlobToolKit API."""
    cmd = find_binary("api")
    # cmd = "blobtoolkit-api"
    origins = "http://localhost:%d http://localhost null" % int(port)
    if hostname != "localhost":
        origins += " http://%s:%d http://%s" % (hostname, int(port), hostname)
    process = Popen(
        shlex.split(cmd),
        stdout=PIPE,
        stderr=PIPE,
        encoding="ascii",
        env=dict(
            os.environ,
            BTK_API_PORT=api_port,
            BTK_FILE_PATH=directory,
            BTK_ORIGINS=origins,
        ),
    )
    return process


def start_viewer(port, api_port, hostname):
    """Start BlobToolKit viewer."""
    cmd = find_binary("viewer")
    # cmd = "blobtoolkit-viewer"
    api_url = "http://%s:%d/api/v1" % (hostname, int(api_port))
    process = Popen(
        shlex.split(cmd),
        stdout=PIPE,
        stderr=PIPE,
        encoding="ascii",
        env=dict(
            os.environ,
            BTK_HOST=hostname,
            BTK_CLIENT_PORT=port,
            BTK_API_PORT=api_port,
            BTK_API_URL=api_url,
        ),
    )
    return process


def main(args):
    """Entrypoint for blobtools host."""
    global PIDS
    path = Path(args["DIRECTORY"])
    if not path.exists():
        print("ERROR: Directory '%s' does not exist" % args["DIRECTORY"])
        sys.exit(1)
    if (path / "meta.json").exists():
        print("WARNING: Directory '%s' appears to be a BlobDir." % args["DIRECTORY"])
        print("         Hosting the parent directory instead.")
        path = path.resolve().parent
    test_port(args["--api-port"], "BlobtoolKit API")
    test_port(args["--port"], "BlobtoolKit viewer")
    api = start_api(
        args["--port"],
        args["--api-port"],
        args["--hostname"],
        path.absolute(),
    )
    PIDS.append(api.pid)
    print(
        "Starting BlobToolKit API on port %d (pid: %d)"
        % (int(args["--api-port"]), api.pid)
    )
    time.sleep(2)
    viewer = start_viewer(args["--port"], args["--api-port"], args["--hostname"])
    PIDS.append(viewer.pid)
    print(
        "Starting BlobToolKit viewer on port %d (pid: %d)"
        % (int(args["--port"]), viewer.pid)
    )
    time.sleep(2)
    ready = False
    url = "http://%s:%d" % (args["--hostname"], int(args["--port"]))
    while True:
        time.sleep(1)
        if api.poll() is not None:
            for line in api.stdout.readlines():
                print(line.strip())
            for line in api.stderr.readlines():
                print(line.strip())
            if viewer.poll() is not None:
                for line in viewer.stdout.readlines():
                    print(line.strip())
                for line in viewer.stderr.readlines():
                    print(line.strip())
                try:
                    os.kill(viewer.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            break
        if viewer.poll() is not None:
            for line in viewer.stdout.readlines():
                print(line.strip())
            for line in viewer.stderr.readlines():
                print(line.strip())
            try:
                os.kill(api.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            break
        if not ready:
            print("Visit %s to use the interactive BlobToolKit Viewer." % url)
            ready = True
        time.sleep(1)


def cli():
    """Entry point."""
    if len(sys.argv) == sys.argv.index(__name__.split(".")[-1]) + 1:
        args = docopt(__doc__, argv=[])
    else:
        args = docopt(__doc__, version=__version__)
    try:
        main(args)
    except KeyboardInterrupt:
        pass
    finally:
        for pid in PIDS:
            kill_child_processes(pid, signal.SIGTERM)


if __name__ == "__main__":
    cli()