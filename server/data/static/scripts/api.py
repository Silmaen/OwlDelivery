"""
Script for using server API
"""

import sys
from datetime import datetime
from pathlib import Path
from sys import stderr
from urllib.parse import urlencode

try:
    from requests import post as http_post
    from requests.auth import HTTPBasicAuth
    from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
except ImportError as e:
    print(
        f"ERROR: Missing required Python package: {e}\n"
        f"Install with: pip install requests requests-toolbelt",
        file=stderr,
    )
    sys.exit(2)


class Revision:
    def __init__(self):
        self.hash = ""
        self.branch = ""
        self.name = ""
        self.flavor_name = ""
        self.rev_type = ""
        self.date = ""
        self.file = Path()

    def compact(self):
        import tarfile

        if self.file.is_dir():
            if verbosity > 0:
                print(f"Compacting directory {self.file}... ", end="")
            output_filename = self.file.parent / f"Archive_{self.branch}.tgz"
            with tarfile.open(output_filename, "w:gz") as tar:
                for item in self.file.iterdir():
                    # Ajouter chaque élément à l'archive
                    tar.add(item, arcname=item.relative_to(self.file))
            self.file = output_filename
            if verbosity > 0:
                print("done.")


rev = Revision()
user = ""
cred = ""
destination = ""
verbosity = 0
# Fields and file of a push_screenshot / push_release request.
page_fields = {}
page_file = None


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


def get_log_dir():
    """Get the log directory, creating it if necessary."""
    log_dir = Path(__file__).resolve().parent / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


# Size threshold (100 MB) above which files are sent via /upload (nginx upload module)
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024


def push():
    """
    Push a package or documentation to the server.
    :return: 0 on success, 1 on error.
    """
    try:
        basic = HTTPBasicAuth(user, cred)
        post_data = {
            "action": ["push", "push_doc"][rev.rev_type == "d"],
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
        if rev.file.stat().st_size < LARGE_FILE_THRESHOLD:
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
            # The nginx upload module drops the text fields of the form: they go in the query string too.
            query = urlencode({k: v for k, v in post_data.items() if k != "package"})
            resp = http_post(
                f"{destination}/upload?{query}",
                auth=basic,
                data=monitor,
                headers=headers,
            )
            if verbosity > 0:
                print()

        return check_response(resp)
    except Exception as err:
        print(
            f"ERROR Exception during server push: {destination}: {err}",
            file=stderr,
        )
        return 1


def check_response(resp):
    """
    Report the answer of the server.
    :param resp: The response.
    :return: 0 on success or warning, 1 on error.
    """
    if resp.status_code == 201:
        print(
            f"WARNING coming from server: {destination}: {resp.status_code}: {resp.reason}",
            file=stderr,
        )
        print(f"response: {resp.content.decode('utf8')}", file=stderr)
        return 0
    if resp.status_code != 200:
        log_file = get_log_dir() / "error.log"
        print(
            f"ERROR connecting to server: {destination}: {resp.status_code}: {resp.reason}, see {log_file}",
            file=stderr,
        )
        with open(log_file, "ab") as fp:
            fp.write(f"\n---- ERROR: {datetime.now()} ---- \n".encode())
            fp.write(resp.content)
        return 1
    if verbosity > 0:
        print(resp.content.decode("utf8"))
    return 0


def push_page():
    """
    Push a screenshot or a release note of the presentation page. Always small: sent straight to /api.
    :return: 0 on success, 1 on error.
    """
    try:
        basic = HTTPBasicAuth(user, cred)
        fields = dict(page_fields)
        if page_file is not None:
            fields["package"] = (page_file.name, open(page_file, "rb"), "application/octet-stream")
        encoder = MultipartEncoder(fields=fields)
        headers = {"Content-Type": encoder.content_type}
        resp = http_post(f"{destination}/api", auth=basic, data=encoder, headers=headers)
        return check_response(resp)
    except Exception as err:
        print(
            f"ERROR Exception during server push: {destination}: {err}",
            file=stderr,
        )
        return 1


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

    screenshot_parser = sub_parsers.add_parser(
        "push_screenshot", help="Push a screenshot of the presentation page"
    )
    add_page_arguments(screenshot_parser)
    screenshot_parser.add_argument(
        "--key", "-k", type=str, help="Stable name of the image (hub, raycast...)"
    )
    screenshot_parser.add_argument(
        "--file", "-f", type=str, help="The PNG, JPEG or WebP file"
    )
    screenshot_parser.add_argument("--caption", type=str, help="Visible caption")
    screenshot_parser.add_argument(
        "--alt_text", type=str, help="Description for screen readers"
    )
    screenshot_parser.add_argument(
        "--style_tag",
        type=str,
        choices=["2d", "raycast", "voxel", "isometric", "3d", "hud", "editor"],
        help="Rendering style badge",
    )
    screenshot_parser.add_argument(
        "--in_gallery",
        type=str,
        choices=["true", "false"],
        help="Show the image in the gallery",
    )
    screenshot_parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish a new image right away (default: draft)",
    )

    release_parser = sub_parsers.add_parser(
        "push_release", help="Push the release note of a version"
    )
    add_page_arguments(release_parser)
    release_parser.add_argument(
        "--branch", "-b", type=str, help="The version branch (0.3.0)"
    )
    release_parser.add_argument("--title", type=str, help="Title of the release")
    release_parser.add_argument(
        "--release_date", type=str, help="Release date, YYYY-MM-DD"
    )
    release_parser.add_argument(
        "--highlights", type=str, help="Markdown highlights"
    )
    release_parser.add_argument(
        "--highlights_file", type=str, help="File holding the markdown highlights"
    )
    release_parser.add_argument(
        "--changelog_url", type=str, help="Anchor of the changelog page"
    )

    args = parser.parse_args()

    verbosity = args.verbose
    if args.command in ["push_screenshot", "push_release"]:
        return parse_page_args(args)
    if args.command == "push":
        rev.rev_type = args.type
        if args.branch:
            rev.branch = args.branch
        else:
            print("ERROR: missing branch code", file=stderr)
            sys.exit(1)
        if args.file:
            rev.file = Path(args.file)
        else:
            print("ERROR: missing revision file", file=stderr)
            sys.exit(1)
        destination = args.url
        if destination in ["", None]:
            print("ERROR: missing destination url", file=stderr)
            sys.exit(1)
        if rev.rev_type == "d":  # if documentation
            if not rev.file.is_dir():
                print("ERROR: Documentation data must be a directory", file=stderr)
                sys.exit(1)
            if not (rev.file / "index.html").exists():
                print(
                    "ERROR: Documentation data does not contains index.html file",
                    file=stderr,
                )
                sys.exit(1)
            # do the compression
            rev.compact()
            if not rev.file.is_file():
                print(
                    "ERROR: Documentation content should now be an archive file",
                    file=stderr,
                )
                sys.exit(1)
        else:  # if not documentation
            if not rev.file.is_file():
                print(
                    "ERROR: Package content should now be a file",
                    file=stderr,
                )
                sys.exit(1)
            if args.hash:
                rev.hash = args.hash
            else:
                print("ERROR: missing revision hash", file=stderr)
                sys.exit(1)
            if args.name:
                rev.name = args.name
            else:
                print("ERROR: missing revision name", file=stderr)
                sys.exit(1)
            if args.flavor_name:
                rev.flavor_name = args.flavor_name
            else:
                print("ERROR: missing revision flavor name", file=stderr)
                sys.exit(1)
            if args.date:
                rev.date = args.date
            else:
                print("ERROR: missing revision date", file=stderr)
                sys.exit(1)
        user = args.user
        if user in ["", None]:
            print("ERROR: missing user", file=stderr)
            sys.exit(1)
        cred = args.passwd
        if cred in ["", None]:
            print("ERROR: missing password", file=stderr)
            sys.exit(1)
        return "push"

    return ""


def add_page_arguments(parser):
    """
    Arguments shared by the sub-commands of the presentation page.
    """
    parser.add_argument(
        "--verbose", "-v", action="count", default=0, help="The verbosity"
    )
    parser.add_argument("--user", "-u", type=str, help="The user")
    parser.add_argument("--passwd", "-p", type=str, help="The password")
    parser.add_argument("--url", type=str, help="The server destination")


def parse_page_args(args):
    """
    Check the arguments of push_screenshot / push_release and fill the request fields.
    :return: The command name.
    """
    global user, cred, destination, page_file

    destination = args.url
    user = args.user
    cred = args.passwd
    for value, what in [(destination, "destination url"), (user, "user"), (cred, "password")]:
        if value in ["", None]:
            print(f"ERROR: missing {what}", file=stderr)
            sys.exit(1)
    page_fields["action"] = args.command
    if args.command == "push_screenshot":
        if not args.key:
            print("ERROR: missing image key", file=stderr)
            sys.exit(1)
        if not args.file or not Path(args.file).is_file():
            print("ERROR: missing image file", file=stderr)
            sys.exit(1)
        page_fields["key"] = args.key
        page_file = Path(args.file)
        for name in ["caption", "alt_text", "style_tag", "in_gallery"]:
            if getattr(args, name) is not None:
                page_fields[name] = getattr(args, name)
        if args.publish:
            page_fields["publish"] = "true"
    else:
        if not args.branch:
            print("ERROR: missing branch code", file=stderr)
            sys.exit(1)
        page_fields["branch"] = args.branch
        if args.highlights_file:
            page_fields["highlights"] = Path(args.highlights_file).read_text(encoding="utf8")
        for name in ["title", "release_date", "highlights", "changelog_url"]:
            if getattr(args, name) is not None:
                page_fields[name] = getattr(args, name)
    return args.command


def main():
    cmd = parse_args()
    if cmd == "push":
        sys.exit(push())
    if cmd in ["push_screenshot", "push_release"]:
        sys.exit(push_page())
    sys.exit(1)


if __name__ == "__main__":
    main()
