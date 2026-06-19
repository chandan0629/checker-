# PBTL / IPBTL-RDHEI Documentation (Updated)

This document describes the **current implementation** in this repository and how it behaves in practice. It maps directly to the code in `pbtl_encryption.py` and `pbtl_decryption.py`.

## Quick overview

For each image, the pipeline:

1. Reads the image with OpenCV.
2. Predicts each pixel using the MED predictor and its neighbors.
3. Converts the prediction error into a 3‑bit label.
4. Stores the label in the pixel’s lowest 3 bits (LSBs).
5. Embeds message bits when the error is zero.
6. Saves the PNG (lossless).
7. On decrypt, reconstructs the original image and extracts the message.
8. Restores exceptional pixels using embedded PNG metadata (if present).

## Inputs and outputs

**Input**
- Images inside the `assets/` folder.

**Output**
- Encrypted PNGs in `encrypted_images/`.
- Decrypted PNGs in `decrypted_images/`.
- Extracted message text files alongside decrypted images.

## Key parameters used in the code

- `L = 3`: number of lowest bits used to store the label.
- `key = 42`: used to seed the random generator (present but not required for the current label‑only encryption).

## 2‑D image matrix view

A grayscale image is a matrix:

$$
I = \begin{bmatrix}
I(0,0) & I(0,1) & I(0,2) & \cdots \\
I(1,0) & I(1,1) & I(1,2) & \cdots \\
I(2,0) & I(2,1) & I(2,2) & \cdots \\
\vdots & \vdots & \vdots & \ddots
\end{bmatrix}
$$

For color images, the code processes each channel separately (B, G, R), so you can think of three 2‑D matrices handled with the same logic.

## MED predictor (pixel prediction)

For each pixel at `(i, j)`, the code uses these neighbors:

- `u = I(i-1, j)` (upper)
- `l = I(i, j-1)` (left)
- `ul = I(i-1, j-1)` (upper‑left)

The MED rule is:

- If `ul >= max(u, l)`, predict `min(u, l)`.
- If `ul <= min(u, l)`, predict `max(u, l)`.
- Otherwise, predict `u + l - ul`.

That prediction is called **beta** in some papers and **pred** in the code.

## Error (residual)

The error is:

$$
error = I(i,j) - pred
$$

This error is mapped to a 3‑bit label.

## Label mapping (L = 3)

The label is written into the **lowest 3 bits** of the stored pixel. The mapping is:

| Label | Meaning |
|---|---|
| 0 | error <= -4 |
| 1 | error = -3 |
| 2 | error = -2 |
| 3 | error = -1 |
| 4 | error = 0, embedded bit 0 |
| 5 | error = 0, embedded bit 1 |
| 6 | error = 1 |
| 7 | error >= 2 |

## Message embedding

A message is converted to a bit stream. When `error == 0`, the code writes label `4` or `5`:

- `4` embeds a `0`
- `5` embeds a `1`

The message ends with a null byte (`00000000`) so the decoder can stop.

## How the “encryption” is done

The implementation does **not** XOR or scramble the full image. Instead:

- It only replaces the lowest 3 bits with the label.
- The higher bits remain unchanged.

This keeps the encrypted output visually close to the original, but still makes it reversible because the label preserves the prediction error.

## Exception pixels

If an error is **less than −4** or **greater than 2**, the pixel cannot be represented exactly by the 3‑bit label range. These pixels are saved as **exceptions**:

- Their coordinates and original values are collected.
- The list is compressed and stored inside the PNG as a text chunk named `pbtl_meta`.
- During decryption, those pixels are restored exactly.

This preserves full reversibility.

## Encryption flow (current code)

```text
Input image
  ↓
Read with cv2.imread(..., IMREAD_UNCHANGED)
  ↓
If grayscale, add a channel dimension
  ↓
For each pixel and channel:
  - predict using MED
  - compute error
  - map error to 3‑bit label
  - write label into lowest 3 bits
  - keep a working copy synchronized
  ↓
Save PNG (with optional pbtl_meta text chunk)
```

## Decryption flow (current code)

```text
Encrypted PNG
  ↓
Read with cv2.imread(..., IMREAD_UNCHANGED)
  ↓
For each pixel and channel:
  - predict using MED (same order)
  - read 3‑bit label
  - map label to error
  - recover original pixel = pred + error
  ↓
Extract message bits from labels 4 and 5
  ↓
If pbtl_meta exists, restore exception pixels
```

## Why the image still looks normal

Only the lowest 3 bits are modified. That typically changes a pixel by at most ±7, which is visually subtle, so the encrypted image appears close to the original.

## Practical notes

- PNG is required (LSBs are preserved).
- The code is lossless for typical images.
- The hidden message is written to a `.txt` file during decryption.

## Example run

```bash
python3 pbtl_encryption.py
python3 pbtl_decryption.py
```

Expected outputs:

- `encrypted_images/<name>.png`
- `decrypted_images/<name>.png`
- `decrypted_images/<name>.txt`

## Summary

This repository implements a PBTL‑style reversible data hiding system using MED prediction and 3‑bit labeling. It modifies only the LSBs for embedding while keeping the rest of the pixel unchanged, enabling near‑original appearance and full reversibility.
