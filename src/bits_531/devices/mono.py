"""BL531 monochromator energy pseudo-positioner and calibration offset.

Provides :class:`MonoEnergy` (photon energy in eV <-> Si(111) Bragg angle in
degrees) and :class:`MonoAngleOffset`, a soft signal that carries the runtime
calibration offset into the baseline stream.  The physical constants and the
default calibration offset are copied verbatim from the legacy
``startup_bl531/01_motors.py``.
"""

import numpy as np
from ophyd import Component as Cpt
from ophyd import EpicsMotor
from ophyd import Signal
from ophyd.pseudopos import PseudoPositioner
from ophyd.pseudopos import PseudoSingle
from ophyd.pseudopos import pseudo_position_argument
from ophyd.pseudopos import real_position_argument
from ophyd.signal import AttributeSignal

# ============================================================================
# Physical Constants for Monochromator
# ============================================================================

H_M2KGPS = 6.6261e-34  # Planck constant (J·s)
C_MPS = 299792458  # Speed of light (m/s)
E_EV = 6.2415e18  # Elementary charge (1/eV to J conversion)

# Silicon crystal parameters
SI_M = 5.43e-10  # Si lattice constant (m)
A_SI111_M = SI_M / np.sqrt(3)  # Si(1,1,1) d-spacing (m)
# 19.2567degree at copper edge 8980.3eV
# H_M2KGPS * C_MPS * E_EV/(energies_kev*1000)/(2*A_SI111_M)

# Calibration
# 19.2525
# 19.223 Dec 4, 2025
# 19.16745 - May 14, 2026
# 19.157569
DEFAULT_MONO_OFFSET_DEG = (
    19.157569
    - np.arcsin(H_M2KGPS * C_MPS * E_EV / (8978.8) / (2 * A_SI111_M)) * 180 / np.pi
)  # Default calibration offset


class MonoEnergy(PseudoPositioner):
    """Monochromator energy pseudo positioner.

    Provides energy control (eV) by moving the mono_angle motor (degrees).
    Uses Bragg's law: E = h*c / (2*d*sin(θ)) for Si(111) crystal.

    Real axis:
        mono_angle: Physical monochromator angle in degrees

    Pseudo axis:
        energy_eV: Photon energy in eV

    Example:
        >>> mono.energy_eV.position  # Read current energy
        8930.0
        >>> mono.energy_eV.move(9000)  # Move to 9 keV
    """

    # Pseudo axis - what the user controls
    energy_eV = Cpt(PseudoSingle, limits=(2400, 12000), egu="eV", kind="hinted")

    # Real axis - the physical motor
    mono_angle = Cpt(
        EpicsMotor, "bl531_xps1:mono_angle_deg", labels={"motors"}, kind="normal"
    )

    # Calibration offset (can be changed at runtime)
    offset = Cpt(AttributeSignal, attr="_offset", name="offset")

    def __init__(self, *args, offset=DEFAULT_MONO_OFFSET_DEG, **kwargs):
        """Initialize monochromator energy positioner.

        Args:
            offset: Calibration offset in degrees (default: -18.1361915)
        """
        self._offset = offset
        super().__init__(*args, **kwargs)

    @property
    def _d_spacing(self):
        """Si(111) d-spacing in meters."""
        return A_SI111_M

    @property
    def _hc_factor(self):
        """Constant factor h*c*E_EV for energy calculation."""
        return H_M2KGPS * C_MPS * E_EV

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        """Convert energy (eV) to mono_angle (degrees).

        Bragg's law: θ = arcsin(h*c/(2*d*E))

        Args:
            pseudo_pos: PseudoPosition with .energy_eV attribute (eV)

        Returns:
            RealPosition with .mono_angle attribute (degrees)
        """
        energy_ev = pseudo_pos.energy_eV

        # Calculate angle from energy using Bragg's law
        sin_theta = self._hc_factor / (2 * self._d_spacing * energy_ev)

        # Check if physically possible
        if abs(sin_theta) > 1:
            raise ValueError(
                f"Energy {energy_ev} eV is outside physical range. "
                f"sin(θ) = {sin_theta:.3f} (must be ≤ 1)"
            )

        theta_rad = np.arcsin(sin_theta)
        theta_deg = np.degrees(theta_rad)

        # Apply calibration offset
        mono_angle_deg = theta_deg + self._offset

        return self.RealPosition(mono_angle=mono_angle_deg)

    @real_position_argument
    def inverse(self, real_pos):
        """Convert mono_angle (degrees) to energy (eV).

        Bragg's law: E = h*c / (2*d*sin(θ))

        Handles invalid angles gracefully to prevent subscription errors.

        Args:
            real_pos: RealPosition with .mono_angle attribute (degrees)

        Returns:
            PseudoPosition with .energy_eV attribute (eV)
        """
        mono_angle_deg = real_pos.mono_angle

        # Remove calibration offset
        theta_deg = mono_angle_deg - self._offset
        theta_rad = np.radians(theta_deg)

        sin_theta = np.sin(theta_rad)

        # Handle invalid Bragg angles gracefully
        # Valid Bragg angles need 0 < sin(θ) ≤ 1
        if sin_theta <= 0 or sin_theta > 1:
            # Return fallback value to prevent subscription errors
            return self.PseudoPosition(energy_eV=self.energy_eV.limits[0])

        # Calculate energy from angle using Bragg's law
        energy_ev = self._hc_factor / (2 * self._d_spacing * sin_theta)

        # Clamp to valid energy range
        energy_ev = max(
            self.energy_eV.limits[0], min(energy_ev, self.energy_eV.limits[1])
        )

        return self.PseudoPosition(energy_eV=energy_ev)


class MonoAngleOffset(Signal):
    """Soft signal holding the mono calibration offset (deg).

    Declared in ``devices.yml`` as ``mono_angle_offset`` with the ``baseline``
    label, reproducing the legacy soft signal that recorded the current
    calibration offset in every run's baseline stream.  Defaults to
    :data:`DEFAULT_MONO_OFFSET_DEG` so the value stays tied to the calibration
    formula rather than a hard-coded number in YAML.
    """

    def __init__(self, *args, value=DEFAULT_MONO_OFFSET_DEG, **kwargs):
        """Initialize with the default calibration offset as the value."""
        super().__init__(*args, value=value, **kwargs)
