from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .backend import (
    APP_NAME,
    detect_ports,
    inspect_image,
    launch_cardwriter,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tech2-cardwriter",
        description="Write Saab and GM Tech 2 PCMCIA card images from Linux.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--list-ports", action="store_true", help="list serial ports and exit")
    parser.add_argument("--inspect", metavar="IMAGE", help="inspect a .bin card image and exit")
    parser.add_argument("--image", metavar="IMAGE", help="pre-select a card image")
    parser.add_argument("--port", metavar="DEVICE", help="pre-select a serial port, e.g. /dev/ttyUSB0")
    parser.add_argument("--launch", action="store_true", help="launch Card Writer without opening the GUI")
    parser.add_argument("--debug", action="store_true", help="keep Wine debug output")
    parser.add_argument("file", nargs="?", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.debug:
        os.environ["TECH2_DEBUG"] = "1"

    if args.list_ports:
        ports = detect_ports()
        if not ports:
            print("No serial ports found. Plug in a USB-to-serial adapter and try again.")
            return 1
        for port in ports:
            access = "ok" if port.accessible else "permission denied"
            print(f"{port.device}\t{port.label}\t{access}")
        return 0

    if args.inspect:
        try:
            image = inspect_image(args.inspect)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"file:      {image.path}")
        print(f"size:      {image.size_mb:g} MB")
        print(f"version:   {image.version_label}")
        print(f"header:    {'ok' if image.magic_ok else 'missing T2 header'}")
        print(f"coverage:  {image.coverage or 'unknown'}")
        for warning in image.warnings:
            print(f"warning:   {warning}")
        return 0 if image.valid else 1

    if args.launch:
        port = args.port
        if not port:
            ports = detect_ports()
            port = ports[0].device if ports else None
        if not port:
            print("error: no serial port found; use --port /dev/ttyUSB0", file=sys.stderr)
            return 1
        try:
            proc, log = launch_cardwriter(port)
        except Exception as exc:  # noqa: BLE001 - CLI should report the real error
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"Card Writer started (pid {proc.pid}).")
        print(f"Log: {log}")
        print("In Card Writer: select COM1, click Start, then choose your .bin image.")
        return 0

    image = args.image or args.file
    from .app import Application

    app = Application(initial_image=image, initial_port=args.port)
    return app.run([sys.argv[0]])
