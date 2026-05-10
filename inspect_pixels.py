import cv2, numpy as np
orig = cv2.imread('assets/jet.jpg', cv2.IMREAD_UNCHANGED)
enc  = cv2.imread('encrypted_images/jet.png', cv2.IMREAD_UNCHANGED)
dec  = cv2.imread('decrypted_images/jet.png', cv2.IMREAD_UNCHANGED)
print('shapes', orig.shape, enc.shape, dec.shape)
L=3; key=42; h,w = orig.shape[:2]
np.random.seed(key)
mask = np.random.randint(0, 1<<L, (h,w), dtype=np.uint8)
print('mask[0,0]', int(mask[0,0]), 'mask[0,1]', int(mask[0,1]))
coords = [(1,1),(1,2),(10,10),(100,200)]
for y,x in coords:
    print('\ncoord', (y,x))
    print('orig', orig[y,x].tolist())
    print('enc ', enc[y,x].tolist())
    print('dec ', dec[y,x].tolist())
    print('enc upper bits', [ int(enc[y,x,ch] & 0xF8) for ch in range(enc.shape[2])])
    print('label', [ int(enc[y,x,ch] & 7) for ch in range(enc.shape[2])])
    print('orig ^ mask', [ int(orig[y,x,ch] ^ mask[y,x]) for ch in range(orig.shape[2])])
