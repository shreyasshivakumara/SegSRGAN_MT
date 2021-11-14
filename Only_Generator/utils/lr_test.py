import SimpleITK as sitk
import scipy.ndimage
from ImageReader import NIFTIReader
import numpy as np
reference_instance = NIFTIReader('/proj/SegSRGAN/GoldAtlasMHD/1_04_P/image_resize.nii')
reference_image = reference_instance.get_np_array()
print (reference_image.shape[0])
#new_resolution = [0.5,0.5,2]
new_resolution = [[0.5,0.5,2], [0.5,0.5,3]]
lin_res_x = np.linspace(new_resolution[0][0], new_resolution[1][0], reference_image.shape[0])
lin_res_y = np.linspace(new_resolution[0][1], new_resolution[1][1], reference_image.shape[1])
lin_res_z = np.linspace(new_resolution[0][2], new_resolution[1][2], reference_image.shape[2])
#print (lin_res_y)
res_test = []
res_test.append([lin_res_x[i] for i in range(reference_image.shape[0])])
res_test.append([lin_res_y[i] for i in range(reference_image.shape[1])])
res_test.append([lin_res_z[i] for i in range(reference_image.shape[2])])
list_res = res_test
up_scale = tuple(itemb/itema for itema, itemb in zip(reference_instance.itk_image.GetSpacing(), list_res[0]))
#print (up_scale)
BlurReferenceImage = scipy.ndimage.filters.gaussian_filter(reference_image, sigma=2)
low_resolution_image = scipy.ndimage.zoom(BlurReferenceImage, zoom=(1/float(idxScale) for idxScale in up_scale),order=0)
image = sitk.GetImageFromArray(low_resolution_image)
path_output_hr = 'lr_image_resize.nii'
sitk.WriteImage(image, path_output_hr)
#path_output_hr = ''
print (low_resolution_image.shape)
#sitk.WriteImage(image, path_output_hr)
