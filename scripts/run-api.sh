#!/usr/bin/env bash
# Usage: bash scripts/run-api.sh <module>   (needs: npm i -g newman)
set -e
MOD="${1:?module}"
mkdir -p reports
newman run api/collections/"$MOD".postman_collection.json -e api/environments/"$MOD".postman_environment.json --reporters cli,junit --reporter-junit-export reports/api-"$MOD".xml
