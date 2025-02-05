# Openrecon MRpro Server

Basic docker image for an openrecon image using [MRpro](https://github.com/PTB-MR/mrpro) for MRI image reconstruction

## Build requirements

- Docker
- Python 3.11

## Modifications

To change the reconstruction, modify `process.py`.
To change the UI, modify `settings.json`

## Build

- Run `pip install .` to install dependencies
- Run `python build.py`.

Follow openrecon manual to install the zip file at the scanner.
