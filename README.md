# OwlDelivery

Webserver For Owl Delivery and documentation

This server aim to host the delivery packages of the Owl Game engine [Owl Engine](https://github.com/Silmaen/Owl).

## Docker

### Docker image

Most parts of the work reside in a docker image can can simply be deployed.

`docker pull registry.argawaen.net/owl-delivery-server`

### Docker compose

It is possible to use the server directly in Docker compose:

```yaml
version: 3.8
services:
  owl-delivery-server:
    image: registry.argawaen.net/argawaen/owl-delivery-server
    container_name: owl-delivery-server
  volume:
    - /srv/data/owldeliv:/data       # Persistent volume for package storage, logs, internal database.
  ports:
    - 80:80                          # Port of the web UI.
  environment:
    - TZ:"Europe/Paris"              # The time zone to use in the container.
    - PUID:1000                      # UID used for file writing.
    - PGID:1000                      # GID used for file writing.
    - DOMAIN_NAME:"example.com"      # The domain of this server (mandatory for correct usage).
    - ADMIN_NAME:"admin"             # login of the first admin.
    - ADMIN_PASSWD:"MyBigPassW0rd"   # passwd of the first admin.
    - EMAIL_HOST:"mail.example.com"  # URL of the mail server.
    - EMAIL_PORT:587                 # Port of the mail server.
    - EMAIL_USE_TLS:"True"           # If server uses TLS.
    - EMAIL_USER:"admin"             # Email user login.
    - EMAIL_PASSWD:"MyBigPassW0rd"   # Email user password.
networks:
  default:
    name: proxyed_servers
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
By default: '127.0.0.1' and 'localhost' are used. It is also important to add the port if not using
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

## Content and capabilities

This server will provide both link to depmanager client as a remote and a web-based
UI to manage the content of the repository.

### General purpose capabilities

This server will allow control of user access: cli pull(& query)/push and UI read/write.
As 'write' in the UI we mean the possibility to delete a package.

### remote capabilities

As remote, the server will not send a deplist to the client (like for ftp server) that contains
the full content of the repository. Instead, it uses a sql table and each client query will pass
through the server.

### UI capabilities

UI can manager users, set database options, location of file of the repository.

It can also browse through the packages in the server.
