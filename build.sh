#!/usr/bin/env bash
#
# Regenerate every generated part of the site.
#
#   ./build.sh          apply
#   ./build.sh --check  verify only; non-zero exit if anything is stale
#
# Order matters:
#   1. pages     - create the tour/destination pages first, so later steps
#                  have them to link to and validate against
#   2. listings  - card grids and forms, which link to those pages
#   3. seo       - reads the finished <title> of every page
#   4. alt text  - runs over all images, including newly generated ones
#   5. propagate - stamps the shared chrome last, so it lands everywhere
#
# Note on --check: each stage legitimately rewrites what earlier stages
# produced, so a per-stage --check reports false staleness. Instead we run the
# whole pipeline into a scratch copy and diff the result against the working
# tree, which is what "are the committed files up to date?" actually means.
#
set -euo pipefail
cd "$(dirname "$0")"

STEPS=(build_pages build_listings build_seo build_alt_text propagate)

run_pipeline() {
    for step in "${STEPS[@]}"; do
        echo "--- ${step} ---"
        python3 "scripts/${step}.py"
    done
}

if [[ "${1:-}" == "--check" ]]; then
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT

    cp ./*.html "$tmp"/ 2>/dev/null || true
    cp sitemap.xml "$tmp"/ 2>/dev/null || true
    cp -r data partials scripts css js "$tmp"/
    # images/ is 14MB and only ever read for existence checks - link, don't copy.
    ln -s "$PWD/images" "$tmp/images"
    ln -s "$PWD/fonts" "$tmp/fonts"

    ( cd "$tmp" && run_pipeline ) >/dev/null 2>&1 || {
        echo "BUILD FAILED during --check; run ./build.sh to see the error."
        exit 1
    }

    stale=0
    for f in "$tmp"/*.html "$tmp"/sitemap.xml; do
        name=$(basename "$f")
        if [[ ! -f "$name" ]] || ! diff -q "$name" "$f" >/dev/null 2>&1; then
            echo "STALE: $name"
            stale=1
        fi
    done

    if [[ $stale -ne 0 ]]; then
        echo
        echo "Generated files are out of date. Run ./build.sh"
        exit 1
    fi
    echo "Everything up to date."
    exit 0
fi

run_pipeline
echo

# grep exits 1 when it finds nothing, which is the good case here; with
# `set -e` and pipefail that would abort the script before the summary.
dead=$( { grep -o 'href="#"' ./*.html 2>/dev/null || true; } | wc -l | tr -d ' ')
echo "Build complete. Dead links: ${dead}"
[[ "$dead" == "0" ]] || { echo "WARNING: dead links present."; exit 1; }
