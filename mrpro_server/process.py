"""Processing."""

import gc
import logging
import resource
import tempfile
from pathlib import Path

from einops import rearrange
import mrpro.operators.models.EPG

import constants
import ismrmrd
import mrpro
import torch

from combine_mrd_header import combine_ismrmrd_files


def process(
    acquisitions: list[ismrmrd.Acquisition],
    config: dict,
    metadata: str,
    images: list[ismrmrd.Image],
    waveforms: list[ismrmrd.Waveform],
) -> list[ismrmrd.Image]:
    """Process ISMRMRD Acquisitions to ISMRMRD Images."""

    reference = acquisitions[0]  # Only needed until we can build header from IData

    # read flip angle pattern
    with open(Path("flip_angle_pattern.txt"), "r") as file:
        fa = torch.as_tensor([float(line) for line in file.readlines()]) / 180 * torch.pi

    with tempfile.TemporaryDirectory() as tmpdir:
        # TODO: create KData directly from ISMRMRD Acquisitions
        file = Path(tmpdir) / "data.mrd"
        with ismrmrd.Dataset(file) as dset:
            dset.write_xml_header(metadata)
            while acquisitions:
                dset.append_acquisition(acquisitions.pop())

        # combine data and header to data_with_traj.h5
        _ = combine_ismrmrd_files(file, Path("header.h5"))

        logging.info(f"KData written to {file!s}. Size:  {file.stat().st_size}")
        gc.collect()

        ##################################################

        # Define the T1 and T2 values to be included in the dictionaries
        t1 = torch.cat(
            (torch.arange(50, 2000 + 10, 10), torch.arange(2020, 3000 + 20, 20), torch.arange(3050, 5000 + 50, 50))
        )
        t2 = torch.cat((torch.arange(6, 100 + 2, 2), torch.arange(105, 200 + 5, 5), torch.arange(220, 500 + 20, 20)))

        n_lines_per_img = 20
        n_lines_overlap = 10

        kdata = mrpro.data.KData.from_file(
            Path(tmpdir) / "data_with_traj.h5", mrpro.data.traj_calculators.KTrajectoryIsmrmrd()
        )
        logging.info("KData created")
        avg_recon = mrpro.algorithms.reconstruction.DirectReconstruction(kdata)
        logging.info("avg img created")

        # Split data into dynamics and reconstruct
        dyn_idx = mrpro.utils.split_idx(torch.arange(0, 47), n_lines_per_img, n_lines_overlap)
        dyn_idx = torch.cat([dyn_idx + ind * 47 for ind in range(15)], dim=0)

        kdata_dyn = kdata.split_k1_into_other(dyn_idx, other_label="repetition")

        dyn_recon = mrpro.algorithms.reconstruction.DirectReconstruction(kdata_dyn, csm=avg_recon.csm)
        logging.info("dyn img reco done")
        dcf_data_dyn = rearrange(avg_recon.dcf.data, "k2 k1 other k0->other k2 k1 k0")
        dcf_data_dyn = rearrange(
            dcf_data_dyn[dyn_idx.flatten(), ...], "(other k1) 1 k2 k0->other k2 k1 k0", k1=dyn_idx.shape[-1]
        )
        dyn_recon.dcf = mrpro.data.DcfData(dcf_data_dyn)

        img = dyn_recon(kdata_dyn).rss()[:, 0, :, :]
        logging.info("dyn images created")

        # Dictionary settings
        t1, t2 = torch.broadcast_tensors(t1[None, :], t2[:, None])
        t1_all = t1.flatten().to(dtype=torch.float32)
        t2_all = t2.flatten().to(dtype=torch.float32)

        t1 = t1_all[t1_all >= t2_all]
        t2 = t2_all[t1_all >= t2_all]
        m0 = torch.ones_like(t1)

        # Dictionary calculation
        n_rf_pulses_per_block = 47  # 47 RF pulses in each block
        acq_t_ms = kdata.header.acq_info.acquisition_time_stamp[0, 0, :, 0] * 2.5
        delay_between_blocks = [
            acq_t_ms[n_block * n_rf_pulses_per_block] - acq_t_ms[n_block * n_rf_pulses_per_block - 1]
            for n_block in range(1, 3 * 5)
        ]
        delay_between_blocks.append(delay_between_blocks[-1])  # last delay is not needed but makes computations easier

        flip_angles = fa
        rf_phases = 0.0
        te = 1.52
        tr = 6.6
        inv_prep_ti = [21, None, None, None, None] * 3  # 21 ms delay after inversion pulse in block 0
        t2_prep_te = [None, None, 30, 50, 100] * 3  # T2-preparation pulse with TE = 30, 50, 100
        delay_due_to_prep = [0, 30, 50, 100, 21] * 3
        delay_after_block = [
            trig_delay - prep_delay for prep_delay, trig_delay in zip(delay_due_to_prep, delay_between_blocks)
        ]
        epg_mrf_fisp = mrpro.operators.models.EPG.EpgMrfFispWithPreparation(
            flip_angles, rf_phases, te, tr, inv_prep_ti, t2_prep_te, n_rf_pulses_per_block, delay_after_block
        )
        (signal_dictionary,) = epg_mrf_fisp.forward(m0, t1, t2)

        signal_dictionary = rearrange(
            signal_dictionary[dyn_idx.flatten(), ...], "(other k1) t->other t k1", k1=dyn_idx.shape[-1]
        )
        signal_dictionary = torch.mean(signal_dictionary, dim=-1)
        signal_dictionary = signal_dictionary.abs()

        # Normalise dictionary entries
        vector_norm = torch.linalg.vector_norm(signal_dictionary, dim=0)
        signal_dictionary /= vector_norm

        # Dictionary matching
        n_y, n_x = img.shape[-2:]
        dot_product = torch.mm(rearrange(img.abs(), "other y x->(y x) other"), signal_dictionary)
        idx_best_match = torch.argmax(torch.abs(dot_product), dim=1)
        data = rearrange(t1[idx_best_match], "(y x)->1 1 1 y x", y=n_y, x=n_x).to(torch.complex64)
        # t2_match = rearrange(t2[idx_best_match], "(y x)->y x", y=n_y, x=n_x)

        logging.info("Reconstruction done")
        logging.debug(
            f"Memory used by Python process: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.2f} MB"
        )

        ##################################################

        # TODO: create ISMRMRD Image from IData
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
                    "Keep_image_geometry": 0,
                    "ImageComments": config["comment"],
                }
            )

            ismrmrd_image.attribute_string = meta.serialize()
            ismrmrd_image.image_index = i
            ismrmrd_image.image_type = constants.IMTYPE_COMPLEX
            new_images.append(ismrmrd_image)

        return new_images
