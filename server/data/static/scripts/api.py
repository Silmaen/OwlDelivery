"""
Script for using server API
"""

from datetime import datetime
from pathlib import Path
from sys import stderr

from requests import post as http_post
from requests.auth import HTTPBasicAuth
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor


class Revision:
    def __init__(self):
        self.hash = ""
        self.branch = ""
        self.name = ""
        self.flavor_name = ""
        self.rev_type = ""
        self.date = ""
        self.file = Path()


rev = Revision()
user = ""
cred = ""
destination = ""
verbosity = 0


def pretty_size_print(raw_size):
    """
    Pretty print of sizes with units
    :param raw_size:
    :return:
    """
    for unite in ["B", "KB", "MB", "GB", "TB"]:
        if raw_size < 1024.0:
            break
        raw_size /= 1024.0
    return f"{raw_size:.2f} {unite}"


def create_callback(encoder):
    """
    Create a callback for the given encoder.
    :param encoder: The encoder.
    :return: A monitor call back.
    """

    encoder_len = encoder.len
    if verbosity > 0:
        print(
            f"[{pretty_size_print(0)} of {pretty_size_print(encoder_len)}]                    ",
            flush=True,
            end="\r",
        )

    def callback(monitor):
        """
        The callback function.
        :param monitor: The monitor
        """
        if verbosity > 0:
            print(
                f"[{pretty_size_print(monitor.bytes_read)} of {pretty_size_print(encoder_len)}]                    ",
                flush=True,
                end="\r",
            )

    return callback


def push():
    try:
        basic = HTTPBasicAuth(user, cred)
        post_data = {
            "action": "push",
            "hash": rev.hash,
            "branch": rev.branch,
            "name": rev.name,
            "flavor_name": rev.flavor_name,
            "date": rev.date,
            "rev_type": rev.rev_type,
            "package": (
                rev.file.name,
                open(rev.file, "rb"),
                "application/octet-stream",
            ),
        }
        encoder = MultipartEncoder(fields=post_data)
        if rev.file.stat().st_size < 1:
            monitor = MultipartEncoderMonitor(encoder)
            headers = {"Content-Type": monitor.content_type}
            resp = http_post(
                f"{destination}/api", auth=basic, data=monitor, headers=headers
            )
        else:
            monitor = MultipartEncoderMonitor(
                encoder, callback=create_callback(encoder)
            )
            headers = {"Content-Type": monitor.content_type}
            resp = http_post(
                f"{destination}/upload",
                auth=basic,
                data=monitor,
                headers=headers,
            )
            if verbosity > 0:
                print()

        if resp.status_code == 201:
            print(
                f"WARNING coming from server: {destination}: {resp.status_code}: {resp.reason}",
                file=stderr,
            )
            print(f"response: {resp.content.decode('utf8')}", file=stderr)
            return
        if resp.status_code != 200:
            print(
                f"ERROR connecting to server: {destination}: {resp.status_code}: {resp.reason}, see error.log",
                file=stderr,
            )
            with open("error.log", "ab") as fp:
                fp.write(f"\n---- ERROR: {datetime.now()} ---- \n".encode("utf8"))
                fp.write(resp.content)
            return
    except Exception as err:
        print(
            f"ERROR Exception during server push: {destination}: {err}",
            file=stderr,
        )
    return


def parse_args():
    from argparse import ArgumentParser

    global verbosity, rev, user, cred, destination

    parser = ArgumentParser(description="Revision manager")
    sub_parsers = parser.add_subparsers(
        title="Sub Commands", help="Sub command Help", dest="command", required=True
    )
    push_parser = sub_parsers.add_parser("push")
    push_parser.add_argument(
        "--verbose", "-v", action="count", default=0, help="The verbosity"
    )
    push_parser.add_argument(
        "--type",
        "-t",
        type=str,
        choices=["e", "a", "d"],
        default="e",
        help="The type of package",
    )
    push_parser.add_argument(
        "--hash",
        type=str,
        help="The hash of package",
    )
    push_parser.add_argument(
        "--branch",
        "-b",
        type=str,
        help="The branch of package",
    )
    push_parser.add_argument(
        "--name",
        "-n",
        type=str,
        help="The name of package",
    )
    push_parser.add_argument(
        "--flavor_name",
        type=str,
        help="The flavor_name of package",
    )
    push_parser.add_argument(
        "--date",
        "-d",
        type=str,
        help="The date of package",
    )
    push_parser.add_argument(
        "--file",
        "-f",
        type=str,
        help="The file of package",
    )
    push_parser.add_argument(
        "--user",
        "-u",
        type=str,
        help="The user",
    )
    push_parser.add_argument(
        "--passwd",
        "-p",
        type=str,
        help="The password",
    )
    push_parser.add_argument(
        "--url",
        type=str,
        help="The server destination",
    )

    args = parser.parse_args()

    verbosity = args.verbose
    if args.command == "push":
        rev.rev_type = args.type
        if args.hash:
            rev.hash = args.hash
        else:
            print("ERROR: missing revision hash", file=stderr)
            exit(1)
        rev.branch = "main"
        if args.branch:
            rev.branch = args.branch
        if args.name:
            rev.name = args.name
        else:
            print("ERROR: missing revision name", file=stderr)
            exit(1)
        if args.flavor_name:
            rev.flavor_name = args.flavor_name
        else:
            print("ERROR: missing revision flavor name", file=stderr)
            exit(1)
        if args.date:
            rev.date = args.date
        else:
            print("ERROR: missing revision date", file=stderr)
            exit(1)
        if args.file:
            rev.file = Path(args.file)
        else:
            print("ERROR: missing revision file", file=stderr)
            exit(1)
        user = args.user
        cred = args.passwd
        destination = args.url
        return "push"

    return ""


def main():
    cmd = parse_args()
    if cmd == "push":
        push()


if __name__ == "__main__":
    main()
