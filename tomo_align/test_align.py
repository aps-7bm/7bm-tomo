import align
import skimage.io
import numpy as np
import matplotlib.pyplot as plt

bright = skimage.io.imread('Bright_000.tif').astype(np.float64)[2:,:]
dark = skimage.io.imread('Dark_000.tif').astype(np.float64)[2:,:]
image1 = skimage.io.imread('Alignment_090.tif').astype(np.float64)[2:,:]
image2 = skimage.io.imread('Alignment_091.tif').astype(np.float64)[2:,:]
image1 = align.normalize(image1, bright, dark)
image2 = np.roll(image1, (-250, 400), axis=(0,1))
image2[-250:,:] = 0
image2[:,:400] = 0
#image2 = align.normalize(image2, bright, dark)[:,::-1]
#skimage.io.imsave('Align_Norm_91.tif', image2.astype(np.float32))
#skimage.io.imsave('Align_Norm_90.tif', image1.astype(np.float32))
plt.figure(1)
plt.imshow(image1)#, vmin=0, vmax=4)
plt.colorbar()
plt.figure(2)
plt.imshow(image2)#, vmin=0, vmax=4)
plt.colorbar()
plt.show()
print(image1.shape)
print(image2.shape)
plt.imshow(image1 - image2, vmin=-0.5, vmax=0.5)
plt.colorbar()
plt.show()
print(align.template_match_images(image1, image2))
