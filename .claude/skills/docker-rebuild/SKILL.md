---
name: docker-rebuild
description: Rebuild and restart the Docker container
---

# Rebuild and restart Docker

1. Run `docker compose down` to stop the running container
2. Run `docker compose build` to rebuild the image
3. Run `docker compose up -d` to start in detached mode
4. Run `docker compose logs -f --tail=50` to show recent logs
5. Report the result to the user
