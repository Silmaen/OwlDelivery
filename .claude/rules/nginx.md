---
paths:
  - "server/config/**"
---

# Nginx Configuration

## File Structure

- `server/config/nginx.conf` — main config (worker processes, logging, http block)
- `server/config/http.d/Django_server.conf` — server block (locations)

## Path Prefix

All paths inside nginx configs must use the `/app/` prefix:
- Static files: `root /app/server/data`
- Media alias: `alias /app/data`
- Upload store: `upload_store /app/data/_upload 1`
- Access log: `access_log /app/data/log/access.log`
- Include: `include /app/server/config/http.d/*.conf`

## Upload Module

The `/upload` location uses `nginx-mod-http-upload` to handle large file uploads before passing to Django. The upload module:
1. Receives the file directly into `/app/data/_upload/{0-9}/`
2. Rewrites the request body with file metadata (path, name, md5, size)
3. Forwards to `/api` for Django processing
4. Cleans up on 4xx-5xx errors
