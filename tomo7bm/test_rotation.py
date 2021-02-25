import numpy as np
import matplotlib.pyplot as plt
import skimage.feature
import skimage.io
import align
import skimage.transform

bright = skimage.io.imread('Bright_000.tif').astype(np.float64)[2:,:]
dark = skimage.io.imread('Dark_000.tif').astype(np.float64)[2:,:]
image1 = skimage.io.imread('Alignment_013.tif').astype(np.float64)[2:,:]
image2 = skimage.io.imread('Alignment_014.tif').astype(np.float64)[2:,:]
image1 = align.normalize(image1, bright, dark)
image2 = align.normalize(image2, bright, dark)[:,::-1]
row_shift, col_shift = align.template_match_images(image1, image2)
image2 = np.roll(image2, (row_shift, col_shift), (0,1))
plt.imshow(image1 - image2, vmin = -0.2, vmax = 0.2)
plt.colorbar()
plt.show()

#Try the log polar idea
rad = image1.shape[0] // 2
polar1 = skimage.transform.warp_polar(image1, radius = rad, output_shape = (rad, 3600))
polar2 = skimage.transform.warp_polar(image2, radius = rad, output_shape = (rad, 3600))
plt.imshow(polar1)
plt.figure()
plt.imshow(polar2)
plt.show()
shift1, shift2 = align.template_match_images(polar1, polar2)
print(shift1, shift2)
