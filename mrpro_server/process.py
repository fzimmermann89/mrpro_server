"""Processing."""

import gc
import logging
import resource
import tempfile
from pathlib import Path

import constants
import ismrmrd
import mrpro
import torch


def process(
    acquisitions: list[ismrmrd.Acquisition],
    config: dict,
    metadata: str,
    images: list[ismrmrd.Image],
    waveforms: list[ismrmrd.Waveform],
) -> list[ismrmrd.Image]:
    """Process ISMRMRD Acquisitions to ISMRMRD Images."""

    reference = acquisitions[0]  # Only needed until we can build header from IData
    with tempfile.TemporaryDirectory() as tmpdir:
        # TODO: create KData directly from ISMRMRD Acquisitions
        file = Path(tmpdir) / "data.mrd"
        with ismrmrd.Dataset(file) as dset:
            dset.write_xml_header(metadata)
            while acquisitions:
                dset.append_acquisition(acquisitions.pop())
        logging.info(f"KData written to {file!s}. Size:  {file.stat().st_size}")
        gc.collect()

        ##################################################

        kdata = mrpro.data.KData.from_file(file, trajectory=mrpro.data.traj_calculators.KTrajectoryCartesian())
        csm = mrpro.data.CsmData(torch.from_numpy(images[0].data).permute(-1, -2, -3).unsqueeze(0), kdata.header)
        logging.debug(f"KData: {kdata!s}")
        logging.debug(f"CSM: {csm!s}")

        recon = mrpro.algorithms.reconstruction.IterativeSENSEReconstruction(kdata, csm=csm)
        image = recon(kdata)

        logging.info("Reconstruction done")
        logging.debug(f"Memory used by Python process: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.2f} MB")

        ##################################################

        # TODO: create ISMRMRD Image from IData
        data = image.rss(keepdim=True).detach().cpu().flatten(end_dim=-5).to(torch.complex64)
        scale = (data.shape[-3:].numel()) ** 0.5
        data = data * scale  # ICE uses no scaling in backward
        fov = kdata.header.recon_fov.apply(mrpro.utils.unit_conversion.m_to_mm)

        new_images = []
        for i, current_data in enumerate(data):
            ismrmrd_image = ismrmrd.Image.from_array(
                current_data.numpy(), acquisition=reference, transpose=False, field_of_view=(fov.x, fov.y, fov.z)
            )
            directions = kdata.header.acq_info.orientation.reshape(-1)[0].as_directions()
            logging.debug(f"Orientations {directions!s}")
            meta = ismrmrd.Meta(
                {
                    "DataRole": "Image",
                    "ImageRowDir": [f"{v:.18f}" for v in ismrmrd_image.getHead().read_dir],
                    "ImageColumnDir": [f"{v:.18f}" for v in ismrmrd_image.getHead().phase_dir],
                    "Keep_image_geometry": 1,
                    "ImageComments": config["comment"],
                }
            )

            ismrmrd_image.attribute_string = meta.serialize()
            ismrmrd_image.image_index = i  # type: ignore
            ismrmrd_image.image_type = constants.IMTYPE_COMPLEX  # type: ignore
            new_images.append(ismrmrd_image)

        return new_images
