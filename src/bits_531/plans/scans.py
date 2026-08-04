"""BL531 standard scan plans (ported from ``startup_bl531/15_plans.py``).

These plans receive their detectors and motors as parameters (the queueserver
converts device names via ``convert_device_names``), so they carry no
module-global device references.  Every ``@parameter_annotation_decorator`` is
preserved verbatim so the finch UI keeps its min/max/step annotations.
"""
# ruff: noqa: E501  -- verbatim UI annotation description strings exceed 88 cols

from bluesky.plans import grid_scan as _grid_scan
from bluesky.plans import rel_scan as _rel_scan
from bluesky.plans import scan as _scan
from bluesky_queueserver.manager.annotation_decorator import (
    parameter_annotation_decorator,
)


# 2D grid scan for spectroscopy
@parameter_annotation_decorator(
    {
        "description": "Scan over a 2d grid to perform spectroscopy",
        "parameters": {
            "detectors": {
                "description": "Required. List of detectors",
                "annotation": "typing.List[str]",
                "convert_device_names": True,
            },
            "motor1": {
                "description": "Required. First inidividual motor that is moved between the start and stop positions.",
                "annotation": "typing.Any",
                "convert_device_names": True,
            },
            "motor1_start": {
                "description": "Required. The start position for motor #1, uses the default units of the motor",
                "default": 0.0,
                "min": 0,
                "max": 20,
                "step": 0.1,
            },
            "motor1_stop": {
                "description": "Required. The stop position for motor #1, uses the default units of the motor",
                "default": 20.0,
                "min": 0,
                "max": 20,
                "step": 0.1,
            },
            "motor1_num": {
                "description": "Required. The number of points that motor #1 will stop at between the start and stop.",
                "default": 10,
                "min": 0,
                "max": 30,
                "step": 1,
            },
            "motor2": {
                "description": "Required. Second inidividual motor that is moved between the start and stop positions.",
                "annotation": "typing.Any",
                "convert_device_names": True,
            },
            "motor2_start": {
                "description": "Required. The start position for motor #2, uses the default units of the motor",
                "default": 0.0,
                "min": 0,
                "max": 20,
                "step": 0.1,
            },
            "motor2_stop": {
                "description": "Required. The stop position for motor #2, uses the default units of the motor",
                "default": 20.0,
                "min": 0,
                "max": 20,
                "step": 0.1,
            },
            "motor2_num": {
                "description": "Required. The number of points that motor #2 will stop at between the start and stop.",
                "default": 10,
                "min": 0,
                "max": 30,
                "step": 1,
            },
            "snake_axes": {
                "description": "Optional boolean. Should the motors follow a snake pattern when moving through the selected locations? Default=True",
                "annotation": "bool",
                "default": True,
            },
        },
    }
)
def grid_scan(
    detectors,
    motor1,
    motor2,
    motor1_start: float = 0.0,
    motor2_start: float = 0.0,
    motor1_stop: float = 20.0,
    motor2_stop: float = 20.0,
    motor1_num: int = 10,
    motor2_num: int = 10,
    snake_axes: bool = False,
    *,
    md: dict = None,
):
    """Scan over a 2D grid to perform spectroscopy."""
    yield from _grid_scan(
        detectors,
        motor1,
        motor1_start,
        motor1_stop,
        motor1_num,
        motor2,
        motor2_start,
        motor2_stop,
        motor2_num,
        snake_axes,
        md=md,
    )


# 1D scan for endstation x, z or filters
@parameter_annotation_decorator(
    {
        "description": "Scan over one multi-motor trajectory.",
        "parameters": {
            "detectors": {
                "description": "Required. List of detectors",
                "annotation": "typing.List[str]",
                "convert_device_names": True,
            },
            "motor": {
                "description": "Required. Inidividual motor that is moved between the start and stop positions.",
                "annotation": "typing.Any",
                "convert_device_names": True,
            },
            "start": {
                "description": "Required. The start position for the motor, uses the default units of the motor",
                "default": 0.0,
                "min": -10000,
                "max": 12000,
                "step": 0.1,
            },
            "stop": {
                "description": "Required. The stop position for the motor, uses the default units of the motor",
                "default": 0.0,
                "min": -10000,
                "max": 12000,
                "step": 0.1,
            },
            "num": {
                "description": "Required. The number of points that motor will stop at between the start and stop.",
                "default": 10,
                "min": 0,
                "max": 401,
                "step": 1,
            },
        },
    }
)
def scan(
    detectors,
    motor,
    start: float = 0.0,
    stop: float = 0.0,
    num: int = 10,
    *,
    md: dict = None,
):
    """Scan a single motor over one trajectory."""
    yield from _scan(detectors, motor, start, stop, num, md=md)


# 1D energy scan
@parameter_annotation_decorator(
    {
        "description": "Scan over one multi-motor trajectory.",
        "parameters": {
            "detectors": {
                "description": "Required. List of detectors",
                "annotation": "typing.List[str]",
                "convert_device_names": True,
            },
            "motor": {
                "description": "Required. Inidividual motor that is moved between the start and stop positions.",
                "annotation": "typing.Any",
                "convert_device_names": True,
            },
            "start": {
                "description": "Required. The start position for the motor, uses the default units of the motor",
                "default": 0.0,
                "min": -10000,
                "max": 12000,
                "step": 0.1,
            },
            "stop": {
                "description": "Required. The stop position for the motor, uses the default units of the motor",
                "default": 0.0,
                "min": -10000,
                "max": 12000,
                "step": 0.1,
            },
            "num": {
                "description": "Required. The number of points that motor will stop at between the start and stop.",
                "default": 10,
                "min": 0,
                "max": 401,
                "step": 1,
            },
        },
    }
)
def energy_scan_ui(
    detectors,
    motor,
    start: float = 0.0,
    stop: float = 0.0,
    num: int = 10,
    *,
    md: dict = None,
):
    """Scan a single motor over one trajectory (energy UI variant)."""
    yield from _scan(detectors, motor, start, stop, num, md=md)


# 1D angle scan
@parameter_annotation_decorator(
    {
        "description": "Scan over one multi-motor trajectory.",
        "parameters": {
            "detectors": {
                "description": "Required. List of detectors",
                "annotation": "typing.List[str]",
                "convert_device_names": True,
            },
            "motor": {
                "description": "Required. Inidividual motor that is moved between the start and stop positions.",
                "annotation": "typing.Any",
                "convert_device_names": True,
            },
            "start": {
                "description": "Required. The start position for the motor, uses the default units of the motor",
                "default": 0.0,
                "min": -10000,
                "max": 12000,
                "step": 0.1,
            },
            "stop": {
                "description": "Required. The stop position for the motor, uses the default units of the motor",
                "default": 0.0,
                "min": -10000,
                "max": 12000,
                "step": 0.1,
            },
            "num": {
                "description": "Required. The number of points that motor will stop at between the start and stop.",
                "default": 10,
                "min": 0,
                "max": 401,
                "step": 1,
            },
        },
    }
)
def angle_scan(
    detectors,
    motor,
    start: float = 0.0,
    stop: float = 0.0,
    num: int = 10,
    *,
    md: dict = None,
):
    """Scan a single motor over one trajectory (angle variant)."""
    yield from _scan(detectors, motor, start, stop, num, md=md)


# 1D scan for endstation x, z or filters
@parameter_annotation_decorator(
    {
        "description": "Scan over one multi-motor trajectory.",
        "parameters": {
            "detectors": {
                "description": "Required. List of detectors",
                "annotation": "typing.List[str]",
                "convert_device_names": True,
            },
            "motor": {
                "description": "Required. Inidividual motor that is moved between the start and stop positions.",
                "annotation": "typing.Any",
                "convert_device_names": True,
            },
            "start": {
                "description": "Required. The start position for the motor, uses the default units of the motor",
                "default": 0.0,
                "min": -5,
                "max": 5,
                "step": 0.01,
            },
            "stop": {
                "description": "Required. The stop position for the motor, uses the default units of the motor",
                "default": 0.0,
                "min": -5,
                "max": 5,
                "step": 0.01,
            },
            "num": {
                "description": "Required. The number of points that motor will stop at between the start and stop.",
                "default": 10,
                "min": 0,
                "max": 200,
                "step": 1,
            },
        },
    }
)
def rel_scan(
    detectors,
    motor,
    start: float = 0.0,
    stop: float = 0.0,
    num: int = 10,
    *,
    md: dict = None,
):
    """Relative scan of a single motor over one trajectory."""
    yield from _rel_scan(detectors, motor, start, stop, num, md=md)


# MonoEnergy scan - optimized for angle resolution
@parameter_annotation_decorator(
    {
        "description": "Energy scan for monochromator (optimized to avoid duplicate angle positions)",
        "parameters": {
            "detectors": {
                "description": "Required. List of detectors",
                "annotation": "typing.List[str]",
                "convert_device_names": True,
            },
            "mono": {
                "description": "Required. MonoEnergy pseudo positioner",
                "annotation": "typing.Any",
                "convert_device_names": True,
            },
            "start_eV": {
                "description": "Required. Start energy in eV",
                "default": 7000.0,
                "min": 2400,
                "max": 12000,
                "step": 0.1,
            },
            "stop_eV": {
                "description": "Required. Stop energy in eV",
                "default": 7050.0,
                "min": 2400,
                "max": 12000,
                "step": 0.1,
            },
            "num": {
                "description": "Required. Requested number of points (will be adjusted to match 0.001° resolution)",
                "default": 120,
                "min": 2,
                "max": 10000,
                "step": 1,
            },
        },
    }
)
def energy_scan(
    detectors,
    mono,
    start_eV: float = 7000.0,
    stop_eV: float = 7050.0,
    num: int = 120,
    *,
    md: dict = None,
):
    """Scan monochromator energy with automatic optimization for angle resolution.

    Converts energy range to angle range and adjusts the number of points
    to ensure scan steps are multiples of 0.001° (the mono resolution).
    This avoids wasting time on duplicate positions.

    Args:
        detectors: List of detectors
        mono: MonoEnergy instance
        start_eV: Start energy in eV
        stop_eV: Stop energy in eV
        num: Requested number of points
        md: Optional metadata dictionary

    Example:
        RE(energy_scan([diode], mono, 7000, 7050, 120))
    """
    angle_resolution = 0.001  # degrees

    # Convert energy to angle
    start_angle = mono.forward(mono.PseudoPosition(energy_eV=start_eV)).mono_angle
    stop_angle = mono.forward(mono.PseudoPosition(energy_eV=stop_eV)).mono_angle

    # Calculate actual angle range
    angle_range = abs(stop_angle - start_angle)

    # Calculate requested step size
    requested_step = angle_range / (num - 1) if num > 1 else angle_range

    # Round step size to nearest multiple of resolution (at least 1x)
    step_multiple = max(1, round(requested_step / angle_resolution))
    actual_step = step_multiple * angle_resolution

    # Calculate actual number of points
    actual_num = int(angle_range / actual_step) + 1

    # Report scan parameters
    print(f"\n{'=' * 60}")
    print("MonoEnergy Scan")
    print(f"{'=' * 60}")
    print(f"Energy range:    {start_eV:.1f} → {stop_eV:.1f} eV")
    print(f"Angle range:     {start_angle:.4f} → {stop_angle:.4f}°")
    print(f"Requested:       {num} points (step = {requested_step:.6f}°)")
    print(
        f"Optimized:       {actual_num} points (step = {actual_step:.4f}° = {step_multiple}x{angle_resolution}°)"
    )

    if actual_num != num:
        print(f"Adjustment:      Avoiding {num - actual_num} duplicate positions")
    else:
        print("Status:          Already optimal!")

    print(f"{'=' * 60}\n")

    # Execute the scan on the real motor (angle)
    yield from _scan(
        detectors, mono.mono_angle, start_angle, stop_angle, actual_num, md=md
    )
