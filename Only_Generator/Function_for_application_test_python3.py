import os

import progressbar
import sys
import h5py

import numpy as np
import SimpleITK as sitk
import scipy.ndimage
from ast import literal_eval as make_tuple

sys.path.insert(0,os.path.split(__file__)[0])

from utils.utils3d import shave3D
from utils.utils3d import pad3D
from utils.SegSRGAN import SegSRGAN
from utils.ImageReader import NIFTIReader
from utils.ImageReader import DICOMReader
from utils.normalization import Normalization
from keras.engine import saving
import utils.interpolation as inter

GREEN = '\033[32m' # mode 32 = green forground
start = "\033[1m" # for printing in bold
end = "\033[0;0m"
RESET = '\033[0m'  # mode 0  = reset


class SegSRGAN_test(object):

    def __init__(self, weights, patch1, patch2, patch3, is_conditional, u_net_gen,is_residual, first_generator_kernel,
                 first_discriminator_kernel,  resolution=0):

        self.patch1 = patch1
        self.patch2 = patch2
        self.patch3 = patch3
        self.prediction = None
        self.SegSRGAN = SegSRGAN(first_generator_kernel=first_generator_kernel,
                                 first_discriminator_kernel=first_discriminator_kernel, u_net_gen=u_net_gen,
                                 image_row=patch1,
                                 image_column=patch2,
                                 image_depth=patch3, is_conditional=is_conditional,
                                 is_residual = is_residual)
        self.generator_model = self.SegSRGAN.generator_model_for_pred()
        self.generator_model.load_weights(weights, by_name=True)
        self.generator = self.SegSRGAN.generator()
        self.is_conditional = is_conditional
        self.resolution = resolution
        self.is_residual = is_residual
        self.res_tensor = np.expand_dims(np.expand_dims(np.ones([patch1, patch2, patch3]) * self.resolution, axis=0),
                                        axis=0)
        print("Init for testing")

    def get_patch(self):
        """

        :return:
        """
        return self.patch

    def test_by_patch(self, test_image, step=1, by_batch=False):
        """

        :param test_image: Image to be tested
        :param step: step
        :param by_batch: to enable by batch processing
        :return:
        """
        # Init temp
        print("Test with patch")
        height, width, depth = np.shape(test_image)

        temp_hr_image = np.zeros_like(test_image)
        temp_seg = np.zeros_like(test_image)
        weighted_image = np.zeros_like(test_image)

        # if is_conditional is set to True we predict on the image AND the resolution
        if self.is_conditional is True:
            if not by_batch:
                print("Condition is true for patch")
                i = 0
                bar = progressbar.ProgressBar(maxval=len(np.arange(0, height - self.patch1 + 1, step)) * len(
                    np.arange(0, width - self.patch2 + 1, step)) * len(np.arange(0, depth - self.patch3 + 1, step))).\
                    start()
                print('Patch=', self.patch1)
                print('Step=', step)
                for idx in range(0, height - self.patch1 + 1, step):
                    for idy in range(0, width - self.patch2 + 1, step):
                        for idz in range(0, depth - self.patch3 + 1, step):
                            # Cropping image
                            test_patch = test_image[idx:idx + self.patch1, idy:idy + self.patch2, idz:idz + self.patch3]
                            image_tensor = test_patch.reshape(1, 1, self.patch1, self.patch2, self.patch3).\
                                astype(np.float32)
                            predict_patch = self.generator.predict([image_tensor, self.res_tensor], batch_size=1)

                            # Adding
                            temp_hr_image[idx:idx + self.patch1, idy:idy + self.patch2,
                            idz:idz + self.patch3] += predict_patch[0, 0, :, :, :]
                            temp_seg[idx:idx + self.patch1, idy:idy + self.patch2, idz:idz + self.patch3] += \
                                predict_patch[0, 1, :, :, :]
                            weighted_image[idx:idx + self.patch1, idy:idy + self.patch2,
                            idz:idz + self.patch3] += np.ones_like(predict_patch[0, 0, :, :, :])

                            i += 1

                            bar.update(i)
            else:

                height = test_image.shape[0]
                width = test_image.shape[1]
                depth = test_image.shape[2]

                patch1 = self.patch1
                patch2 = self.patch2
                patch3 = self.patch3

                patches = np.array([[test_image[idx:idx + patch1, idy:idy + patch2, idz:idz + patch3]] for idx in
                                    range(0, height - patch1 + 1, step) for idy in range(0, width - patch2 + 1, step)
                                    for idz in range(0, depth - patch3 + 1, step)])

                indice_patch = np.array([(idx, idy, idz) for idx in range(0, height - patch1 + 1, step) for idy in
                                         range(0, width - patch2 + 1, step) for idz in range(0, depth - patch3 + 1,
                                                                                             step)])

                pred = self.generator.predict(patches, batch_size=patches.shape[0])

                weight = np.zeros_like(test_image)
                temp_hr_image = np.zeros(test_image)
                temp_seg = np.zeros(test_image)

                for i in range(indice_patch.shape[0]):
                    temp_hr_image[indice_patch[i][0]:indice_patch[i][0] + patch1,
                    indice_patch[i][1]:indice_patch[i][1] + patch2, indice_patch[i][2]:indice_patch[i][2] + patch3] += pred[
                                                                                                                       i, 0,
                                                                                                                       :, :,
                                                                                                                       :]
                    temp_seg[indice_patch[i][0]:indice_patch[i][0] + patch1, indice_patch[i][1]:indice_patch[i][1] + patch2,
                    indice_patch[i][2]:indice_patch[i][2] + patch3] += pred[i, 1, :, :, :]
                    weight[indice_patch[i][0]:indice_patch[i][0] + patch1, indice_patch[i][1]:indice_patch[i][1] + patch2,
                    indice_patch[i][2]:indice_patch[i][2] + patch3] + np.ones_like(
                        weight[indice_patch[i][0]:indice_patch[i][0] + patch1,
                        indice_patch[i][1]:indice_patch[i][1] + patch2, indice_patch[i][2]:indice_patch[i][2] + patch3])
        else:
            if not by_batch:

                i = 0
                bar = progressbar.ProgressBar(maxval=len(np.arange(0, height - self.patch1 + 1, step)) * len(
                    np.arange(0, width - self.patch2 + 1, step)) * len(
                    np.arange(0, depth - self.patch3 + 1, step))).start()
                print('Patch=', self.patch1)
                print('Step=', step)
                for idx in range(0, height - self.patch1 + 1, step):
                    for idy in range(0, width - self.patch2 + 1, step):
                        for idz in range(0, depth - self.patch3 + 1, step):
                            # Cropping image
                            test_patch = test_image[idx:idx + self.patch1, idy:idy + self.patch2, idz:idz + self.patch3]
                            image_tensor = test_patch.reshape(1, 1, self.patch1, self.patch2, self.patch3).astype(
                                np.float32)
                            predict_patch = self.generator.predict(image_tensor, batch_size=1)

                            # Adding
                            temp_hr_image[idx:idx + self.patch1, idy:idy + self.patch2,
                            idz:idz + self.patch3] += predict_patch[0, 0, :, :, :]
                            temp_seg[idx:idx + self.patch1, idy:idy + self.patch2,
                            idz:idz + self.patch3] += predict_patch[0,
                                                      1, :, :, :]
                            weighted_image[idx:idx + self.patch1, idy:idy + self.patch2,
                            idz:idz + self.patch3] += np.ones_like(predict_patch[0, 0, :, :, :])

                            i += 1

                            bar.update(i)
            else:

                height = test_image.shape[0]
                width = test_image.shape[1]
                depth = test_image.shape[2]

                patch1 = self.patch1
                patch2 = self.patch2
                patch3 = self.patch3

                patches = np.array([[test_image[idx:idx + patch1, idy:idy + patch2, idz:idz + patch3]] for idx in
                                    range(0, height - patch1 + 1, step) for idy in range(0, width - patch2 + 1, step)
                                    for
                                    idz in range(0, depth - patch3 + 1, step)])

                indice_patch = np.array([(idx, idy, idz) for idx in range(0, height - patch1 + 1, step) for idy in
                                         range(0, width - patch2 + 1, step) for idz in
                                         range(0, depth - patch3 + 1, step)])

                pred = self.generator.predict(patches, batch_size=patches.shape[0])

                weight = np.zeros_like(test_image)
                temp_hr_image = np.zeros(test_image)
                temp_seg = np.zeros(test_image)

                for i in range(indice_patch.shape[0]):
                    temp_hr_image[indice_patch[i][0]:indice_patch[i][0] + patch1,
                    indice_patch[i][1]:indice_patch[i][1] + patch2,
                    indice_patch[i][2]:indice_patch[i][2] + patch3] += pred[
                                                                       i, 0,
                                                                       :, :,
                                                                       :]
                    temp_seg[indice_patch[i][0]:indice_patch[i][0] + patch1,
                    indice_patch[i][1]:indice_patch[i][1] + patch2,
                    indice_patch[i][2]:indice_patch[i][2] + patch3] += pred[i, 1, :, :, :]
                    weight[indice_patch[i][0]:indice_patch[i][0] + patch1,
                    indice_patch[i][1]:indice_patch[i][1] + patch2,
                    indice_patch[i][2]:indice_patch[i][2] + patch3] + np.ones_like(
                        weight[indice_patch[i][0]:indice_patch[i][0] + patch1,
                        indice_patch[i][1]:indice_patch[i][1] + patch2, indice_patch[i][2]:indice_patch[i][2] + patch3])
        # weight sum of patches
        print(GREEN+start+'\nDone !'+end+RESET)
        estimated_hr = temp_hr_image / weighted_image
        estimated_segmentation = temp_seg / weighted_image

        return estimated_hr, estimated_segmentation


def segmentation(input_file_path, step, new_resolution, path_output_cortex, path_output_hr, weights_path,
                 interpolation_type, patch=None, spline_order=3, by_batch=False, interp='scipy'):
    """

    :param input_file_path: path of the image to be super resolved and segmented
    :param step: the shifting step for the patches
    :param new_resolution: the new z-resolution we want for the output image
    :param path_output_cortex: output path of the segmented cortex
    :param path_output_hr: output path of the super resolution output image
    :param weights_path: the path of the file which contains the pre-trained weights for the neural network
    :param patch: the size of the patches
    :param spline_order: for the interpolation
    :param by_batch: to enable the by-batch processing
    :return:
    """
    # TestFile = path de l'image en entree
    # high_resolution = tuple des resolutions (par axe)

    # Get the generator kernel from the weights we are going to use
    print("Hey!")	
    weights = h5py.File(weights_path, 'r')
    print(weights_path)
    G = weights[list(weights.keys())[1]]
    print(G)
    weight_names = saving.load_attributes_from_hdf5_group(G, 'weight_names')
    print("Sai")
    for i in weight_names:
        if 'gen_conv1' in i:
            weight_values = G[i]
    first_generator_kernel = weight_values.shape[4]
    print("Image")
    # Get the generator kernel from the weights we are going to use

    D = weights[list(weights.keys())[0]]
    weight_names = saving.load_attributes_from_hdf5_group(D, 'weight_names')
    for i in weight_names:
        if 'conv_dis_1/kernel' in i:
            weight_values = D[i]
    first_discriminator_kernel = weight_values.shape[4]

    # Selection of the kind of network

    if "_nn_residual" in list(weights.keys())[1] :

        residual_string = "_nn_residual"
        is_residual = False

    else :

        residual_string=""
        is_residual = True


    if ('G_cond'+residual_string) == list(weights.keys())[1]:
        is_conditional = True
        u_net_gen = False
    elif ('G_unet'+residual_string) == list(weights.keys())[1]:
        is_conditional = False
        u_net_gen = True
    elif ('G_unet_cond'+residual_string) == list(weights.keys())[1] :
        is_conditional = True
        u_net_gen = True
    else:
        is_conditional = False
        u_net_gen = False

    # Check resolution
    if np.isscalar(new_resolution):
        new_resolution = (new_resolution, new_resolution, new_resolution)
    else:
        if len(new_resolution) != 3:
            raise AssertionError('Resolution not supported!')

    # Read low-resolution image
    if input_file_path.endswith('.nii'):
        image_instance = NIFTIReader(input_file_path)
    elif os.path.isdir(input_file_path):
        image_instance = DICOMReader(input_file_path)

    test_image = image_instance.get_np_array()
    test_imageMinValue = float(np.min(test_image))


    norm_instance = Normalization(test_image)


    test_imageNorm = norm_instance.get_normalized_image()[0] #zero indice means get only the normalized LR 


    resolution = image_instance.get_resolution()
    itk_image = image_instance.itk_image

    # Check scale factor type
    up_scale = tuple(itema / itemb for itema, itemb in zip(itk_image.GetSpacing(), new_resolution))

    # spline interpolation
    interpolated_image, up_scale = inter.Interpolation(test_imageNorm, up_scale, spline_order, interp,
                                                       interpolation_type). \
        get_interpolated_image(image_instance)

    if patch is not None:

        print("patch given")

        patch1 = patch2 = patch3 = int(patch)

        border = (
        int((interpolated_image.shape[0] - int(patch)) % step), int((interpolated_image.shape[1] - int(patch)) % step),
        int((interpolated_image.shape[2] - int(patch)) % step))

        border_to_add = (step - border[0], step - border[1], step - border[2])

        # padd border
        padded_interpolated_image = pad3D(interpolated_image, border_to_add)  # remove border of the image

    else:
        border = (
        int(interpolated_image.shape[0] % 4), int(interpolated_image.shape[1] % 4), int(interpolated_image.shape[2] %
                                                                                        4))
        border_to_add = (4 - border[0], 4 - border[1], 4 - border[2])

        padded_interpolated_image = pad3D(interpolated_image, border_to_add)  # remove border of the image

        height, width, depth = np.shape(padded_interpolated_image)
        patch1 = height
        patch2 = width
        patch3 = depth

    if ((step>patch1) |  (step>patch2) | (step>patch3)) & (patch is not None) :

        raise AssertionError('The step need to be smaller than the patch size')

    if (np.shape(padded_interpolated_image)[0]<patch1)|(np.shape(padded_interpolated_image)[1]<patch2)|(np.shape(padded_interpolated_image)[2]<patch3):

        raise AssertionError('The patch size need to be smaller than the interpolated image size')
    print("Just before the test")	
    # Loading weights
    segsrgan_test_instance = SegSRGAN_test(weights_path, patch1, patch2, patch3, is_conditional, u_net_gen,is_residual,
                                           first_generator_kernel, first_discriminator_kernel, resolution)
    print("After the test")
    # GAN
    print("Testing : ")
    estimated_hr_image, estimated_cortex = segsrgan_test_instance.test_by_patch(padded_interpolated_image, step=step,
                                                                             by_batch=by_batch)
    # parcours de l'image avec le patch

    # Padding
    # on fait l'operation de padding a l'envers
    padded_estimated_hr_image = shave3D(estimated_hr_image, border_to_add)
    estimated_cortex = shave3D(estimated_cortex, border_to_add)

    # SR image
    estimated_hr_imageInverseNorm = norm_instance.get_denormalized_result_image(padded_estimated_hr_image)
    estimated_hr_imageInverseNorm[
        estimated_hr_imageInverseNorm <= test_imageMinValue] = test_imageMinValue  # Clear negative value
    output_image = sitk.GetImageFromArray(np.swapaxes(estimated_hr_imageInverseNorm, 0, 2))
    output_image.SetSpacing(tuple(np.array(image_instance.itk_image.GetSpacing())/np.array(up_scale)))
    output_image.SetOrigin(itk_image.GetOrigin())
    output_image.SetDirection(itk_image.GetDirection())

    sitk.WriteImage(output_image, path_output_hr)

    # Cortex segmentation
    output_cortex = sitk.GetImageFromArray(np.swapaxes(estimated_cortex, 0, 2))
    output_cortex.SetSpacing(tuple(np.array(image_instance.itk_image.GetSpacing())/np.array(up_scale)))
    output_cortex.SetOrigin(itk_image.GetOrigin())
    output_cortex.SetDirection(itk_image.GetDirection())

    sitk.WriteImage(output_cortex, path_output_cortex)

    return "Segmentation Done"
