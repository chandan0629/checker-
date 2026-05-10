import cv2
import numpy as np
import os
from pathlib import Path
from PIL import Image
import zlib
import base64

class IPBTL_Decryption:
    """
    Implementation of Decryption and Data Extraction for IPBTL-RDHEI.
    """
    
    def __init__(self, L=3, key=42):
        self.L = L
        self.key = key
        self.lsb_mask = (0xFF << self.L) & 0xFF

    def med_predictor(self, u, l, ul):
        u, l, ul = int(u), int(l), int(ul)
        if ul >= max(u, l):
            return min(u, l)
        elif ul <= min(u, l):
            return max(u, l)
        else:
            return u + l - ul

    def generate_encryption_mask(self, shape):
        np.random.seed(self.key)
        return np.random.randint(0, 1 << self.L, shape, dtype=np.uint8)

    def decrypt_image(self, encrypted_path: Path, decrypted_dir: Path):
        # Read encrypted image
        img = cv2.imread(str(encrypted_path), cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"[-] Error: Could not read {encrypted_path.name}")
            return

        if img.ndim == 2:
            img = img[:, :, np.newaxis]

        h, w, channels = img.shape
        # Recover original image and extract data
        recovered_img = np.zeros((h, w), dtype=np.uint8)
        if channels > 1:
            recovered_img = np.zeros((h, w, channels), dtype=np.uint8)

        # Reference pixels (row 0 and column 0) were not labeled; they
        # were left as the original (we avoided XOR for visual fidelity),
        # so copy them directly from the encrypted file.
        recovered_img[0, :] = img[0, :]
        recovered_img[:, 0] = img[:, 0]
        
        extracted_bits = []
        
        for i in range(1, h):
            for j in range(1, w):
                for c in range(channels):
                    pred = self.med_predictor(recovered_img[i-1, j, c] if channels > 1 else recovered_img[i-1, j], 
                                              recovered_img[i, j-1, c] if channels > 1 else recovered_img[i, j-1], 
                                              recovered_img[i-1, j-1, c] if channels > 1 else recovered_img[i-1, j-1])
                    
                    label = img[i, j, c] & 7 if channels > 1 else img[i, j] & 7
                    e = 0
                    if label == 0: e = -4
                    elif label == 1: e = -3
                    elif label == 2: e = -2
                    elif label == 3: e = -1
                    elif label == 4 or label == 5:
                        e = 0
                        extracted_bits.append(label & 1)
                    elif label == 6: e = 1
                    elif label == 7: e = 2
                    
                    if channels > 1:
                        recovered_img[i, j, c] = np.clip(pred + e, 0, 255)
                    else:
                        recovered_img[i, j] = np.clip(pred + e, 0, 255)

        if channels == 1:
            recovered_img = recovered_img[:, :, 0]

        # If exception metadata was embedded into the PNG, extract it and
        # restore those pixels exactly.
        try:
            pil = Image.open(str(encrypted_path))
            b64 = pil.info.get('pbtl_meta')
            if b64:
                compressed = base64.b64decode(b64)
                raw = zlib.decompress(compressed)
                arr = np.frombuffer(raw, dtype=np.int32).reshape(-1, 4)
                for rec in arr:
                    i, j, c, val = map(int, rec)
                    if channels == 1:
                        recovered_img[i, j] = val
                    else:
                        recovered_img[i, j, c] = val
        except Exception:
            pass

        # Convert bits to message
        message = ""
        # The bits were added in the order they appear in the msg_bits string
        # msg_bits = ''.join(format(ord(c), '08b') for c in secret_msg)
        # So extracted_bits[0..7] correspond to the first character's 8 bits
        for b in range(0, len(extracted_bits), 8):
            byte_bits = extracted_bits[b:b+8]
            if len(byte_bits) < 8: break
            
            char_bits_str = "".join(map(str, byte_bits))
            char_code = int(char_bits_str, 2)
            
            if char_code == 0: break
            message += chr(char_code)

        # Save results
        save_img_path = decrypted_dir / encrypted_path.name
        cv2.imwrite(str(save_img_path), recovered_img)
        
        save_txt_path = decrypted_dir / (encrypted_path.stem + ".txt")
        with open(save_txt_path, "w", encoding="utf-8") as f:
            f.write(message)
            
        print(f"[+] Decrypted: {encrypted_path.name}")
        print(f"    Message: {message[:50]}...")

def main():
    encrypted_dir = Path("./encrypted_images")
    decrypted_dir = Path("./decrypted_images")
    decrypted_dir.mkdir(exist_ok=True)
    
    decryptor = IPBTL_Decryption(L=3, key=42)
    
    image_files = list(encrypted_dir.glob("*"))
    if not image_files:
        print("No encrypted images found.")
        return
        
    for img_path in image_files:
        if img_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            decryptor.decrypt_image(img_path, decrypted_dir)

if __name__ == "__main__":
    main()




