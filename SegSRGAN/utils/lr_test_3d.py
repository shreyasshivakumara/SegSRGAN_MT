import SimpleITK as sitk
import scipy.ndimage
from ImageReader import NIFTIReader
import numpy as np
reference_instance = NIFTIReader('/proj/SegSRGAN/GoldAtlasMHD/1_04_P/image_resize.nii')
reference_image = reference_instance.get_np_array()
print (reference_image.shape)
x_generator = scipy.ndimage.filters.gaussian_filter(reference_image, sigma=1)
x_generator = scipy.ndimage.zoom(x_generator, [(1 / 4), (1 / 4),(1 / 4)], prefilter=False, order=0)
print ("x_generator" , x_generator.shape)
scanArray = np.transpose(x_generator, (2,1,0))
image = sitk.GetImageFromArray(scanArray)
#print (image)
print ("NP Min", np.min(image))
#image1 = resample_img(image, out_spacing=[1.75,1.75,5], is_label=False)
image.SetSpacing([3.5,3.5,10])
path_output_hr = '/proj/SegSRGAN/GoldAtlasMHD/1_04_P/lr_3d_image_resize_4.nii'
#print (image.GetSpacing())
#print (image.GetSize())
#sitk.WriteImage(image, path_output_hr)
