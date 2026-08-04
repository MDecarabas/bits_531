"""BL531 hexapod axis positioners.

Six single-axis :class:`~ophyd.PVPositioner` wrappers around the SmarAct/
Symetrie hexapod (``SYM:HEX01:...``).  Each axis drives one component of the
``MOVE_PTP`` point-to-point move and reads back the corresponding ``s_uto_*``
readback, sharing the hexapod's ``InPosition_RBV`` done flag and ``MOVE_PTP``
"GO" actuator.  Full PVs are baked into the components, so these are declared
with an empty ``prefix`` in ``configs/devices.yml``.
"""

from ophyd import Component as Cpt
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
from ophyd import PVPositioner


class HexapodAxisTz(PVPositioner):
    """Hexapod vertical (Z) axis positioner."""

    # Target position
    setpoint = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP:Tz")
    # Readback position
    readback = Cpt(EpicsSignalRO, "SYM:HEX01:s_uto_tz_RBV")
    # Done status (True when in position / stopped)
    done = Cpt(EpicsSignalRO, "SYM:HEX01:s_hexa:InPosition_RBV")
    # Execution PV ("GO" button)
    actuate = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP")

    # Actuation signal ("GO" button)
    actuate_value = 1  # Value to start motion


class HexapodAxisTy(PVPositioner):
    """Hexapod lateral (Y) axis positioner."""

    # Target position
    setpoint = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP:Ty")
    # Readback position
    readback = Cpt(EpicsSignalRO, "SYM:HEX01:s_uto_ty_RBV")
    # Done status (True when in position / stopped)
    done = Cpt(EpicsSignalRO, "SYM:HEX01:s_hexa:InPosition_RBV")
    # Execution PV ("GO" button)
    actuate = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP")

    # Actuation signal ("GO" button)
    actuate_value = 1  # Value to start motion


class HexapodAxisTx(PVPositioner):
    """Hexapod lateral (X) axis positioner."""

    # Target position
    setpoint = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP:Tx")
    # Readback position
    readback = Cpt(EpicsSignalRO, "SYM:HEX01:s_uto_tx_RBV")
    # Done status (True when in position / stopped)
    done = Cpt(EpicsSignalRO, "SYM:HEX01:s_hexa:InPosition_RBV")
    # Execution PV ("GO" button)
    actuate = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP")

    # Actuation signal ("GO" button)
    actuate_value = 1  # Value to start motion


class HexapodAxisRz(PVPositioner):
    """Hexapod rotation (Rz) axis positioner - used for vertical rotation."""

    # Target position
    setpoint = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP:Rz")
    # Readback position
    readback = Cpt(EpicsSignalRO, "SYM:HEX01:s_uto_rz_RBV")
    # Done status (True when in position / stopped)
    done = Cpt(EpicsSignalRO, "SYM:HEX01:s_hexa:InPosition_RBV")
    # Execution PV ("GO" button)
    actuate = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP")

    # Actuation signal ("GO" button)
    actuate_value = 1  # Value to start motion


class HexapodAxisRy(PVPositioner):
    """Hexapod rotation (Ry) axis positioner - used for grazing incidence angle."""

    # Target position
    setpoint = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP:Ry")
    # Readback position
    readback = Cpt(EpicsSignalRO, "SYM:HEX01:s_uto_ry_RBV")
    # Done status (True when in position / stopped)
    done = Cpt(EpicsSignalRO, "SYM:HEX01:s_hexa:InPosition_RBV")
    # Execution PV ("GO" button)
    actuate = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP")

    # Actuation signal ("GO" button)
    actuate_value = 1  # Value to start motion


class HexapodAxisRx(PVPositioner):
    """Hexapod rotation (Rx) axis positioner - used for tilting."""

    # Target position
    setpoint = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP:Rx")
    # Readback position
    readback = Cpt(EpicsSignalRO, "SYM:HEX01:s_uto_rx_RBV")
    # Done status (True when in position / stopped)
    done = Cpt(EpicsSignalRO, "SYM:HEX01:s_hexa:InPosition_RBV")
    # Execution PV ("GO" button)
    actuate = Cpt(EpicsSignal, "SYM:HEX01:MOVE_PTP")

    # Actuation signal ("GO" button)
    actuate_value = 1  # Value to start motion
