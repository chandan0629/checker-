# PBtl / IPBTL-RDHEI (Reversible Data Hiding in Encrypted Images)

This repository contains a Python implementation of a PBTL-style reversible data hiding pipeline using a MED (Median Edge Detector) predictor.

## Files

- `pbtl_encryption.py` — encrypts an image (LSB label embedding) and embeds the hidden message bits.
- `pbtl_decryption.py` — decrypts/reconstructs the original image and extracts the hidden message.
- `assets/` — input images.
- `encrypted_images/` — output encrypted images (PNG).
- `decrypted_images/` — recovered images and extracted message text.
- `requirements.txt` — Python dependencies.

## High-level algorithm

For each pixel (per channel):

1. Predict the pixel using the **MED predictor** from its upper/left/upper-left neighbors.
2. Compute the prediction error `error = alpha - beta`.
3. Map the error into a **3-bit label** and write it into the **lowest 3 bits** of the image.
4. When `error == 0`, embed message bits by choosing label `4` or `5`.
5. Save as PNG (lossless for LSBs).
6. On decryption, reconstruct using the same prediction order, then extract message bits from labels `4` and `5`.
7. Exception pixels are restored using a `pbtl_meta` PNG text chunk when present.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

## Run

Encryption:

```bash
python3 pbtl_encryption.py
```

Decryption:

```bash
python3 pbtl_decryption.py
```

## Expected outputs

- `encrypted_images/<image>.png`
- `decrypted_images/<image>.png`
- `decrypted_images/<image>.txt`

## Documentation

- `PBTL_Documentation.md`
- `PBTL_Documentation_Updated.md`

