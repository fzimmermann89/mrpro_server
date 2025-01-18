# Openrecon MRpro Server

Basic docker image for an openrecon image using [MRpro](https://github.com/PTB-MR/mrpro) for MRI image reconstruction

## Build requirements

- Docker
- jq
- zip

## Modifications

To change the reconstruction, modify `process.py`.
To change the UI, modify `config.json`

## Build

Run `build.sh`.
Follow openrecon manual to install the zip file at the scanner.
