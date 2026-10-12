#!/usr/bin/env bash
# Prints a unique test email. Usage: bash scripts/gen-user.sh [prefix]
echo "${1:-qa}+$(date +%s)${RANDOM}@example.com"
