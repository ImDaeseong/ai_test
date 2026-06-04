"""Run Demucs with a WAV-save fallback for newer torchaudio builds."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _patch_torchaudio_save() -> None:
    import torchaudio

    original_save = torchaudio.save

    def save_with_soundfile_fallback(path, src, sample_rate, *args, **kwargs):
        try:
            return original_save(path, src, sample_rate, *args, **kwargs)
        except (ImportError, RuntimeError) as exc:
            message = str(exc)
            if "TorchCodec" not in message and "libtorchcodec" not in message:
                raise

            target = Path(path)
            if target.suffix.lower() != ".wav":
                raise

            import soundfile as sf

            wav = src.detach().cpu()
            data = wav.numpy()
            if data.ndim == 2:
                data = data.T

            encoding = kwargs.get("encoding")
            bits = kwargs.get("bits_per_sample", 16)
            if encoding == "PCM_F":
                subtype = "FLOAT"
            else:
                subtype = {16: "PCM_16", 24: "PCM_24", 32: "PCM_32"}.get(bits, "PCM_16")

            sf.write(str(target), data, sample_rate, subtype=subtype)
            return None

    torchaudio.save = save_with_soundfile_fallback


def main() -> None:
    _patch_torchaudio_save()
    sys.argv = ["demucs.separate", *sys.argv[1:]]
    runpy.run_module("demucs.separate", run_name="__main__")


if __name__ == "__main__":
    main()
