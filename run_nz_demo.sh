#!/usr/bin/env bash
# run_nz_demo.sh — Run the NZ ETAS demo using the pre-built fat jar.
#
# Usage:
#   ./run_nz_demo.sh                          # uses etas_config.json in current directory
#   ./run_nz_demo.sh path/to/my_config.json   # uses a custom config file
#   ./run_nz_demo.sh 2016p858000 7 14         # legacy positional args (eventId dataEnd forecastEnd)
#
# Rebuild the jar after any code change with:
#   ./gradlew appNZDemoJar

JAR="$(dirname "$0")/build/libs/ETAS_Demo_NZ.jar"

if [ ! -f "$JAR" ]; then
    echo "ERROR: Jar not found at $JAR"
    echo "Build it first with: ./gradlew appNZDemoJar"
    exit 1
fi

# Default to config file if no args supplied
if [ $# -eq 0 ]; then
    CONFIG="$(dirname "$0")/etas_config.json"
    if [ ! -f "$CONFIG" ]; then
        echo "ERROR: No arguments supplied and no etas_config.json found in $(dirname "$0")"
        exit 1
    fi
    set -- --config "$CONFIG"
fi

java -jar "$JAR" "$@"
