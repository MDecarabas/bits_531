"""BL531 fluorescence detector: Amptek Silicon Drift Detector (SDD).

Ported from ``startup_bl531/03_fluorescent_detectors.py``.  The legacy module's
import-time side effects (``amptek_fluo.get()`` which triggered a real
acquisition, the diagnostic ``print(...)`` calls, and ``set_exposure``/
``set_roi``) are removed: ROI is set from constructor kwargs and the 1 s preset
exposure is expressed as a ``stage_sigs`` entry so it is applied at acquisition
time rather than on import.  ``MercuryDetector`` is intentionally excluded -- it
is a plain Python class (not an ophyd ``Device``) and no active plan uses it.
"""

import threading
import time

import numpy as np
from ophyd import Component as Cpt
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import Signal
from ophyd.status import DeviceStatus


# ============================================================================
# Fluorescent Detector for XAS
# ============================================================================
class SiliconDriftDetector(Device):
    """Ophyd device for an Amptek Silicon Drift Detector via an EPICS MCA record.

    The full spectrum is stored internally and retrievable via spectrum().
    Only the integrated count within the configured ROI (roi_sum) is sent
    to the bluesky run-engine and the tiled data server.

    Parameters
    ----------
    prefix : str
        EPICS PV prefix for the MCA record, e.g. 'mcaTest:mca1'.
        Note: the EraseStart PV must live at {prefix}EraseStart (no dot).
    roi_low : int, optional
        First channel of the ROI, inclusive. Default 1800.
    roi_high : int, optional
        Last channel of the ROI, exclusive. Default 2750.
    name : str
        Ophyd device name (required keyword argument).

    Examples
    --------
    >>> sdd = SiliconDriftDetector('mcaTest:mca1', name='sdd',
    ...                            roi_low=1800, roi_high=2750)
    >>> sdd.set_exposure(0.1)
    >>> sdd.set_roi(1800, 2750)
    >>> sdd.get()           # triggers acquisition, returns ROI sum as float
    42315.0
    >>> sdd.spectrum()      # numpy array of the last acquired spectrum
    """

    # ------------------------------------------------------------------
    # EPICS PV components
    # 'mcaTest:mca1' + '.PRTM' → 'mcaTest:mca1.PRTM'
    # 'mcaTest:mca1' + 'EraseStart' → 'mcaTest:mca1EraseStart'  (no dot!)
    # ------------------------------------------------------------------
    exposure_time = Cpt(
        EpicsSignal,
        ".PRTM",
        kind="config",
        doc="Preset real time (exposure) in seconds.",
    )
    acquiring = Cpt(
        EpicsSignalRO,
        ".ACQG",
        kind="omitted",
        doc="1 while acquiring, 0 when idle.",
    )
    _spectrum_pv = Cpt(
        EpicsSignalRO,
        ".VAL",
        kind="omitted",
        doc="Raw MCA spectrum array.",
    )
    _erase_start = Cpt(
        EpicsSignal,
        "EraseStart",
        kind="omitted",
        doc="Write 1 to erase memory and begin acquisition.",
    )

    # ------------------------------------------------------------------
    # Soft (Python-side) configuration signals — no EPICS PV backing
    # ------------------------------------------------------------------
    roi_low = Cpt(
        Signal,
        value=1800,
        kind="config",
        doc="First channel of ROI, inclusive.",
    )
    roi_high = Cpt(
        Signal,
        value=2750,
        kind="config",
        doc="Last channel of ROI, exclusive.",
    )

    # ------------------------------------------------------------------
    # Primary readable — the only field tiled / bluesky will record
    # ------------------------------------------------------------------
    roi_sum = Cpt(
        Signal,
        value=0.0,
        kind="hinted",
        doc="Integrated photon counts within [roi_low, roi_high).",
    )

    # ------------------------------------------------------------------

    def __init__(self, *args, roi_low=1800, roi_high=2750, **kwargs):
        """Initialize the detector, set the ROI, and default exposure to 1 s.

        The legacy module set a 1 s preset exposure once at import time; here
        it is a ``stage_sigs`` entry so the write happens when the RunEngine
        stages the detector (no EPICS write on import / device creation).
        """
        super().__init__(*args, **kwargs)
        self._latest_spectrum = None  # populated on first acquisition
        self.roi_low.put(roi_low)
        self.roi_high.put(roi_high)
        # Legacy: amptek_fluo.set_exposure(1) at module scope -> applied at stage.
        self.stage_sigs["exposure_time"] = 1.0

    # ══════════════════════════════════════════════════════════════════
    # Bluesky / tiled interface
    # ══════════════════════════════════════════════════════════════════

    def trigger(self):
        """Erase detector, acquire for exposure_time seconds, update roi_sum.

        The bluesky run-engine calls trigger() automatically before read().
        Returns a DeviceStatus that resolves when acquisition is complete.
        """
        status = DeviceStatus(self)

        def _acquire():
            try:
                # Erase memory and start acquisition
                self._erase_start.put(1, wait=True)
                time.sleep(0.05)  # let ACQG assert

                # Poll until the detector goes idle
                while self.acquiring.get() == 1:
                    time.sleep(0.05)

                # Grab the spectrum and compute the ROI integral
                spec = np.asarray(self._spectrum_pv.get())
                self._latest_spectrum = spec

                lo = int(self.roi_low.get())
                hi = int(self.roi_high.get())
                self.roi_sum.put(float(np.sum(spec[lo:hi])))

                status._finished()  # signal completion
            except Exception:
                status._finished(success=False)

        threading.Thread(target=_acquire, daemon=True).start()
        return status

    # read() and describe() are inherited from Device and work automatically:
    #   sdd.read()   → {'sdd_roi_sum': {'value': ..., 'timestamp': ...}}
    #   sdd.hints    → {'fields': ['sdd_roi_sum']}

    # ══════════════════════════════════════════════════════════════════
    # User-facing convenience API
    # ══════════════════════════════════════════════════════════════════

    def get(self):
        """Trigger a fresh acquisition and return the ROI sum as a single float.

        Blocks until acquisition is complete.

        Returns
        -------
        float
            Sum of photon counts in [roi_low, roi_high).
        """
        self.trigger().wait()
        return float(self.roi_sum.get())

    def spectrum(self):
        """Return the most recently acquired spectrum as a numpy array.

        If trigger() / get() has never been called, reads the hardware
        buffer directly without starting a new acquisition.

        Returns
        -------
        numpy.ndarray, shape (n_channels,)
        """
        if self._latest_spectrum is None:
            self._latest_spectrum = np.asarray(self._spectrum_pv.get())
        return self._latest_spectrum

    def set_roi(self, low: int, high: int):
        """Configure the integration window.

        Parameters
        ----------
        low : int   First channel, inclusive.
        high : int  First channel to exclude.
        """
        self.roi_low.put(low)
        self.roi_high.put(high)
        print(f"ROI set → channels [{low}, {high})  ({high - low} channels)")

    def set_exposure(self, seconds: float):
        """Set the detector preset real-time (exposure duration).

        Parameters
        ----------
        seconds : float
        """
        self.exposure_time.put(float(seconds), wait=True)
        print(f"Exposure time → {seconds} s")

    def __repr__(self):
        """Return a human-readable summary of the detector state."""
        try:
            return (
                f"SiliconDriftDetector(prefix={self.prefix!r}, "
                f"name={self.name!r})\n"
                f"  exposure : {self.exposure_time.get():.3f} s\n"
                f"  roi      : [{int(self.roi_low.get())}, "
                f"{int(self.roi_high.get())})\n"
                f"  roi_sum  : {self.roi_sum.get():.0f} counts"
            )
        except Exception:
            return f"SiliconDriftDetector(prefix={self.prefix!r}, name={self.name!r})"
