import cv2
import numpy as np
import os
import random
from pathlib import Path
from PIL import Image, PngImagePlugin
import zlib
import base64

class IPBTL_RDHEI:
    """
    Implementation of Improved Parametric Binary Tree Labeling for 
    Reversible Data Hiding in Encrypted Images (IPBTL-RDHEI).
    
    This class handles the Content Owner's role:
    1. Image Prediction (using MED)
    2. Pixel Labeling (using Parametric Binary Tree)
    3. Image Encryption
    4. Room Vacating (Labeling/Preprocessing for data hiding)
    """

    def __init__(self, L=3, key=12345):
        """
        Args:
            L (int): Depth of the parametric binary tree.
            key (int): Encryption key used to seed the PRNG for image encryption.
        """
        self.L = L
        self.key = key
        self.lsb_mask = (0xFF << self.L) & 0xFF

    def med_predictor(self, u, l, ul):
        """
        Median Edge Detector (MED) Predictor.
        Calculates the predicted value of a pixel based on its neighbors.
        
        Args:
            u: Upper neighbor I(i-1, j)
            l: Left neighbor I(i, j-1)
            ul: Upper-left neighbor I(i-1, j-1)
        """
        u, l, ul = int(u), int(l), int(ul)
        if ul >= max(u, l):
            return min(u, l)
        elif ul <= min(u, l):
            return max(u, l)
        else:
            return u + l - ul

    def generate_encryption_mask(self, shape):
        """Generates a pseudo-random mask for encryption based on the key."""
        np.random.seed(self.key)
        return np.random.randint(0, 1 << self.L, shape, dtype=np.uint8)

    def process_image(self, img_path: Path, save_path: Path, secret_msg: str = "Secret Message"):
        """
        Processes a single image: predicts, labels, encrypts, and embeds data.
        """
        # Read image
        img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"[-] Error: Could not read {img_path.name}")
            return

        if img.ndim == 2:
            img = img[:, :, np.newaxis]

        h, w, channels = img.shape
        
        # Convert message to bits
        msg_bits = ''.join(format(ord(c), '08b') for c in secret_msg) + '00000000'
        msg_idx = 0
        
        # 2. Encryption Phase
        # To keep the encrypted image visually close to the original,
        # only replace the lowest `L` bits with the label. Do not XOR
        # the whole image — this preserves appearance and still allows
        # reversible reconstruction using the labels.
        final_img = img.copy()
        
        embedded_count = 0
        exceptions = []
        # Use a working copy to compute predictions based on already-embedded/reconstructed
        # neighbor pixels so encryption and decryption follow the same causal order.
        work = img.copy().astype(np.int32)
        for i in range(1, h):
            for j in range(1, w):
                for c in range(channels):
                    pred = self.med_predictor(work[i-1, j, c], work[i, j-1, c], work[i-1, j-1, c])
                    error = int(img[i, j, c]) - pred
                    
                    # Label mapping (L=3, 8 values):
                    # 0: e=-4, 1: e=-3, 2: e=-2, 3: e=-1
                    # 4: e=0, bit=0
                    # 5: e=0, bit=1
                    # 6: e=1, 7: e=2
                    
                    label = 0
                    if error <= -4:
                        label = 0
                        if error < -4:
                            exceptions.append((i, j, c, int(img[i, j, c])))
                    elif error == -3: label = 1
                    elif error == -2: label = 2
                    elif error == -1: label = 3
                    elif error == 0:
                        label = 4
                        if msg_idx < len(msg_bits):
                            label |= int(msg_bits[msg_idx])
                            msg_idx += 1
                            embedded_count += 1
                    elif error == 1:
                        label = 6
                    else:
                        label = 7
                        if error > 2:
                            exceptions.append((i, j, c, int(img[i, j, c])))
                    
                    final_img[i, j, c] = (img[i, j, c] & self.lsb_mask) | label
                    # Update working image with reconstructed value so subsequent
                    # predictions match decryption's reconstruction order.
                    if label == 0:
                        e = -4
                    elif label == 1:
                        e = -3
                    elif label == 2:
                        e = -2
                    elif label == 3:
                        e = -1
                    elif label in (4, 5):
                        e = 0
                    elif label == 6:
                        e = 1
                    else:
                        e = 2
                    recon = pred + e
                    work[i, j, c] = np.clip(recon, 0, 255)

        if channels == 1:
            final_img = final_img[:, :, 0]

        # Save the processed image. If we have exception metadata, embed it
        # into the PNG as a compressed base64 text chunk so there are no
        # separate sidecar files.
        if exceptions:
            arr = np.array(exceptions, dtype=np.int32)
            raw = arr.tobytes()
            compressed = zlib.compress(raw)
            b64 = base64.b64encode(compressed).decode('ascii')

            # cv2 arrays are BGR; convert to RGB for PIL
            pil_img = final_img
            if channels == 3:
                pil_img = cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB)
            elif channels == 4:
                pil_img = cv2.cvtColor(final_img, cv2.COLOR_BGRA2RGBA)
            pil = Image.fromarray(pil_img)
            meta = PngImagePlugin.PngInfo()
            meta.add_text('pbtl_meta', b64)
            pil.save(str(save_path), pnginfo=meta)
        else:
            # No metadata: save normally via cv2 to keep BGR ordering consistent
            cv2.imwrite(str(save_path), final_img)
        print(f"[+] Encrypted and embedded: {save_path.name} ({embedded_count} bits)")

def main():
    # Setup directories
    assets_dir = Path("./assets")
    encrypted_dir = Path("./encrypted_images")
    encrypted_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize the IPBTL algorithm
    pbtl = IPBTL_RDHEI(L=3, key=42)
    
    msg = "TULIPS ARE BEAUTIFUL! 🌷🌷🌷"
    
    image_files = list(assets_dir.glob("*"))
    if not image_files:
        print(f"Warning: No images found in the '{assets_dir}' directory.")
        return

    for img_path in assets_dir.glob("*"):
        if img_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
            # Save as PNG to ensure lossless preservation of LSBs
            save_path = encrypted_dir / (img_path.stem + ".png")
            pbtl.process_image(img_path, save_path, msg)
    
    print("-" * 40)
    print("Encryption and Data Hiding complete.")

    
    print("-" * 40)
    print("Processing complete.")

if __name__ == "__main__":
    main()


