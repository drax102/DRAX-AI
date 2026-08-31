"""
audio_manager.py — Microphone discovery, configuration, and stream management for DRAX AI.
"""

import sounddevice as sd
from backend.core.logger import get_logger
from backend.core.config import settings

logger = get_logger(__name__)


def list_input_devices() -> list[dict]:
    """Return a list of available input (microphone) devices."""
    devices = []
    try:
        all_devices = sd.query_devices()
        for idx, dev in enumerate(all_devices):
            if dev.get("max_input_channels", 0) > 0:
                devices.append({
                    "index": idx,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": int(dev["default_samplerate"]),
                })
    except Exception as e:
        logger.error(f"Failed to enumerate audio devices: {e}")
    return devices


def get_default_input_device() -> dict | None:
    """Return the system default input device info, or None."""
    try:
        dev = sd.query_devices(kind="input")
        return {
            "index": None,  # None = system default in sounddevice
            "name": dev["name"],
            "channels": dev["max_input_channels"],
            "sample_rate": int(dev["default_samplerate"]),
        }
    except Exception as e:
        logger.error(f"Failed to get default input device: {e}")
        return None


def resolve_device_index() -> int | None:
    """
    Resolve microphone device index from settings.
    - "auto" → None (sounddevice uses system default)
    - integer string → that device index
    - device name substring → matched by name
    Returns None (system default) if resolution fails.
    """
    mic_setting = settings.get("speech", "microphone", "auto")

    if mic_setting == "auto":
        logger.info("Microphone: using system default")
        return None

    # Try as integer index
    try:
        idx = int(mic_setting)
        devices = list_input_devices()
        if any(d["index"] == idx for d in devices):
            logger.info(f"Microphone: using device index {idx}")
            return idx
        else:
            logger.warning(f"Device index {idx} not found — falling back to default")
            return None
    except (ValueError, TypeError):
        pass

    # Try as name substring
    mic_lower = str(mic_setting).lower()
    devices = list_input_devices()
    for dev in devices:
        if mic_lower in dev["name"].lower():
            logger.info(f"Microphone: matched '{dev['name']}' (index {dev['index']})")
            return dev["index"]

    logger.warning(f"Microphone '{mic_setting}' not found — falling back to default")
    return None


def print_device_list():
    """Print all available input devices to console (for diagnostics)."""
    devices = list_input_devices()
    if not devices:
        print("No input devices found.")
        return
    print(f"\n{'Index':<6} {'Name':<45} {'Channels':<10} {'Sample Rate'}")
    print("-" * 70)
    for d in devices:
        print(f"{d['index']:<6} {d['name']:<45} {d['channels']:<10} {d['sample_rate']}")
    print()


def test_microphone(duration: float = 3.0) -> bool:
    """
    Record audio for `duration` seconds using the configured device.
    Returns True if successful, False on error.
    """
    device_idx = resolve_device_index()
    sample_rate = settings.get("speech", "sample_rate", 16000)
    try:
        logger.info(f"Microphone test: recording {duration}s at {sample_rate}Hz")
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            device=device_idx,
        )
        sd.wait()
        # Check if we got any non-zero audio
        peak = int(abs(audio).max())
        logger.info(f"Microphone test complete — peak level: {peak}")
        if peak < 50:
            logger.warning("Microphone test: very low audio level — check microphone")
        return True
    except Exception as e:
        logger.error(f"Microphone test failed: {e}")
        return False
