"""
Start Bluesky Data Acquisition sessions of all kinds.

Includes:

* Python script
* IPython console
* Jupyter notebook
* Bluesky queueserver
"""

# Standard Library Imports
import logging
import os
from pathlib import Path

# Core Functions
from apsbits.core.best_effort_init import init_bec_peaks
from apsbits.core.catalog_init import init_catalog
from apsbits.core.instrument_init import init_instrument
from apsbits.core.instrument_init import make_devices
from apsbits.core.run_engine_init import init_RE
from apsbits.core.session_setup import prepare_bits

# Utility functions
from apsbits.utils.baseline_setup import setup_baseline_stream

# Configuration functions
from apsbits.utils.config_loaders import load_config
from apsbits.utils.helper_functions import register_bluesky_magics
from apsbits.utils.helper_functions import running_in_queueserver
from apsbits.utils.logging_setup import configure_logging

# Tiled document writer (stream Bluesky documents to the BL531 Tiled server)
from bluesky_tiled_plugins import TiledWriter
from tiled.client import from_uri

# Run first so we get better diagnostics about subsequent problems
configure_logging()
prepare_bits()

# Configuration block
# Get the path to the instrument package
# Load configuration to be used by the instrument.
instrument_path = Path(__file__).parent
iconfig_path = instrument_path / "configs" / "iconfig.yml"
iconfig = load_config(iconfig_path)

logger = logging.getLogger(__name__)
logger.info("Starting Instrument with iconfig: %s", iconfig_path)

# initialize instrument
instrument, oregistry = init_instrument("guarneri")

# Discard oregistry items loaded above.
oregistry.clear()

# Configure the session with callbacks, devices, and plans.

# Command-line tools, such as %wa, %ct, ...
register_bluesky_magics()

# Bluesky initialization block

bec, peaks = init_bec_peaks(iconfig)
cat = init_catalog(iconfig)
RE, sd = init_RE(iconfig, subscribers=[bec, cat])

# --- BL531 local Tiled writer (ported from startup_bl531/00_base.py) ---
# Stream every run's documents to the BL531 Tiled server.  The URI defaults to
# the beamline's local Tiled and may be overridden (for testing on another host)
# via BL531_TILED_URI; the API key is required via TILED_SINGLE_USER_API_KEY
# (same guard as the legacy startup).
tiled_uri = os.getenv("BL531_TILED_URI", "http://192.168.10.155:8000")
tiled_api_key = os.getenv("TILED_SINGLE_USER_API_KEY")
if not tiled_api_key:
    raise ValueError("TILED_SINGLE_USER_API_KEY environment variable is not set.")
tiled_client = from_uri(tiled_uri, api_key=tiled_api_key)
RE.subscribe(TiledWriter(tiled_client, batch_size=1))

# Per-run access tagging is OFF, matching the current legacy runtime (the tag is
# commented out in 00_base.py).  The modern TiledWriter reads `tiled_access_tags`
# from the start document, so BL531 access control can be enabled with one line:
#     RE.md["tiled_access_tags"] = ["5.3.1"]
#
# The central ALS Tiled writer is likewise left off (parity with 00_base.py; the
# legacy CENTRAL_API_KEY requirement is intentionally NOT ported since the writer
# it guarded is disabled).  To enable it, patch resource paths and subscribe a
# second writer:
#     LOCAL_PATH_PREFIX = "mnt/data531"
#     CENTRAL_PATH_PREFIX = "/global/beegfs/beamlines/bl531/raw"
#     def patch_ride_filenames(doc):
#         rp = doc.get("resource_path", "")
#         if rp.startswith(LOCAL_PATH_PREFIX):
#             doc["resource_path"] = os.path.join(
#                 CENTRAL_PATH_PREFIX, rp[len(LOCAL_PATH_PREFIX) :].lstrip("/")
#             )
#         return doc
#     central_client = from_uri(
#         "https://tiled.computing.als.lbl.gov/api/v1/metadata/beamlines/bl531/raw",
#         api_key=os.getenv("CENTRAL_API_KEY"),
#     )
#     RE.subscribe(
#         TiledWriter(
#             central_client, batch_size=1, patches={"resource": patch_ride_filenames}
#         )
#     )

# Optional Nexus callback block
# delete this block if not using Nexus
if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    from .callbacks.demo_nexus_callback import nxwriter_init

    nxwriter = nxwriter_init(RE, iconfig)

# Optional SPEC callback block
# delete this block if not using SPEC
if iconfig.get("SPEC_DATA_FILES", {}).get("ENABLE", False):
    from .callbacks.demo_spec_callback import init_specwriter_with_RE
    from .callbacks.demo_spec_callback import newSpecFile  # noqa: F401
    from .callbacks.demo_spec_callback import spec_comment  # noqa: F401

    specwriter = init_specwriter_with_RE(RE, iconfig)  # noqa: F811

# These imports must come after the above setup.
# Queue server block
if running_in_queueserver():
    ### To make all the standard plans available in QS, import by '*', otherwise import
    ### plan by plan.
    from apstools.plans import lineup2  # noqa: F401
    from bluesky.plans import *  # noqa: F403
else:
    # Import bluesky plans and stubs with prefixes set by common conventions.
    # The apstools plans and utils are imported by '*'.
    from apstools.plans import *  # noqa: F403
    from apstools.utils import *  # noqa: F403
    from bluesky import plan_stubs as bps  # noqa: F401
    from bluesky import plans as bp  # noqa: F401

# Experiment specific logic, device and plan loading. # Create the devices.
# BL531 devices are split by category, mirroring the legacy startup_bl531/ files
# (01_motors, 02_area_detectors, 03_fluorescent_detectors); devices.yml holds the
# simulated devices used by the sim plans.  clear=False accumulates across files.
make_devices(clear=False, file="devices.yml", device_manager=instrument)
make_devices(clear=False, file="devices_motors.yml", device_manager=instrument)
make_devices(clear=False, file="devices_area_detectors.yml", device_manager=instrument)
make_devices(
    clear=False, file="devices_fluorescent_detectors.yml", device_manager=instrument
)

# Setup baseline stream with connect=False is default
# Devices with the label 'baseline' will be added to the baseline stream.
setup_baseline_stream(sd, oregistry, connect=False)

# BL531 plans (ported from startup_bl531/*.py).  Imported by name so the
# queueserver registers them; these override any same-named bluesky.plans
# imports so the finch UI gets the annotated BL531 versions.
from .plans.gisaxs import automatic_diode_alignment  # noqa: E402, F401
from .plans.gisaxs import automatic_gisaxs_alignment  # noqa: E402, F401
from .plans.gisaxs import gisaxs_height_scan  # noqa: E402, F401
from .plans.gisaxs import gisaxs_th_scan  # noqa: E402, F401
from .plans.scans import angle_scan  # noqa: E402, F401
from .plans.scans import energy_scan  # noqa: E402, F401
from .plans.scans import energy_scan_ui  # noqa: E402, F401
from .plans.scans import grid_scan  # noqa: E402, F401
from .plans.scans import rel_scan  # noqa: E402, F401
from .plans.scans import scan  # noqa: E402, F401
from .plans.sim_plans import sim_count_plan  # noqa: E402, F401
from .plans.sim_plans import sim_print_plan  # noqa: E402, F401
from .plans.sim_plans import sim_rel_scan_plan  # noqa: E402, F401
from .plans.xas import xas_scan  # noqa: E402, F401
