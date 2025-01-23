import base64
import json
import tempfile
import subprocess
import requests
import zipfile
from pathlib import Path

def main():
    config_file = Path("config.json")
    config_data = json.loads(config_file.read_text())
    vendor = config_data["general"]["vendor"]
    name_en = config_data["general"]["name"]["en"]
    version = config_data["general"]["version"]

    name = f"OpenRecon_{vendor}_{name_en}_V{version}"
    tag = f"openrecon_{vendor.lower()}_{name_en.lower()}:v{version}"
    config_encoded = base64.b64encode(config_file.read_bytes()).decode("utf-8")

    print("Fetching latest mrpro version...")
    latest_mrpro_version = requests.get("https://pypi.org/pypi/mrpro/json").json()["info"]["version"]
    print(f"Latest mrpro version: {latest_mrpro_version}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        docker_image_path = tmp_dir_path / f"{name}.tar"

        print("Building Docker image...")
        subprocess.run([
            "docker", "build", "mrpro_server",
            "-f", "Dockerfile",
            "-t", tag,
            "--build-arg", f"CONFIG={config_encoded}",
            "--build-arg", f"VERSION={version}",
            "--build-arg", f"MRPRO_VERSION={latest_mrpro_version}"
        ], check=True)

        print("Saving Docker image...")
        subprocess.run(["docker", "save", tag, "-o", str(docker_image_path)], check=True)

        print("Creating archive...")
        with zipfile.ZipFile(f"{name}.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(docker_image_path, docker_image_path.name)
            archive.write("info.pdf", f"{name}.pdf")

    print(f"Archive created: {name}.zip")

if __name__ == "__main__":
    main()
