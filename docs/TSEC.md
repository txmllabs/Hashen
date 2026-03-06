# Two-Stage Entropy Cascade (TSEC)

## Overview

TSEC is the core analysis engine in Hashen. It determines whether a digital signal (image, audio, video, financial data, etc.) is authentic or manipulated by measuring the **variation in local entropy** across the signal.

The key insight: authentic content exhibits **natural entropy variation** (high H2), while synthetic or manipulated content exhibits **entropy uniformity** (low H2).

## How It Works

### Stage 1: Windowed H1 Computation

The input signal is segmented into fixed-length windows. For each window, Shannon entropy H1 is computed from a histogram-based probability distribution. This produces an **ordered array of H1 values** that captures local entropy variation across the signal.

```
Signal: [████████████████████████████████████]
         ↓ window 1  ↓ window 2  ↓ window 3 ...
H1:     [   5.2    ] [   4.8    ] [   5.5   ] → H1 array = [5.2, 4.8, 5.5, ...]
```

### Stage 2: Fixed-Range H2 Computation

A **second histogram** is constructed over the H1 array using a **fixed entropy range** (e.g., 0 to 6.0). H2 is computed as the Shannon entropy of this histogram.

The fixed range is **preconfigured and independent of the input data**. This prevents auto-scaling artifacts where low-variance data gets artificially spread across histogram bins, producing incorrect classifications.

```
H1 array: [5.2, 4.8, 5.5, 5.1, 4.9, 5.3, ...]  (varied → high H2)
H1 array: [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, ...]  (uniform → low H2)
```

### Classification

- H2 > threshold → **Authentic** (natural entropy variation)
- H2 ≤ threshold → **Potentially manipulated** (entropy uniformity)

## Modality Pathways

TSEC adapts to different data types via modality-specific pathways:

| Pathway | Input | H1 Computed On |
|---------|-------|----------------|
| Image (130a) | Pixel intensities | Tile histograms |
| Audio (130b) | STFT frames | Spectral energy distributions |
| Time-series (130c) | Sensor readings | Sliding temporal windows |
| Graph (130d) | Edge lists | Node degree distributions |
| Text | Character sequences | Character n-gram frequencies |
| Raw | Byte streams | Direct byte value histograms |

## Configuration

Key parameters in `config_vector`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `use_tsec` | `false` | Enable TSEC cascade (vs legacy) |
| `modality` | `"raw"` | Modality pathway to use |
| `window_size` | `512` | Stage 1 window size |
| `step_size` | `256` | Stage 1 step (50% overlap) |
| `h1_bins` | `64` | Histogram bins for Stage 1 |
| `h2_min` | `0.0` | Stage 2 histogram range minimum |
| `h2_max` | `6.0` | Stage 2 histogram range maximum |
| `h2_bins` | `64` | Histogram bins for Stage 2 |
| `authenticity_threshold` | `4.0` | H2 threshold for classification |

## Why Fixed Range Matters

Without fixed range, the Stage 2 histogram auto-scales to the min/max of the H1 values in each sample. This causes a critical bug: data with very uniform H1 values (low variance) gets spread across the full histogram, artificially inflating H2. The fix is simple: use a predetermined range (default 0 to log2(h1_bins)) that is the same for all samples.

See [FIXED_ENTROPY_RANGE.md](FIXED_ENTROPY_RANGE.md) for details.

## Benchmark Results

| Domain | AUC | Accuracy | Cohen's d |
|--------|-----|----------|-----------|
| Audio (voice clone) | 1.000 | 100% | 2.55 |
| Video (deepfake) | 1.000 | 100% | 5.67 |
| Image (AI-generated) | 1.000 | 100% | 2.89 |
| Financial fraud | 0.944 | 88.8% | 2.27 |

Run benchmarks: `hashen benchmark run --domain all --samples 40`
