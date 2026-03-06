"""Synthetic dataset generators for TSEC benchmarking."""

from __future__ import annotations

import random


def _seeded(seed: int) -> random.Random:
    """Return a deterministic Random instance."""
    return random.Random(seed)


def generate_audio_dataset(
    n_samples: int = 40,
    seed: int = 42,
) -> dict[str, list[list[float]]]:
    """
    Generate synthetic authentic vs cloned audio H1 sequences.

    Authentic: varied spectral entropy (phonemes, breaths, silences).
    Cloned: smooth spectral entropy (neural vocoder).
    Returns {"authentic": [list[float], ...], "attack": [list[float], ...]}
    """
    rng = _seeded(seed)
    authentic = []
    for _ in range(n_samples):
        h1_seq = []
        for _ in range(500):
            seg = rng.choice(["voiced", "unvoiced", "silence", "breath"])
            if seg == "voiced":
                h1_seq.append(rng.gauss(5.5, 0.6))
            elif seg == "unvoiced":
                h1_seq.append(rng.gauss(6.5, 0.4))
            elif seg == "silence":
                h1_seq.append(rng.gauss(2.0, 0.5))
            else:
                h1_seq.append(rng.gauss(4.0, 0.8))
        authentic.append(h1_seq)

    attack = []
    for i in range(n_samples):
        rng2 = _seeded(seed + 10000 + i)
        t = i % 3
        if t == 0:
            attack.append([rng2.gauss(5.0, 0.15) for _ in range(500)])
        elif t == 1:
            seq = []
            for _ in range(500):
                if rng2.random() < 0.85:
                    seq.append(rng2.gauss(5.2, 0.3))
                else:
                    seq.append(rng2.gauss(3.0, 0.2))
            attack.append(seq)
        else:
            seq = []
            for _ in range(500):
                seg = rng2.choice(["v", "u", "s"])
                if seg == "v":
                    seq.append(rng2.gauss(5.3, 0.35))
                elif seg == "u":
                    seq.append(rng2.gauss(6.0, 0.25))
                else:
                    seq.append(rng2.gauss(2.5, 0.3))
            attack.append(seq)

    return {"authentic": authentic, "attack": attack}


def generate_financial_dataset(
    n_samples: int = 40,
    seed: int = 42,
) -> dict[str, list[list[float]]]:
    """
    Generate synthetic normal vs fraudulent transaction streams.

    Normal: log-normal amounts + Poisson timing.
    Fraud: card cloning / structured deposits / account takeover.
    Returns values suitable for TSEC windowing.
    """
    rng = _seeded(seed)
    authentic = []
    for _ in range(n_samples):
        amounts = [abs(rng.lognormvariate(4, 1.5)) for _ in range(2000)]
        intervals = [rng.expovariate(1 / 3600) for _ in range(2000)]
        a_max = max(amounts) or 1
        i_max = max(intervals) or 1
        values = [a / a_max for a in amounts] + [i / i_max for i in intervals]
        authentic.append(values)

    attack = []
    for i in range(n_samples):
        rng2 = _seeded(seed + 20000 + i)
        t = i % 3
        if t == 0:
            amounts = [49.99 + rng2.gauss(0, 0.1) for _ in range(1200)] + [
                abs(rng2.lognormvariate(4, 1)) for _ in range(800)
            ]
            intervals = [30 + rng2.gauss(0, 5) for _ in range(1200)] + [
                rng2.expovariate(1 / 3600) for _ in range(800)
            ]
        elif t == 1:
            amounts = [9900 + rng2.uniform(-100, 100) for _ in range(1000)] + [
                abs(rng2.lognormvariate(4, 1)) for _ in range(1000)
            ]
            intervals = [rng2.expovariate(1 / 7200) for _ in range(2000)]
        else:
            amounts = [abs(rng2.lognormvariate(4, 1)) for _ in range(1800)] + [
                rng2.uniform(5000, 20000) for _ in range(200)
            ]
            intervals = [rng2.expovariate(1 / 3600) for _ in range(1800)] + [
                10 + rng2.gauss(0, 2) for _ in range(200)
            ]
        a_max = max(amounts) or 1
        i_max = max(intervals) or 1
        values = [a / a_max for a in amounts] + [i / i_max for i in intervals]
        attack.append(values)

    return {"authentic": authentic, "attack": attack}


def generate_image_dataset(
    n_samples: int = 40,
    seed: int = 42,
) -> dict[str, list[list[float]]]:
    """Generate synthetic real vs AI-generated image pixel values."""
    rng = _seeded(seed)
    authentic = []
    for _ in range(n_samples):
        pixels = [max(0, min(1, rng.gauss(0.5, 0.14) + rng.gauss(0, 0.02))) for _ in range(65536)]
        for _ in range(rng.randint(3, 10)):
            start = rng.randint(0, 60000)
            for j in range(min(2000, 65536 - start)):
                pixels[start + j] = max(0, min(1, pixels[start + j] + rng.gauss(0, 0.15)))
        authentic.append(pixels)

    attack = []
    for i in range(n_samples):
        rng2 = _seeded(seed + 30000 + i)
        t = i % 3
        if t == 0:
            pixels = [i / 65536 + rng2.gauss(0, 0.01) for i in range(65536)]
        elif t == 1:
            pixels = []
            for _ in range(64):
                base = rng2.uniform(0.1, 0.9)
                pixels.extend([max(0, min(1, base + rng2.gauss(0, 0.03))) for _ in range(1024)])
            pixels = pixels[:65536]
        else:
            pixels = [max(0, min(1, rng2.gauss(0.5, 0.14))) for _ in range(65536)]
            for j in range(16384, 49152):
                pixels[j] = max(0, min(1, rng2.gauss(0.55, 0.04)))
        attack.append(pixels)

    return {"authentic": authentic, "attack": attack}
