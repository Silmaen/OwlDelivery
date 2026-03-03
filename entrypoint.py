#!/usr/bin/env python3
"""
Main entry point for the docker image
"""
import os
import shutil
from pathlib import Path
from sys import stderr

server_path = Path("/app/server")
server_config = server_path / "config"
server_data = Path("/app/data")
packages_dir = server_data / "packages"
documentation_dir = server_data / "documentation"
server_data_upload = server_data / "_upload"
server_scripts = server_path / "scripts"
server_log = server_data / "log"
migrations_dir = server_data / "migrations"

config = {
    "puid": 1000,
    "pgid": 1000,
    "tz": "",
    "admin_name": "admin",
    "admin_passwd": "admin",
    "domain_name": "",
}
group_info = {"name": "server", "id": config["pgid"]}
user_info = {"name": "server", "id": config["puid"]}


def check_env():
    """
    Environment checks.
    :return: True if everything OK.
    """
    # get config from environment variables
    for key, val in os.environ.items():
        print(f"{key}={val}")
        for key_config in config:
            if key.lower() == key_config:
                config[key_config] = val
    # verify the config
    result = True
    if type(config["puid"]) is str:
        try:
            uid = int(config["puid"])
        except Exception as err:
            uid = 0
            result = False
            print(f"ERROR: PUID must be integer ({err})", file=stderr)
        config["puid"] = uid
    if type(config["pgid"]) is str:
        try:
            gid = int(config["pgid"])
        except Exception as err:
            gid = 0
            result = False
            print(f"ERROR: PGID must be integer ({err})", file=stderr)
        config["pgid"] = gid
    if config["domain_name"] in [None, ""]:
        print(
            "Warning: DOMAIN_NAME environment variable Must be set to allow POST requests.",
            file=stderr,
        )
        print(
            "         It can be in the form of real domain name: 'example.com' or an IP.",
            file=stderr,
        )
        print(
            "         If you are not using the standard http or https port, don't forget to add it e.g. '127.0.0.1:8080'.",
            file=stderr,
        )
    if not result:
        print("Problem in environment...", file=stderr)
        print("======== ENV DUMP ==========", file=stderr)
        for key, val in config.items():
            print(f"{key}={val}", file=stderr)
        print("====== END ENV DUMP ========", file=stderr)
    else:
        print("Environment OK.")
    return result


def check_user_exist():
    """
    Check and create user & group as required
    """
    import pwd
    import grp

    global user_info, group_info
    try:
        # check group info and name
        group_info["id"] = config["pgid"]
        if group_info["id"] in [it.gr_gid for it in grp.getgrall()]:
            # a group with the needed Id already exists -> using its name
            group_info["name"] = str(grp.getgrgid(group_info["id"]).gr_name)
            print(
                f"Group {group_info['id']} already exist with name: {group_info['name']}"
            )
        else:
            if group_info["name"] in [str(it.gr_name) for it in grp.getgrall()]:
                # a group with the default name already exists -> adapt the name
                group_info["name"] += "_docker"
                while group_info["name"] in [str(it.gr_name) for it in grp.getgrall()]:
                    print(f"Group named {group_info['name']} already exist...")
                    group_info["name"] += "0"
            print(
                f"Create group named {group_info['name']} with gid: {group_info['id']}"
            )
            if not exec_cmd(
                f"addgroup -g {group_info['id']} {group_info['name']}", True
            ):
                print("ERROR detected during addgroup...", file=stderr)
                return False

        # check user info and name
        user_info["id"] = config["puid"]
        if user_info["id"] in [it.pw_uid for it in pwd.getpwall()]:
            # a user with the needed id already exists, use its name
            user_info["name"] = str(pwd.getpwuid(user_info["id"]).pw_name)
            print(
                f"User {user_info['id']} already exist with name: {user_info['name']}"
            )
        else:
            if user_info["name"] in [str(it.pw_name) for it in pwd.getpwall()]:
                # a user with the default name already exists -> adapt the name
                user_info["name"] += "_docker"
                while user_info["name"] in [str(it.pw_name) for it in pwd.getpwall()]:
                    print(f"User named {user_info['name']} already exist...")
                    user_info["name"] += "0"
            print(f"Create user named {user_info['name']} with pid: {user_info['id']}")
            if not exec_cmd(
                f"adduser -D -H -u {user_info['id']} -G {group_info['name']} {user_info['name']}",
                True,
            ):
                print("ERROR detected during adduser...", file=stderr)
                return False
    except Exception as err:
        print(f"ERROR: unable to check user: {err}", file=stderr)
        return False
    print(f"Everything is OK with user.")
    return True


def correct_permission():
    """
    Check and correct the data permission.
    Ensures all required directories exist and everything under /app/data
    belongs to the configured PUID/PGID.
    """
    try:
        # Ensure all required directories exist
        folder_list = [
            server_data,
            server_log,
            packages_dir,
            documentation_dir,
            migrations_dir,
        ]
        for i in range(10):
            folder_list.append(server_data_upload / str(i))
        for folder in folder_list:
            folder.mkdir(parents=True, exist_ok=True)

        # Recursively chown everything under /app/data
        uid = user_info["id"]
        gid = group_info["id"]
        for root, dirs, files in os.walk(server_data):
            for d in dirs:
                os.chown(os.path.join(root, d), uid, gid)
            for f in files:
                os.chown(os.path.join(root, f), uid, gid)
        os.chown(server_data, uid, gid)
        print(
            f"Permissions set on {server_data} to "
            f"{user_info['name']}({uid}):{group_info['name']}({gid})"
        )
    except Exception as err:
        print(f"ERROR: unable to change permission: {err}", file=stderr)
        return False
    print(f"Everything is OK with permissions.")
    return True


def exec_cmd(cmd: str, as_root=False):
    """
    Execute a command in shell with right ID.
    :param cmd: The command to run.
    :param as_root: if must be run as root.
    :return:
    """
    import subprocess

    def demote():
        """
        Change the exec credential.
        """

        def setId():
            """
            Define the user id.
            """
            import os

            os.setgid(group_info["id"])
            os.setuid(user_info["id"])

        return setId

    try:
        if as_root:
            p = subprocess.run(str(cmd), shell=True)
        else:
            p = subprocess.run(str(cmd), shell=True, preexec_fn=demote())
        return p.returncode == 0
    except Exception as err:
        print(f"ERROR Executing {cmd} : {err}", file=stderr)
    return False


def fall_back():
    """
    If something goes wrong fall back to console
    """
    print("Falling back.")
    shell = Path("/bin/bash")
    if not shell.exists():
        shell = Path("/bin/sh")
    try:
        print(f"Executing {shell}.")
        exec_cmd(str(shell), True)
    except Exception as err:
        print(f"ERROR Executing shell fallback : {err}.", file=stderr)
    print("End of fallback :( .")


def get_user_group():
    """
    Get the user and group for execution.
    :return: user_name, group_name.
    """
    import pwd, grp

    try:
        user_name = str(pwd.getpwuid(config["puid"]).pw_name)
        group_name = str(grp.getgrgid(config["pgid"]).gr_name)
    except Exception as err:
        print(
            f"ERROR no user or group with uid={config['puid']} gid={config['puid']}: {err}.",
            file=stderr,
        )
        print(f"Fallback to root", file=stderr)
        user_name = "root"
        group_name = "root"
    return user_name, group_name


def check_timezone():
    """
    Set the right Time zone if not zone already defined
    :return: True if everything is OK.
    """
    if config["tz"] not in [None, ""] and not Path("/etc/localtime").exists():
        print("Initializing TimeZone")
        start = Path("/usr/share/zoneinfo") / config["tz"]
        if not start.exists():
            print(f"ERROR zone {config['tz']} does not exists in tzdata.", file=stderr)
            return False
        shutil.copy2(start, Path("/etc/localtime"))
        with open("/etc/timezone", "w") as fp:
            fp.write(f"{config['tz']}\n")
    return True


def check_admin_user():
    """
    Server initialization
    """
    print("Checking for an admin user")
    try:
        # create log folder if not exists
        print("Check if an admin user already exists.")
        import sqlite3

        con = sqlite3.connect("/app/data/delivery.db")
        cur = con.cursor()
        res = cur.execute("SELECT * FROM auth_user WHERE is_superuser=1")
        ls_admin = res.fetchall()
        admin_exist = len(ls_admin) > 0
        if admin_exist:
            print(f"One admin already exists.")
        else:
            print(f"Create new admin user named {config['admin_name']}.")
            cmd = (
                f'python3 manage.py shell -c "'
                f"from django.contrib.auth import get_user_model; "
                f"User=get_user_model(); "
                f"User.objects.create_superuser("
                f"'{config['admin_name']}',"
                f"'admin@foo.bar',"
                f"'{config['admin_passwd']}')"
                f'"'
            )
            print(f"Executing: '{cmd}'")
            return exec_cmd(cmd)
    except Exception as err:
        print(f"ERROR exception during Server Initialization: {err}.", file=stderr)
        return False
    # default: nothing to do
    return True


def dump_migrations(src: Path, dest: Path):
    """
    Dump or restore migration files
    :param src:
    :param dest:
    :return:
    """
    dest.mkdir(parents=True, exist_ok=True)
    for file in src.glob("**/migrations/*.py"):
        if file.is_file():
            destination = dest / file.relative_to(src)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, destination)


def do_migrations():
    """
    Execute the migrations
    """
    print("Checking migrations")
    if migrations_dir.exists():
        print("Restoring previous migrations")
        dump_migrations(migrations_dir, server_path)
    os.chdir(server_scripts)
    if not exec_cmd("python3 manage.py makemigrations"):
        print("ERROR: Error making migrations.", file=stderr)
        return False
    if not exec_cmd("python3 manage.py migrate"):
        print("ERROR: Error migrating.", file=stderr)
        return False
    print("Saving migrations")
    dump_migrations(server_path, migrations_dir)
    fix_absolute_media_paths()
    print("Migrations OK.")
    return True


def fix_absolute_media_paths():
    """
    Fix legacy absolute paths in FileField columns.
    Old MEDIA_ROOT was /data, so Django stored names like /data/packages/...
    They need to be relative: packages/...
    """
    import sqlite3

    db_path = server_data / "delivery.db"
    if not db_path.exists():
        return
    print("Checking for legacy absolute media paths in database")
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    try:
        cur.execute(
            "UPDATE delivery_revisionitementry SET package = SUBSTR(package, 7) "
            "WHERE package LIKE '/data/%'"
        )
        updated = cur.rowcount
        if updated > 0:
            con.commit()
            print(f"Fixed {updated} legacy absolute paths in delivery_revisionitementry")
        else:
            print("No legacy paths to fix.")
    except Exception as err:
        print(f"WARNING: could not fix legacy paths: {err}", file=stderr)
    finally:
        con.close()


def collect_static():
    """
    Collect static files for Django
    """
    print("Collecting static files")
    os.chdir(server_scripts)
    if not exec_cmd("python3 manage.py collectstatic --noinput", True):
        print("ERROR: Error collecting static files.", file=stderr)
        return False
    print("Static files collected.")
    return True


def start_server():
    """
    Start of the Server
    """
    print("Starting server")
    os.chdir(server_scripts)
    print("Starting Nginx:")
    if not exec_cmd(f"/usr/sbin/nginx -c /app/server/config/nginx.conf", True):
        fall_back()
    print("Starting Gunicorn:")
    os.chdir(server_scripts)
    if not (server_scripts / "scripts" / "wsgi.py").exists():
        print(f"ERROR: no project scripts is configured.", file=stderr)
        return False
    cmd = (
        "gunicorn scripts.wsgi"
        " --bind=0.0.0.0:8000"
        " --reload"
        " --log-level info"
        " --log-file /app/data/log/gunicorn.log"
    )
    print(f"Executing: '{cmd}'")
    os.execvp("gunicorn", [
        "gunicorn", "scripts.wsgi",
        "--bind=0.0.0.0:8000",
        "--reload",
        "--log-level", "info",
        "--log-file", "/app/data/log/gunicorn.log",
    ])
    return True


def main():
    """
    Main Entrypoint
    """
    print("Django webserver starting")
    if check_env():
        if not check_user_exist():
            fall_back()
            return
        if not check_timezone():
            fall_back()
            return
        if not correct_permission():
            fall_back()
            return
        if not do_migrations():
            fall_back()
            return
        if not correct_permission():
            fall_back()
            return
        if not collect_static():
            fall_back()
            return
        if not check_admin_user():
            fall_back()
            return
        if not start_server():
            fall_back()
            return
    else:
        print("ERROR in environment, fall back to bash", file=stderr)
        fall_back()


if __name__ == "__main__":
    main()
