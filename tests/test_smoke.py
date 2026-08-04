"""Smoke tests for the bits_531 BITS instrument package.

The device/plan-structure tests run with no hardware or Tiled server.  The full
``startup`` import (which subscribes a live ``TiledWriter``) is marked to skip
unless a Tiled server is configured via ``BL531_TILED_URI`` +
``TILED_SINGLE_USER_API_KEY``.
"""

import os

import pytest


def test_device_modules_import():
    """Device modules import with no side effects; mono Bragg math works."""
    import bits_531.devices  # noqa: F401
    from bits_531.devices.mono import MonoEnergy
    from bits_531.devices.motors import HexapodAxisRy  # noqa: F401

    mono = MonoEnergy("", name="mono")
    angle = mono.forward(mono.PseudoPosition(energy_eV=8978.8)).mono_angle
    assert 19.0 < angle < 19.3


def test_scan_plan_message_sequence():
    """energy_scan yields a valid message sequence against a sim detector."""
    from ophyd.sim import det

    from bits_531.devices.mono import MonoEnergy
    from bits_531.plans.scans import energy_scan

    mono = MonoEnergy("", name="mono")
    msgs = list(energy_scan([det], mono, 7000.0, 7005.0, 5))
    commands = {msg.command for msg in msgs}
    assert {"open_run", "close_run", "set", "trigger", "read"} <= commands


def test_gisaxs_imports_without_network():
    """Importing the gisaxs plans makes no network connection at import."""
    import bits_531.plans.gisaxs as gisaxs

    assert gisaxs._tiled_client is None


@pytest.mark.skipif(
    not (os.getenv("BL531_TILED_URI") and os.getenv("TILED_SINGLE_USER_API_KEY")),
    reason="startup subscribes a live TiledWriter; needs BL531_TILED_URI + "
    "TILED_SINGLE_USER_API_KEY pointing at a reachable Tiled server",
)
def test_startup_imports_and_sim_count_runs():
    """Full startup imports and sim_count_plan runs end-to-end."""
    from bits_531.startup import RE
    from bits_531.startup import sd
    from bits_531.startup import sim_count_plan

    # Bypass the real-device baseline (disconnected without IOCs).
    sd.baseline.clear()
    (uid,) = RE(sim_count_plan())
    assert isinstance(uid, str)
