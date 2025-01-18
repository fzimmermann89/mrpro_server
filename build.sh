#!/bin/sh
set -e

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT


if [ ! -f config.json ]; then
    echo "Error: config.json not found"
    exit 1
fi

if [ ! -f info.pdf ]; then
    echo "Error: info.pdf not found"
    exit 1
fi

config=$(base64 config.json | tr -d '\n')
name=$(jq -r '"OpenRecon_\(.general.vendor)_\(.general.name.en)_V\(.general.version)"' config.json)
version=$(jq -r '.general.version' config.json)

echo "Building docker image"
docker build mrpro_server -f Dockerfile -t mrpro_server --build-arg CONFIG="$config" --build-arg VERSION="$version"

echo "Saving docker image to $TMP_DIR/$name.tar"
docker save mrpro_server -o "$TMP_DIR/$name.tar"

echo "Creating $name.zip"
cp info.pdf "$TMP_DIR/$name.pdf"
zip -9 - "$TMP_DIR/$name.tar" "$TMP_DIR/$name.pdf" -j > "$name.zip"

rm -rf "$TMP_DIR"
