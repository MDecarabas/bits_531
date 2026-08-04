"""BL531 area detectors: Basler camera and Pilatus 300k / 1M.

Ported from ``startup_bl531/02_area_detectors.py``.  The ``stage_sigs`` and
``read_attrs`` tweaks that the legacy file applied *after* instantiation are
applied here inside each device's ``__init__`` instead, so importing this
module (and letting ``make_devices`` build the objects) has no side effects and
does not require a live IOC.  File paths, PV suffixes, and stage-sig values are
copied verbatim.
"""

import os

from ophyd import ADComponent
from ophyd import CamBase
from ophyd import Component
from ophyd import DetectorBase
from ophyd import EpicsSignal
from ophyd import ImagePlugin
from ophyd import PilatusDetector
from ophyd import SingleTrigger
from ophyd.areadetector.cam import PilatusDetectorCam
from ophyd.areadetector.filestore_mixins import FileStoreTIFFIterativeWrite
from ophyd.areadetector.plugins import TIFFPlugin

PILATUS_FILES_ROOT = "/mnt/data531"
BLUESKY_FILES_ROOT = "/mnt/data531"
BASLER_FILES_ROOT = "/mnt/data531"
BASLER_TEST_IMAGE_DIR = ""


class MyBaslerTIFFPlugin(FileStoreTIFFIterativeWrite, TIFFPlugin):
    """TIFF plugin for the Basler camera (iterative-write filestore)."""


############### Basler Camera Device ################
class BaslerCam(CamBase):
    """Basler camera component."""

    # Defer PV connection: SingleTrigger reads cam.acquire at construction, and
    # the acquire component is created on this cam instance, so the flag must
    # live here (not just on the detector) to avoid blocking with the IOC down.
    lazy_wait_for_connection = False

    # Common camera parameters
    acquire_time = Component(EpicsSignal, "AcquireTime")
    acquire_period = Component(EpicsSignal, "AcquirePeriod")
    num_images = Component(EpicsSignal, "NumImages")
    image_mode = Component(EpicsSignal, "ImageMode")
    trigger_mode = Component(EpicsSignal, "TriggerMode")

    # Basler-specific parameters
    pixel_format = Component(EpicsSignal, "PixelFormat")
    gain = Component(EpicsSignal, "Gain")
    exposure_auto = Component(EpicsSignal, "ExposureAuto")
    gain_auto = Component(EpicsSignal, "GainAuto")


class BaslerDetector(SingleTrigger, DetectorBase):
    """Complete Basler camera detector."""

    # SingleTrigger.__init__ accesses cam.acquire; without this, ophyd blocks on
    # PV connection at construction and make_devices aborts when the IOC is down.
    # guarneri's connect() step connects (or tolerates disconnection) instead.
    lazy_wait_for_connection = False

    cam = Component(BaslerCam, "cam1:")
    image = Component(ImagePlugin, "image1:")
    tiff = ADComponent(
        MyBaslerTIFFPlugin,
        "TIFF1:",
        write_path_template=os.path.join(BASLER_FILES_ROOT, BASLER_TEST_IMAGE_DIR),
        read_path_template=os.path.join(BASLER_FILES_ROOT, BASLER_TEST_IMAGE_DIR),
    )

    def __init__(self, *args, **kwargs):
        """Build the detector and apply staging / read-attr configuration."""
        super().__init__(*args, **kwargs)
        self.cam.stage_sigs["image_mode"] = "Single"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["acquire_time"] = 0.1
        self.cam.stage_sigs["acquire_period"] = 0.105
        self.tiff.stage_sigs["file_template"] = "/%s%s_%3.3d.tif"

        # try to make sure that the file writing part is in read attributes
        # and picked up by tiled writer
        self.read_attrs = ["tiff"]
        self.tiff.read_attrs = []


################# Pilatus Camera Device ################
TEST_IMAGE_DIR = "scans/%Y/%m/%d"


class PilatusTIFFPlugin(FileStoreTIFFIterativeWrite, TIFFPlugin):
    """TIFF filestore plugin for the Pilatus detectors."""

    def __init__(self, *args, root_str="/nsls2/data/smi/proposals", md=None, **kwargs):
        """Initialize the plugin, recording the asset root string."""
        super().__init__(*args, **kwargs)
        self._md = md
        self.__stage_cache = {}
        self._asset_path = ""
        self.root_str = root_str

    def describe(self):
        """Describe the image data key, filling in shape and dtype."""
        ret = super().describe()
        key = self.parent._image_name
        color_mode = self.parent.cam.color_mode.get(as_string=True)
        if color_mode == "Mono":
            ret[key]["shape"] = [
                self.parent.cam.num_images.get(),
                self.array_size.height.get(),
                self.array_size.width.get(),
            ]

        elif color_mode in ["RGB1", "Bayer"]:
            ret[key]["shape"] = [
                self.parent.cam.num_images.get(),
                *self.array_size.get(),
            ]
        else:
            raise RuntimeError("SHould never be here")

        cam_dtype = self.data_type.get(as_string=True)
        type_map = {
            "UInt8": "|u1",
            "UInt16": "<u2",
            "Float32": "<f4",
            "Float64": "<f8",
            "Int32": "<i4",
        }
        if cam_dtype in type_map:
            ret[key].setdefault("dtype_str", type_map[cam_dtype])

        return ret


PILATUS_300K_IMAGE_DIR = "scans/%Y/%m/%d/pilatus300k"
PILATUS_1M_IMAGE_DIR = "scans/%Y/%m/%d/pilatus1M"


class MyPilatusCam(PilatusDetectorCam):
    """Pilatus cam that defers PV connection out of construction."""

    lazy_wait_for_connection = False


class My300kPilatusDetector(SingleTrigger, PilatusDetector):
    """Pilatus 300k detector."""

    # See BaslerDetector: defer PV connection out of construction so
    # make_devices can build this with the IOC down.
    lazy_wait_for_connection = False

    cam = ADComponent(MyPilatusCam, "cam1:")
    image = ADComponent(ImagePlugin, "image1:")
    tiff = ADComponent(
        PilatusTIFFPlugin,
        "TIFF1:",
        write_path_template=os.path.join(PILATUS_FILES_ROOT, PILATUS_300K_IMAGE_DIR),
        read_path_template=os.path.join(BLUESKY_FILES_ROOT, PILATUS_300K_IMAGE_DIR),
    )

    def __init__(self, *args, **kwargs):
        """Build the detector and apply staging / read-attr configuration."""
        super().__init__(*args, **kwargs)
        self.cam.stage_sigs["image_mode"] = "Single"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["acquire_period"] = 0.105
        self.tiff.stage_sigs["file_template"] = "/%s%s_%3.3d.tif"

        # try to make sure that the file writing part is in read attributes
        # and picked up by tiled writer
        self.read_attrs = ["tiff"]
        self.tiff.read_attrs = []


class My1MPilatusDetector(SingleTrigger, PilatusDetector):
    """Pilatus 1M detector."""

    # See BaslerDetector: defer PV connection out of construction so
    # make_devices can build this with the IOC down.
    lazy_wait_for_connection = False

    cam = ADComponent(MyPilatusCam, "cam1:")
    image = ADComponent(ImagePlugin, "image1:")
    tiff = ADComponent(
        PilatusTIFFPlugin,
        "TIFF1:",
        write_path_template=os.path.join(PILATUS_FILES_ROOT, PILATUS_1M_IMAGE_DIR),
        read_path_template=os.path.join(BLUESKY_FILES_ROOT, PILATUS_1M_IMAGE_DIR),
    )

    def __init__(self, *args, **kwargs):
        """Build the detector and apply staging / read-attr configuration."""
        super().__init__(*args, **kwargs)
        self.cam.stage_sigs["image_mode"] = "Single"
        self.cam.stage_sigs["num_images"] = 1
        self.cam.stage_sigs["acquire_period"] = 0.105
        self.tiff.stage_sigs["file_template"] = "/%s%s_%3.3d.tif"

        # try to make sure that the file writing part is in read attributes
        # and picked up by tiled writer
        self.read_attrs = ["tiff"]
        self.tiff.read_attrs = []
