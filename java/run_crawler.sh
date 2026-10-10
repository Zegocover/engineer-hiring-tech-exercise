#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -f build/libs/crawler.jar ]]; then
  ./gradlew -q shadowJar
fi
exec java -jar build/libs/crawler.jar "$@"
