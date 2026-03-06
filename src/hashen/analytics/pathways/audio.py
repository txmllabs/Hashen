"""Audio pathway: STFT spectral energy → H1 per frame (Component 130b, Claim 18)."""

from __future__ import annotations

import math


def audio_to_spectral_h1(
    audio_samples: list[float],
    window_size: int = 1024,
    hop_length: int = 512,
    n_freq_bins: int = 64,
) -> list[float]:
    """
    Compute per-frame spectral entropy from audio samples.

    Returns H1 values directly (one per STFT frame).
    Patent Claim 18(b-d): STFT → spectral distribution → H1 per frame.
    """
    h1_values: list[float] = []
    for start in range(0, len(audio_samples) - window_size + 1, hop_length):
        frame = audio_samples[start : start + window_size]
        n = len(frame)
        magnitudes: list[float] = []
        for k in range(min(n_freq_bins, n)):
            re_sum = sum(
                frame[t] * math.cos(2 * math.pi * k * t / n) for t in range(n)
            )
            im_sum = sum(
                frame[t] * math.sin(2 * math.pi * k * t / n) for t in range(n)
            )
            magnitudes.append(math.sqrt(re_sum**2 + im_sum**2))
        total = sum(magnitudes) + 1e-12
        probs = [m / total for m in magnitudes]
        h1 = -sum(p * math.log2(p + 1e-12) for p in probs if p > 0)
        h1_values.append(h1)
    return h1_values
