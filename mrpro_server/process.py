"""Processing"""

import logging
import tempfile
from collections.abc import Sequence

import ismrmrd
import mrpro
import torch


def process(
    acquisitions: Sequence[ismrmrd.Acquisition],
    config: dict,
    metadata: str,
    images: list[ismrmrd.Image],
    waveforms: list[ismrmrd.Waveform],
) -> list[ismrmrd.Image]:
    """Process ISMRMRD Acquisitions to ISMRMRD Images."""

    with tempfile.TemporaryDirectory() as tmpdir:
        # TODO: create KData directly from ISMRMRD Acquisitions
        file = tmpdir + "/data.mrd"
        with ismrmrd.Dataset(file) as dset:
            dset.write_xml_header(metadata)
            for acq in acquisitions:
                dset.append_acquisition(acq)
        logging.info("KData written to %s", file)

        ##################################################

        kdata = mrpro.data.KData.from_file(file, ktrajectory=mrpro.data.traj_calculators.KTrajectoryCartesian())
        recon = mrpro.algorithms.reconstruction.DirectReconstruction(kdata)
        image = recon(kdata)
        logging.info("Reconstruction done. Image info: %s", str(image))

        ##################################################

        # TODO: creae ISMRMRD Image from IData
        data = image.data.detach().to(torch.complex64).cpu().flatten(end_dim=-5).numpy()
        fov = kdata.header.recon_fov.apply(mrpro.utils.unit_conversion.m_to_mm)
        images = []
        for i, current_data in enumerate(data):
            ismrmrd_image = ismrmrd.Image.from_array(
                current_data, acquisition=acquisitions[0], transpose=False, field_of_view=(fov.x, fov.y, fov.z)
            )
            meta = ismrmrd.Meta(
                {
                    "DataRole": "Image",
                    "ImageRowDir": [f"{v:.18f}" for v in ismrmrd_image.getHead().read_dir],
                    "ImageColumnDir": [f"{v:.18f}" for v in ismrmrd_image.getHead().phase_dir],
                    "Keep_image_geometry": 1,
                }
            )
            ismrmrd_image.attribute_string = meta.serialize()
            ismrmrd_image.image_index = i + 1
            images.append(ismrmrd_image)
        logging.info("ISMRMRD Images created")
        return images
