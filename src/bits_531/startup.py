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

#bluesky imports
import ophyd

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

api_key = os.getenv("TILED_SINGLE_USER_API_KEY")
if not api_key:
    raise ValueError("TILED_SINGLE_USER_API_KEY environment variable is not set.")
tiled_client = from_uri("http://192.168.10.155:8000", api_key=api_key)
tw = TiledWriter(tiled_client, batch_size=1)
RE.subscribe(tw)

# --- BL531 Tiled writer ---
# Configured via configs/iconfig.yml (TILED_PROFILE_NAME: bl531) + the tiled
# profile in configs/tiled_profiles/bl531.yml + the TILED_API_KEY env var:
# init_catalog() above returned the Tiled client as `cat`, and init_RE() wrapped
# it in a TiledWriter(batch_size=1) and subscribed it -- so nothing to construct
# here.  Per-run access tagging stays OFF (legacy parity); enable it with
# RE.md["tiled_access_tags"] = ["5.3.1"] or via RUN_ENGINE.DEFAULT_METADATA in
# iconfig.  A second (central ALS) writer can't be expressed through init_catalog
# and would need an explicit RE.subscribe(TiledWriter(...)) here.

# Optional Nexus callback block
# delete this block if not using Nexus
if iconfig.get("NEXUS_DATA_FILES", {}).get("ENABLE", False):
    from .callbacks.demo_nexus_callback import nxwriter_init

    nxwriter = nxwriter_init(RE, iconfig)

# These imports must come after the above setup.
# Queue server block
if running_in_queueserver():
    ### To make all the standard plans available in QS, import by '*', otherwise import
    ### plan by plan.
    # from bluesky.plans import *  # noqa: F403
    # diode = ophyd.EpicsSignal('bl201-beamstop:current', name='diode')



    from bluesky.plans import adaptive_scan as _adaptive_scan  # noqa: F401
    from bluesky.plans import count  # noqa: F401
    from bluesky.plans import fly as _fly  # noqa: F401
    from bluesky.plans import grid_scan as _grid_scan  # noqa: F401
    from bluesky.plans import inner_product_scan as _inner_product_scan  # noqa: F401
    from bluesky.plans import list_grid_scan as _list_grid_scan  # noqa: F401
    from bluesky.plans import list_scan as _list_scan  # noqa: F401
    from bluesky.plans import log_scan as _log_scan  # noqa: F401
    from bluesky.plans import ramp_plan as _ramp_plan  # noqa: F401
    from bluesky.plans import rel_adaptive_scan as _rel_adaptive_scan  # noqa: F401
    from bluesky.plans import rel_grid_scan as _rel_grid_scan  # noqa: F401
    from bluesky.plans import rel_list_grid_scan as _rel_list_grid_scan  # noqa: F401
    from bluesky.plans import rel_list_scan as _rel_list_scan  # noqa: F401
    from bluesky.plans import rel_log_scan as _rel_log_scan  # noqa: F401
    from bluesky.plans import rel_scan as _rel_scan  # noqa: F401
    from bluesky.plans import rel_spiral as _rel_spiral  # noqa: F401
    from bluesky.plans import rel_spiral_fermat as _rel_spiral_fermat  # noqa: F401
    from bluesky.plans import rel_spiral_square as _rel_spiral_square  # noqa: F401
    from bluesky.plans import (
        relative_inner_product_scan as _relative_inner_product_scan,  # noqa: F401
    )
    from bluesky.plans import scan as _scan  # noqa: F401
    from bluesky.plans import scan_nd as _scan_nd  # noqa: F401
    from bluesky.plans import spiral as _spiral  # noqa: F401
    from bluesky.plans import spiral_fermat as spiral_fermat  # noqa: F401
    from bluesky.plans import spiral_square as _spiral_square  # noqa: F401
    from bluesky.plans import tune_centroid as _tune_centroid  # noqa: F401
    from bluesky.plans import tweak as _tweak  # noqa: F401
    from bluesky.plans import x2x_scan as _x2x_scan  # noqa: F401

else:
    # Import bluesky plans and stubs with prefixes set by common conventions.
    from apstools.utils import *
    from bluesky import plan_stubs as bps  # noqa: F401
    from bluesky import plans as bp  # noqa: F401

# Experiment specific logic, device and plan loading. # Create the devices.
# BL531 devices are split by category, mirroring the legacy startup_bl531/ files
# (01_motors, 02_area_detectors, 03_fluorescent_detectors); devices.yml holds the
# simulated devices used by the sim plans.  clear=False accumulates across files.
make_devices(clear=False, file="devices.yml", device_manager=instrument)
make_devices(clear=False, file="devices_motors.yml", device_manager=instrument)
# make_devices(clear=False, file="devices_area_detectors.yml", device_manager=instrument)
# make_devices(
#     clear=False, file="devices_fluorescent_detectors.yml", device_manager=instrument
# )
# diode_two = ophyd.EpicsSignal('bl201-beamstop:current', name='diode')
# Setup baseline stream with connect=False is default
# Devices with the label 'baseline' will be added to the baseline stream.
setup_baseline_stream(sd, oregistry, connect=True)

# BL531 plans (ported from startup_bl531/*.py).  Imported by name so the
# queueserver registers them; these override any same-named bluesky.plans
# imports so the finch UI gets the annotated BL531 versions.
# from .plans.gisaxs import automatic_diode_alignment  # noqa: E402, F401
# from .plans.gisaxs import automatic_gisaxs_alignment  # noqa: E402, F401
# from .plans.gisaxs import gisaxs_height_scan  # noqa: E402, F401
# from .plans.gisaxs import gisaxs_th_scan  # noqa: E402, F401
# from .plans.scans import angle_scan  # noqa: E402, F401
# from .plans.scans import energy_scan  # noqa: E402, F401
# from .plans.scans import energy_scan_ui  # noqa: E402, F401
# from .plans.scans import grid_scan  # noqa: E402, F401
# from .plans.scans import rel_scan  # noqa: E402, F401
# from .plans.scans import scan  # noqa: E402, F401
from .plans.sim_plans import sim_count_plan  # noqa: E402, F401
from .plans.sim_plans import sim_print_plan  # noqa: E402, F401
from .plans.sim_plans import sim_rel_scan_plan  # noqa: E402, F401
# from .plans.xas import xas_scan  # noqa: E402, F401
