# Functions for obtaining vacuum probe templates, including from vacuum scans, from a selected ROI
# of a scan over vacuum, or synthetic probes.  Ultimately the purpose is to generate a kernel for
# convolution with individual diffraction patterns to identify Bragg disks.  Kernel generation will
# generally proceed in two steps, which will each correspond to a function call: first, obtaining 
# or creating the diffraction pattern of a probe over vacuum, and second, turning the probe DP into
# a convolution kernel by shifting and normalizing.

import numpy as np
from scipy.ndimage.morphology import binary_opening, binary_dilation
from ..utils import get_shifted_ar, get_CoM, get_shift

#### Get the vacuum probe ####

def get_average_probe_from_vacuum_scan(datacube, mask_threshold=0.2, mask_expansion=12,
                                                 mask_opening=3):
    """
    Aligns and averages all diffraction patterns in a datacube, assumed to be taken over vacuum,
    to create and average vacuum probe.

    Values outisde the average probe are zeroed, using a binary mask determined by the optional
    parameters mask_threshold, mask_expansion, and mask_opening.  An initial binary mask is created
    using a threshold of less than mask_threshold times the maximal probe value. A morphological
    opening of mask_opening pixels is performed to eliminate stray pixels (e.g. from x-rays),
    followed by a dilation of mask_expansion pixels to ensure the entire probe is captured.

    Accepts:
        datacube        (DataCube) a vacuum scan
        mask_threshold  (float) threshold determining mask which zeros values outside of probe
        mask_expansion  (int) number of pixels by which the zeroing mask is expanded to capture
                        the full probe
        mask_opening    (int) size of binary opening used to eliminate stray bright pixels

    Returns:
        probe           (ndarray of shape (datacube.Q_Nx,datacube.Q_Ny)) the average probe
    """
    probe = datacube.data4D[0,0,:,:]
    for n in range(1,datacube.R_N):
        Rx = int(n/datacube.R_Nx)
        Ry = n%datacube.R_Nx
        curr_DP = datacube.data4D[Rx,Ry,:,:]

        xshift,yshift = get_shift(probe, curr_DP)
        curr_DP_shifted = get_shifted_ar(curr_DP, xshift, yshift)
        probe = probe*(n-1)/n + curr_DP_shifted/n

    mask = probe > np.max(probe)*mask_threshold
    mask = binary_opening(mask, iterations=mask_opening)
    mask = binary_dilation(mask, iterations=mask_expansion)

    return probe*mask


def get_average_probe_from_ROI(datacube, *args):
    pass

def get_synthetic_probe(datacube, *args):
    pass




#### Get the probe kernel ####

def get_probe_kernel(probe):
    """
    Creates a convolution kernel from an average probe, by normalizing, then shifting the center of
    the probe to the corners of the array.

    Accepts:
        probe           (ndarray) the diffraction pattern corresponding to the probe over vacuum

    Returns:
        probe_kernel    (ndarray) the convolution kernel corresponding to the probe, in real space
    """
    Q_Nx, Q_Ny = probe.shape

    # Get CoM
    xCoM, yCoM = get_CoM(probe)

    # Normalize
    probe = probe/np.sum(probe)

    # Shift center to corners of array
    probe_kernel = get_shifted_ar(probe, -xCoM, -yCoM)

    return probe_kernel


def get_probe_kernel_subtrgaussian(probe, sigma_probe_scale):
    """
    Creates a convolution kernel from an average probe, subtracting a gaussian from the normalized
    probe such that the kernel integrates to zero, then shifting the center of the probe to the
    array corners.

    Accepts:
        probe              (ndarray) the diffraction pattern corresponding to the probe over vacuum
        sigma_probe_scale  (float) the width of the gaussian to subtract, relative to the standard
                           deviation of the probe

    Returns:
        probe_kernel       (ndarray) the convolution kernel corresponding to the probe
    """
    Q_Nx, Q_Ny = probe.shape

    # Get CoM
    xCoM, yCoM = get_CoM(probe)

    # Get probe size
    qy,qx = np.meshgrid(np.arange(Q_Ny),np.arange(Q_Nx))
    q2 = (qx-xCoM)**2 + (qy-yCoM)**2
    qstd2 = np.sum(q2*probe) / np.sum(probe)

    # Normalize to one, then subtract of normed gaussian, yielding kernel which integrates to zero
    probe_template_norm = probe/np.sum(probe)
    subtr_gaussian = np.exp(-q2 / (2*qstd2*sigma_probe_scale**2))
    subtr_gaussian = subtr_gaussian/np.sum(subtr_gaussian)
    probe_kernel = probe_template_norm - subtr_gaussian

    # Shift center to array corners
    probe_kernel = get_shifted_ar(probe_kernel, -xCoM, -yCoM)

    return probe_kernel


def get_probe_kernel_logistictrench(probe, radius, trenchwidth, blurwidth):
    """
    Creates a convolution kernel from an average probe, subtracting an annular trench about the
    probe such that the kernel integrates to zero, then shifting the center of the probe to the
    array corners.

    Accepts:
        probe           (ndarray) the diffraction pattern corresponding to the probe over vacuum
        radius          (float) the inner radius of the trench, from the probe center
        trenchwidth     (float) the trench annulus width (r_outer - r_inner)
        blurwidth       (float) the full width of the blurring of the trench walls

    Returns:
        probe_kernel    (ndarray) the convolution kernel corresponding to the probe
    """
    Q_Nx, Q_Ny = probe.shape

    # Get CoM
    xCoM, yCoM = get_CoM(probe)

    # Get probe size
    qy,qx = np.meshgrid(np.arange(Q_Ny),np.arange(Q_Nx))
    qr = np.sqrt((qx-xCoM)**2 + (qy-yCoM)**2)
    qr = qr-radius                                        # Shift qr=0 to disk edge

    # Calculate logistic function
    logistic_annulus = 1/(1+np.exp(4*qr/blurwidth)) - 1/(1+np.exp(4*(qr-trenchwidth)/blurwidth))

    # Normalize to one, then subtract off logistic annulus, yielding kernel which integrates to zero
    probe_template_norm = probe/np.sum(probe)
    logistic_annulus_norm = logistic_annulus/np.sum(logistic_annulus)
    probe_kernel = probe_template_norm - logistic_annulus_norm

    # Shift center to array corners
    probe_kernel = get_shifted_ar(probe_kernel, -xCoM, -yCoM)

    return probe_kernel








