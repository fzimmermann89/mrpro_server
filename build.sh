#!/bin/bash
set -euo pipefail

error_handler() {
    echo "Error occurred on line $BASH_LINENO while executing: $BASH_COMMAND"
    exit 1
}
trap error_handler ERR

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

for file in config.json info.pdf; do
    if [ ! -f "$file" ]; then
        echo "Error: $file not found."
        exit 1
    fi
done

config=$(base64 -w 0 config.json)
name=$(jq -r '"OpenRecon_\(.general.vendor)_\(.general.name.en)_V\(.general.version)"' config.json)
tag=$(jq -r '"openrecon_\(.general.vendor | ascii_downcase)_\(.general.name.en | ascii_downcase):v\(.general.version)"' config.json)
version=$(jq -r '.general.version' config.json)


echo "Getting latest mrpro version"
latest_mrpro_version=$(curl -fsSL https://pypi.org/pypi/mrpro/json | jq -r '.info.version')
echo "Latest mrpro version: $latest_mrpro_version"

echo "Building Docker image"
docker build mrpro_server \
    -f Dockerfile \
    -t "$tag" \
    --build-arg CONFIG="$config" \
    --build-arg VERSION="$version" \
    --build-arg MRPRO_VERSION="$latest_mrpro_version"

echo "Saving Docker image"
docker save "$tag" -o "$TMP_DIR/$name.tar"

echo "Creating archive"
cp info.pdf "$TMP_DIR/$name.pdf"
zip - "$TMP_DIR/$name.tar" "$TMP_DIR/$name.pdf" -j > "$name.zip"
echo "Archive created: $name.zip"