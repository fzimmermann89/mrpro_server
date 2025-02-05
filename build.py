import base64
import json
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import jsonschema
import requests
from jinja2 import BaseLoader, Environment

CONFIG_TEMPLATE = r"""
{
  "general": {
    "name": { "en": "{{ name }}" },
    "version": "{{ version }}",
    "vendor": "{{ vendor }}",
    "information": { "en": "{{ information }}" },
    "id": "{{ name|lower }}",
    "regulatory_information": {
      "device_trade_name": "{{ name|lower }}",
      "production_identifier": "{{ version }}",
      "manufacturer_address": "Somewhere",
      "made_in": "Somewhere",
      "manufacture_date": "{{ now('%Y/%m/%d') }}",
      "material_number": "{{ name|lower }}_{{ version|replace('.', '_') }}",
      "gtin": "00000000000000",
      "udi": "(00)00000000000000(00)0.0.0",
      "safety_advices": "",
      "special_operating_instructions": "None",
      "additional_relevant_information": "None"
    }
  },
  "reconstruction": {
    "transfer_protocol": { "protocol": "ISMRMRD", "version": "1.4.1" },
    "port": 9002,
    "emitter": "raw",
    "injector": "compleximage",
    "can_process_adjustment_data": {{ can_process_adjustment_data|lower }},
    "can_use_gpu": {{ can_use_gpu|lower }},
    "min_count_required_gpus": {{ min_count_required_gpus }},
    "min_required_gpu_memory": {{ min_required_gpu_memory }},
    "min_required_memory": {{ min_required_memory }},
    "min_count_required_cpu_cores": {{ min_count_required_cpu_cores }},
    "content_qualification_type": "RESEARCH"
  },
  "parameters": {{ ui|tojson }}
}
"""


def render_config(settings_path: Path, context: dict) -> dict:
    env = Environment(loader=BaseLoader())
    env.globals["now"] = lambda fmt: datetime.now().strftime(fmt)
    env.filters["tojson"] = lambda value: json.dumps(value, ensure_ascii=False)
    settings_str = settings_path.read_text(encoding="utf-8")
    settings = json.loads(env.from_string(settings_str).render(**context))
    config = json.loads(env.from_string(CONFIG_TEMPLATE).render(**settings))
    return config


def main() -> None:
    print("Fetching latest mrpro version...")
    latest_mrpro_version: str = requests.get("https://pypi.org/pypi/mrpro/json").json()["info"]["version"]
    print(f"Latest mrpro version: {latest_mrpro_version}")
    mrpro_major, mrpro_minor = latest_mrpro_version.split(".", 1)
    config = render_config(Path("settings.json"), {"mrpro_major": mrpro_major, "mrpro_minor": mrpro_minor})

    schema = json.load(Path("siemens_schema.json").open())
    if errors := list(jsonschema.Draft7Validator(schema).iter_errors(config)):
        print(errors)
        raise ValueError("Json is not valid:\n" + "\n".join(errors))

    vendor = config["general"]["vendor"]
    name = config["general"]["name"]["en"]
    version = config["general"]["version"]
    name = f"OpenRecon_{vendor}_{name}_V{version}"
    tag = f"openrecon_{vendor.lower()}_{name.lower()}:v{version}"
    config_encoded = base64.b64encode(json.dumps(config, indent=2).encode("utf-8")).decode("utf-8")

    with tempfile.TemporaryDirectory() as tmp_dir:
        docker_image_path = Path(tmp_dir) / f"{name}.tar"

        print("Building Docker image...")
        subprocess.run(
            [
                "docker",
                "build",
                "mrpro_server",
                "-f",
                "Dockerfile",
                "-t",
                tag,
                "--build-arg",
                f"CONFIG={config_encoded}",
                "--build-arg",
                f"VERSION={version}",
                "--build-arg",
                f"MRPRO_VERSION={latest_mrpro_version}",
            ],
            check=True,
        )

        print("Saving Docker image...")
        subprocess.run(["docker", "save", tag, "-o", str(docker_image_path)], check=True)

        print("Creating archive...")
        with zipfile.ZipFile(f"{name}.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(docker_image_path, docker_image_path.name)
            archive.write("info.pdf", f"{name}.pdf")

    print(f"Archive created: {name}.zip")

    print("Copying to mars")
    subprocess.run(["scp", f"{name}.zip", "mars:/opt/medcom/openrecon_incomin"])


if __name__ == "__main__":
    main()
