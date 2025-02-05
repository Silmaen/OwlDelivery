# OwlDelivery

Webserver For Owl Delivery and documentation

This server aim to host the delivery packages of the Owl Game engine [Owl Engine](https://github.com/Silmaen/Owl).

## Docker

### Docker image

Most parts of the work reside in a docker image can can simply be deployed.

`docker pull registry.argawaen.net/servers/owl-delivery-server`

### Docker compose

It is possible to use the server directly in Docker compose:

```yaml
version: "3.8"
services:
  owl-delivery-server:
    image: registry.argawaen.net/servers/owl-delivery-server
    container_name: owl-delivery-server
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    volumes:
      - /srv/owldeliv/data:/data       # Persistent volume for package storage, logs, internal database.
      - /etc/timezone:/etc/timezone:ro # Defines the same timezone as the host.
    ports:
      - 80:80                          # Port of the web UI.
    environment:
      - PUID=1000                      # UID used for file writing.
      - PGID=1000                      # GID used for file writing.
      - DOMAIN_NAME="example.com"      # The domain of this server (mandatory for correct usage).
      - ADMIN_NAME="admin"             # login of the first admin.
      - ADMIN_PASSWD="MyBigPassW0rd"   # passwd of the first admin.
      - EMAIL_HOST="mail.example.com"  # URL of the mail server.
      - EMAIL_PORT=587                 # Port of the mail server.
      - EMAIL_USE_TLS="True"           # If server uses TLS.
      - EMAIL_USER="admin"             # Email user login.
      - EMAIL_PASSWD="MyBigPassW0rd"   # Email user password.
      - DEBUG_MODE="False"             # Set Django in debug mode.
      - ENABLE_STAFF="False"           # Activate the staff section for admin users
```

## Variables details

### TZ

Define he time zone to use in the container. You can directly define your Time zone by setting this variable.

Another trick to use the host's defined times zone is to not set this variable and set
`/etc/timezone:/etc/timezone:ro` as a volume (works only if the host is unix-like).

### PUID, PGID

Defines user and group ids number used in server run. Thus, all files uploaded will have these ids
as owner.

### DOMAIN_NAME

The domain of this server. This parameter is mandatory because used in CSRF resolution of POST REQUESTS.
By default, '127.0.0.1' and 'localhost' are used. It is also important to add the port if not using
standard http or https ports in request.

If you can access to this server by the url `http://10.15.165.12:7856`
then use `DOMAIN_NAME:"10.15.165.12:7856"`.

If you can access to this server by the url
`https://any.deliv.home.lan:785` then use `DOMAIN_NAME:"home.lan:785"` or
`DOMAIN_NAME:"deliv.home.lan:785"`

### ADMIN_NAME, ADMIN_PASSWD

Define the first admin user login and password. If an admin user already
exists in the database these parameters are ignored. The only purpose is
to have an admin defined at the first run of a fresh new instance with no
data.

By default, `admin` will be the login and the password.

After the first initialization, it is strongly recommended to change this
admin password!

### EMAIL configuration

Define your mail server `EMAIL_HOST` its address, `EMAIL_PORT` its port.
`EMAIL_USE_TLS` defines if TLS transaction should be used.
If `EMAIL_USER` and  `EMAIL_PASSWD` are set, the communication will use these
credentials.

### Options

`DEBUG_MODE` is a developer option to display the django error messages. Default
is `false` meaning production environment.

`ENABLE_STAFF` make available the 'admin' section of django with a bit more
advanced parameters than the classical admin. Use with cautions.

## Roadmap and versions

* [ ] 0.4.0
    * [ ] Possible link to OAuth authentication
    * [ ] allow mailing to user
        * [ ] tunable notification
        * [ ] notifications for new releases
        * [ ] notification for comments, etc.
* [ ] 0.3.0
    * [X] allow Engine API documentation pages
    * [ ] Branch display management
        * [ ] dissociate current release branch from other branches
        * [ ] allow to hide/see other branches
* [X] 0.2.0 -- release 2025-02-03
    * [X] Revision reorganization
        * [X] Use branch filtering
* [X] 0.1.0 -- first release 2024-05-18
    * [X] user management
        * [X] allow user login and registration
        * [X] allow changing permission to users
        * [X] allow the user to see/edit their information
        * [X] allow user to reset their credential (Require a valid setup of mail server)
    * [X] revision management
        * [X] Pages to navigate through revisions
        * [X] Special address to download push script.
            * [X] Automated push script
    * [X] admin sections
        * [X] can delete revision or revision items
