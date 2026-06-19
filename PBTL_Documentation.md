# PBTL / IPBTL-RDHEI Documentation

This document explains the implemented PBTL-style flow in this repository with direct reference to the code in `pbtl_encryption.py` and `pbtl_decryption.py`.

## What the code does

The current implementation performs the following steps on each image:

1. Reads the image with OpenCV.
2. Treats the image as a 2-D pixel matrix for each channel.
3. Uses the **MED predictor** (Median Edge Detector) to predict a pixel from its upper, left, and upper-left neighbors.
4. Computes a prediction error.
5. Maps that error to a **PBTL label** in the lowest 3 bits.
6. Stores the label in the PNG output.
7. During decryption, reuses the same prediction order to recover the original image and extract the hidden message.
8. If needed, restores exception pixels from the embedded PNG metadata chunk `pbtl_meta`.

The implementation is based on the code in:

- `pbtl_encryption.py`
- `pbtl_decryption.py`

## Important note about alpha and beta

The codebase does **not** use explicit variables named `alpha` and `beta`. In this document, those terms are mapped to the actual implemented logic:

- **alpha** = the original current pixel value `I(i, j)`
- **beta** = the predicted pixel value `pred` produced by the MED predictor
- **residual / error** = `alpha - beta`

So when this document says “alpha/beta”, it means the original pixel and the predicted pixel used by the implemented PBTL flow.

## 2-D image matrix view

A grayscale image can be represented as a matrix:

$$
I = \begin{bmatrix}
I(0,0) & I(0,1) & I(0,2) & \cdots \\
I(1,0) & I(1,1) & I(1,2) & \cdots \\
I(2,0) & I(2,1) & I(2,2) & \cdots \\
\vdots & \vdots & \vdots & \ddots
\end{bmatrix}
$$

For color images, the code processes each channel separately, so you can think of it as three 2-D matrices:

- Blue channel matrix
- Green channel matrix
- Red channel matrix

Each channel is handled using the same prediction and labeling logic.

## Pixel neighborhood used by MED

For a pixel at position `(i, j)`, the code uses these neighbors:

- `u = I(i-1, j)` → upper pixel
- `l = I(i, j-1)` → left pixel
- `ul = I(i-1, j-1)` → upper-left pixel

This is implemented in `med_predictor(u, l, ul)` in both scripts.

### MED predictor rule

The predictor follows this exact logic:

- If `ul >= max(u, l)`, return `min(u, l)`
- If `ul <= min(u, l)`, return `max(u, l)`
- Otherwise, return `u + l - ul`

In short, the prediction is a content-aware estimate from neighboring pixels.

## How PBTL label generation works

The implemented code uses `L = 3`, which means the label is stored in 3 bits.

That gives 8 possible label values:

| Label | Meaning |
|---|---|
| 0 | error <= -4 |
| 1 | error = -3 |
| 2 | error = -2 |
| 3 | error = -1 |
| 4 | error = 0, bit 0 |
| 5 | error = 0, bit 1 |
| 6 | error = 1 |
| 7 | error >= 2 |

This is implemented in `process_image()` inside `pbtl_encryption.py`.

### Error calculation

For each pixel, the code calculates:

$$
error = alpha - beta = I(i,j) - pred
$$

Then it maps the error to one of the 3-bit labels.

### Message embedding

When `error == 0`, the code uses the label value `4` or `5`:

- `4` means embedded bit `0`
- `5` means embedded bit `1`

This lets the code hide a message bit in the lowest 3 bits.

## Example with a small pixel matrix

Consider a small matrix `I`:

$$
I = \begin{bmatrix}
100 & 102 & 103 \\
101 & 104 & 105 \\
99 & 106 & 110
\end{bmatrix}
$$

For pixel `I(1,1) = 104`:

- `u = I(0,1) = 102`
- `l = I(1,0) = 101`
- `ul = I(0,0) = 100`

Since `ul` lies between `u` and `l`, the MED rule returns:

$$
pred = u + l - ul = 102 + 101 - 100 = 103
$$

So:

$$
error = 104 - 103 = 1
$$

The code maps `error = 1` to label `6`.

That label is written into the lowest 3 bits of the stored PNG pixel.

## Encryption flow in this repository

Here is the implemented flow from `pbtl_encryption.py`:

```text
Input image
  ↓
Read with cv2.imread(..., IMREAD_UNCHANGED)
  ↓
Split into channels if needed
  ↓
For each pixel (i, j) and channel:
  - predict beta using MED
  - compute error = alpha - beta
  - convert error to 3-bit PBTL label
  - store label in the lowest 3 bits
  - keep a working copy in sync for causal prediction
  ↓
Save encrypted PNG
  ↓
If needed, embed exception metadata in PNG text chunk pbtl_meta
```

## Decryption flow in this repository

Here is the implemented flow from `pbtl_decryption.py`:

```text
Encrypted PNG
  ↓
Read with cv2.imread(..., IMREAD_UNCHANGED)
  ↓
Split into channels if needed
  ↓
Copy reference pixels directly
  ↓
For each pixel (i, j) and channel:
  - reconstruct beta using the same MED order
  - read the 3-bit label from the PNG
  - map label back to an error value
  - recover alpha = beta + error
  ↓
Extract message bits from labels 4 and 5
  ↓
Rebuild the hidden message text file
  ↓
If PNG contains pbtl_meta, restore exceptional pixels exactly
```

## Diagram

```mermaid
flowchart TD
    A[Original image matrix I] --> B[Pick pixel I(i,j)]
    B --> C[Read neighbors u, l, ul]
    C --> D[MED predictor computes beta]
    D --> E[Compute error = alpha - beta]
    E --> F[Map error to 3-bit PBTL label]
    F --> G[Store label in lowest 3 bits]
    G --> H[Encrypted PNG]

    H --> I[Read PNG during decryption]
    I --> J[Use same neighbor order]
    J --> K[Recompute beta]
    K --> L[Read label from lowest 3 bits]
    L --> M[Convert label back to error]
    M --> N[Recover alpha = beta + error]
    N --> O[Recovered original image]
    L --> P[Extract hidden message bits]
    P --> Q[Write message text file]
```

## Code references

### Encryption

- Image reading and channel handling in `pbtl_encryption.py`
- MED predictor in `med_predictor()`
- Label generation in `process_image()`
- PNG save and embedded metadata in `process_image()`

### Decryption

- Image reading and channel handling in `pbtl_decryption.py`
- MED predictor in `med_predictor()`
- Label decoding and recovery in `decrypt_image()`
- PNG metadata extraction from `pbtl_meta`

## Why the current output stays visually close

The final encrypted PNG does not apply a full-image XOR. Instead, it only changes the lowest 3 bits with the PBTL label. That means:

- the image still looks close to the original
- the hidden data is preserved
- the decryption can reconstruct the original image exactly

## Practical notes

- The implementation is **lossless** for the tested image pipeline.
- PNG is required because it preserves LSB information.
- The current code uses `L = 3` and `key = 42`.
- The message extracted during decryption is written to a `.txt` file next to the decrypted image.

## Example command flow

```bash
python3 pbtl_encryption.py
python3 pbtl_decryption.py
```

After that, you should see:

- `encrypted_images/<name>.png`
- `decrypted_images/<name>.png`
- `decrypted_images/<name>.txt`

## Summary

This repository implements a PBTL-style reversible data hiding pipeline where the pixel prediction comes from MED, the residual is converted into a 3-bit label, and the original image is recovered by reversing the same prediction process. The alpha/beta terminology in this document maps directly to the code’s original pixel and predicted pixel values.
