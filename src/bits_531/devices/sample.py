"""BL531 sample-stage devices.

Grazing-incidence angle pseudo-positioner (wraps the hexapod Ry axis), the
LabJack-driven :class:`Shutter`, and the :class:`SampleDetectorDistance` soft
device.  Ported verbatim from ``startup_bl531/01_motors.py``;
``SampleDetectorDistance`` is defined here but not declared in
``configs/devices.yml`` because no active plan uses it yet.
"""

from ophyd import Component as Cpt
from ophyd import Device
from ophyd import EpicsSignal
from ophyd import Signal
from ophyd.pseudopos import PseudoPositioner
from ophyd.pseudopos import PseudoSingle
from ophyd.pseudopos import pseudo_position_argument
from ophyd.pseudopos import real_position_argument

from .motors import HexapodAxisRy

# ============================================================================
# Grazing Incidence Angle Pseudo Positioner
# ============================================================================


class GrazingIncidenceAngle(PseudoPositioner):
    """Pseudo motor for grazing incidence angle.

    This provides a user-friendly grazing angle coordinate system where:
    - grazing_angle = 0 corresponds to the reference angle (ref_angle)
    - Positive grazing_angle tilts sample toward beam
    - Negative grazing_angle tilts sample away from beam

    Relationship: Ry_physical = ref_angle + grazing_angle

    Example:
        If ref_angle = 0.12 degrees:
        - grazing_angle = 0.0  → Ry = 0.12 (at reference)
        - grazing_angle = 0.05 → Ry = 0.17 (tilted toward beam)
        - grazing_angle = -0.02 → Ry = 0.10 (tilted away)

    Usage:
        >>> gi_angle.grazing_angle.move(0.05)  # Move +0.05° from reference
        >>> gi_angle.set_reference_angle(0.15) # Update reference after alignment
    """

    # Pseudo axis (what user sees/controls)
    grazing_angle = Cpt(PseudoSingle, limits=(-1.0, 1.0), kind="hinted", egu="deg")

    # Real axis (physical motor)
    hexapod_ry = Cpt(HexapodAxisRy, "", kind="normal")

    # Reference angle (stored as attribute, can be updated)
    def __init__(self, *args, ref_angle=-0.7731, **kwargs):
        """Initialize grazing incidence angle positioner.

        Args:
            ref_angle: Reference angle in degrees (default: 0.0)
                      This is typically set after alignment
        """
        self.ref_angle = ref_angle
        super().__init__(*args, **kwargs)

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        """Convert pseudo (grazing angle) to real (Ry physical).

        User requests grazing_angle → calculate Ry_physical
        """
        ry_physical = self.ref_angle + pseudo_pos.grazing_angle
        return self.RealPosition(hexapod_ry=ry_physical)

    @real_position_argument
    def inverse(self, real_pos):
        """Convert real (Ry physical) to pseudo (grazing angle).

        Ry_physical readback → calculate grazing_angle
        """
        grazing = real_pos.hexapod_ry - self.ref_angle
        return self.PseudoPosition(grazing_angle=grazing)

    def set_reference_angle(self, new_ref_angle):
        """Update the reference angle (e.g., after alignment).

        Args:
            new_ref_angle: New reference angle in degrees
        """
        old_ref = self.ref_angle
        self.ref_angle = new_ref_angle
        print(f"Reference angle updated: {old_ref:.4f}° → {new_ref_angle:.4f}°")
        print(f"Current grazing angle: {self.grazing_angle.position:.4f}°")


# ============================================================================
# Shutter device
# ============================================================================


class Shutter(Device):
    """Shutter controlled by LabJack analog output.

    5V = closed, 0V = open. No readback available.
    """

    # The actual PV that controls the shutter
    _control = Cpt(EpicsSignal, "AO0", kind="config")

    # A simulated readback that tracks the last set value
    # since there's no real RBV
    state = Cpt(Signal, value="Unknown", kind="hinted")

    def __init__(self, *args, **kwargs):
        """Initialize the shutter and mark its state as unknown."""
        super().__init__(*args, **kwargs)
        # Set initial state as unknown
        self.state.put("Unknown")

    def open(self):
        """Open the shutter (0V)."""
        self._control.put(0)
        self.state.put("Open")
        print(f"{self.name}: Shutter opened (0V)")

    def close(self):
        """Close the shutter (5V)."""
        self._control.put(5)
        self.state.put("Closed")
        print(f"{self.name}: Shutter closed (5V)")

    def set(self, value):
        """Set shutter state.

        Accepts: 'open', 'Open', 0, 'close', 'Closed', 5
        """
        if value in ["open", "Open", 0]:
            self.open()
        elif value in ["close", "Closed", 5]:
            self.close()
        else:
            raise ValueError(
                f"Invalid shutter command: {value}. Use 'open', 'close', 0, or 5"
            )

        # Return a status object for bluesky compatibility
        from ophyd.status import Status

        st = Status()
        st.set_finished()
        return st

    def read(self):
        """Read the simulated state."""
        return self.state.read()

    def describe(self):
        """Describe the simulated state."""
        return self.state.describe()


# ============================================================================
# Sample-Detector Distance Pseudo Positioner
# ============================================================================


class SampleDetectorDistance(Device):
    """Pseudo positioner for sample-detector distance.

    This is a simple settable/readable signal that stores the distance
    between the sample and detector. Useful for metadata and calibration.

    Usage:
        >>> sdd.distance.put(150.0)  # Set distance to 150 mm
        >>> sdd.distance.get()       # Read current distance
        150.0
        >>> sdd.set(200.0)           # Alternative: set via Device interface
    """

    # Main signal for distance
    distance = Cpt(Signal, value=1500.0, kind="hinted")

    def __init__(self, *args, initial_distance=1500.0, **kwargs):
        """Initialize sample-detector distance.

        Args:
            initial_distance: Initial distance value in mm (default: 1500.0)
        """
        super().__init__(*args, **kwargs)
        self.distance.put(initial_distance)

    def set(self, value):
        """Set the sample-detector distance.

        Args:
            value: Distance in mm

        Returns:
            Status object for bluesky compatibility
        """
        self.distance.put(value)
        print(f"{self.name}: Sample-detector distance set to {value:.2f} mm")

        from ophyd.status import Status

        st = Status()
        st.set_finished()
        return st

    def get(self):
        """Get the current sample-detector distance."""
        return self.distance.get()

    def read(self):
        """Read the distance (for bluesky)."""
        return self.distance.read()

    def describe(self):
        """Describe the distance signal (for bluesky)."""
        return self.distance.describe()
