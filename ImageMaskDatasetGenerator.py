# Copyright 2024 antillia.com Toshiyuki Arai
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# 2024/07/08 
# ImageMaskDatasetGenerator.py

import os
import sys
import shutil
import cv2
import glob
import numpy as np
import nibabel as nib
import traceback
from PIL import Image

# Read a nii.gz file
"""
scan = nib.load('/path/to/stackOfimages.nii.gz')
# Get raw data
scan = scan.get_fdata()
print(scan.shape)
(num, width, height)

"""

class ImageMaskDatasetGenerator:

  def __init__(self, 
               skip_empty_mask= True, 
               rotation       = 270, 
               normalize      = True, 
               resize         = 512,
               image_format   = ".png",
               mask_format    = ".png"):
   self.skip_empty_mask = skip_empty_mask
   self.mask_factor = 255
   self.rotation    = rotation
   self.image_normalize   = normalize
   self.RESIZE     = resize
   self.image_format = image_format
   self.mask_format  = mask_format

  def create_mask_files(self, niigz, output_masks_dir, index):    
    print("--- create_mask_file nii.gz {}".format(niigz))
    nii = nib.load(niigz)
    #print("--- nii {}".format(nii))
    data = nii.get_fdata()
    print("---data mask shape {} len {}".format(data.shape, len(data.shape)))
    
    if len(data.shape) > 3:
      print("--- Invalid mask shape {}".format(data.shape))
      return 0
    
    num_images = data.shape[2] # math.floor(data.shape[2]/2)
    print("--- num_images {}".format(num_images))
    num = 0
    for i in range(num_images):
      img = data[:, :,i]
      img = np.array(img)
      w = img.shape[0]
      h = img.shape[1]
      img = np.reshape(img, (w, h))
      img = img * self.mask_factor
      img = img.astype(np.uint32)
      
      filename = str(index) + "_" + str(i) + self.mask_format
      if self.skip_empty_mask:
        if np.any(img > 0):
          filepath = os.path.join(output_masks_dir, filename)
          img = self.resize_to_square(img)
          if self.rotation > 0:
            img = img.rotate(self.rotation, resample=Image.NEAREST, expand=0)
          img = img.convert('L')
          img.save(filepath)
          print("=== Saved {}".format(filepath))
          num += 1
        else:
          print("=== Skipped empty black mask")
    return num
    
  def create_image_files(self, niigz, output_images_dir, output_mask_dir, index):     
    print("--- create_image_files niigz {}".format(niigz))
    nii = nib.load(niigz)
    #print("--- nii {}".format(nii))
    data = nii.get_fdata()
    print("---data shape {} ".format(data.shape))
 
    #data = np.asanyarray(nii.dataobj)
    num_images = data.shape[2] # math.floor(data.shape[2]/2)
    print("--- num_images {}".format(num_images))
    num = 0
    for i in range(num_images):
      img = data[:,:,i]
      print("---img shape {}".format(img.shape))
      if len(img.shape)>2:
       img = img[:,:,0]
       print(">>>img shape {}".format(img.shape))
      
      img = np.array(img).astype(np.uint32)
      if self.image_normalize:
        img = self.normalize(img)

      filename  = str(index) + "_" + str(i) + self.image_format
      mfilename = str(index) + "_" + str(i) + self.mask_format
      mask_filepath = os.path.join(output_masks_dir, mfilename )
      filepath = os.path.join(output_images_dir, filename)

      if os.path.exists(mask_filepath):
        img = self.resize_to_square(img)
        if self.rotation > 0:
          img = img.rotate(self.rotation, resample=Image.NEAREST, expand=0)
        img.save(filepath)

        print("=== Saved {}".format(filepath))
        num += 1
      else:
        print("==== Skiped {}".format(filepath))
    return num
      

  def generate(self, images_dir, labels_dir,
               output_images_dir, output_masks_dir):
      image_files = glob.glob(images_dir + "/*.nii.gz")
      label_files = glob.glob(labels_dir + "/*.nii.gz")
      num_image_files = len(image_files)
      num_label_files = len(label_files)
      print("=== num_images {}".format(num_image_files))
      print("=== num_labels {}".format(num_label_files))
      if num_image_files != num_label_files:
          raise Exception("Num images and labels are different ")
      index    = 10000
      num_data = num_image_files // 2

      for i in range(num_data):
        index += i
        image_file = image_files[i]
        label_file = label_files[i]
        num_masks  = self.create_mask_files(label_file, output_masks_dir,  index)
        num_images = self.create_image_files(image_file, output_images_dir, output_masks_dir, index)

        if num_images != num_masks:
          raise Exception("Number of images and labels are mismatched.")

  def normalize(self, image):
    min = np.min(image)/255.0
    max = np.max(image)/255.0
    scale = (max - min)
    image = (image - min) / scale
    image = image.astype(np.uint32) 
    return image   

  def resize_to_square(self, cvimage):
     cvimage = cvimage.astype(np.uint32)
     image = Image.fromarray(cvimage)
     w, h  = image.size

     bigger = w
     if h > bigger:
       bigger = h

     background = Image.new("RGB", (bigger, bigger), (0, 0, 0))
    
     x = (bigger - w) // 2
     y = (bigger - h) // 2
     background.paste(image, (x, y))
     background = background.resize((self.RESIZE, self.RESIZE))

     return background
  
  # You may need to convert the color.
  #img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
  #im_pil = Image.fromarray(img)
  def pil2cv(self, image):
    new_image = np.array(image, dtype=np.uint32)
    if new_image.ndim == 2: 
        pass
    elif new_image.shape[2] == 3: 
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGB2BGR)
    elif new_image.shape[2] == 4: 
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGBA2BGRA)
    return new_image
  
  
if __name__ == "__main__":
  try:
    images_dir        = "./t2/imagesTr"
    labels_dir        = "./t2/labelsTr"
    output_dir        = "./Pancreas-T2-master"
    output_images_dir = "./Pancreas-T2-master/images/"
    output_masks_dir  = "./Pancreas-T2-master/masks/"

    if os.path.exists(output_dir):
      shutil.rmtree(output_dir)
    if not os.path.exists(output_dir):
      os.makedirs(output_dir)

    os.makedirs(output_images_dir)  
    os.makedirs(output_masks_dir)

    # Create 512x512 jpg image and mask files from nii.gz files under.
    # /t2
    # +-- imagesTr
    # +-- labelsTr
    skip_empty_mask= True
    rotation       = 270
    normalize      = True
    resize         = 512
    image_format   = ".jpg"
    mask_format    = ".jpg"

    generator = ImageMaskDatasetGenerator(skip_empty_mask= skip_empty_mask,
                                          rotation       = rotation,
                                          normalize      = normalize,
                                          resize         = resize,
                                          image_format   = image_format,
                                          mask_format    = mask_format)
    
    generator.generate(images_dir, labels_dir, output_images_dir, output_masks_dir)

  except:
    traceback.print_exc()


