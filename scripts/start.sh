# This would be needed when someone clones the repository. (After adding their own POSTGRES Password)

#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

# Compose project/port overrides can be supplied through the environment.
docker compose config --quiet
docker compose build etl frontend
docker compose up -d --wait db
# Refresh rewrites the star tables. Keep the frontend stopped until it completes.
docker compose stop frontend
docker compose --profile etl run --rm etl
docker compose up -d --wait frontend
docker compose ps
