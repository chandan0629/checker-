import cv2, numpy as np
orig = cv2.imread('assets/jet.jpg', cv2.IMREAD_UNCHANGED)
dec  = cv2.imread('decrypted_images/jet.png', cv2.IMREAD_UNCHANGED)
print('orig', orig.shape, 'dec', dec.shape)
if orig.shape!=dec.shape:
    print('shapes differ')
if orig.dtype!=dec.dtype:
    dec = dec.astype(orig.dtype)
diff = orig.astype(np.int16)-dec.astype(np.int16)
ne = np.count_nonzero(diff)
print('differing elements:', ne)
if ne>0:
    mask = np.any(diff!=0, axis=2)
    ys, xs = np.where(mask)
    print('examples:', list(zip(ys[:5], xs[:5])))
    y,x = ys[0], xs[0]
    print('orig pixel', orig[y,x].tolist(), 'dec pixel', dec[y,x].tolist())
    chdiff = [np.count_nonzero(diff[:,:,ch]) for ch in range(diff.shape[2])]
    print('per-channel diffs:', chdiff)
