# -*-coding:utf-8-*-
import os
import tarfile

import tensorflow as tf
import matplotlib
import numpy as np
from object_detection.utils import ops as utils_ops

from utils import label_map_util
matplotlib.use('TkAgg')

MODEL_NAME = 'ssd_mobilenet_v1_coco_2017_11_17'
MODEL_FILE = 'model/'+MODEL_NAME + '.tar.gz'
PATH_TO_CKPT = 'model/'+MODEL_NAME + '/frozen_inference_graph.pb'
PATH_TO_LABELS = os.path.join('data', 'mscoco_label_map.pbtxt')
NUM_CLASSES = 90
tar_file = tarfile.open(MODEL_FILE)
threshold = 0.5
for file in tar_file.getmembers():
  file_name = os.path.basename(file.name)
  if 'frozen_inference_graph.pb' in file_name:
    tar_file.extract(file, os.getcwd())
    detection_graph = tf.Graph()

with detection_graph.as_default():
  od_graph_def = tf.compat.v1.GraphDef()
  with tf.compat.v1.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
    serialized_graph = fid.read()
    od_graph_def.ParseFromString(serialized_graph)
    tf.import_graph_def(od_graph_def, name='')
    label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
category_index = label_map_util.create_category_index(categories)

def load_image_into_numpy_array(image):
  (im_width, im_height) = image.size
  return np.array(image.getdata()).reshape(
      (im_height, im_width, 3)).astype(np.uint8)

def run_inference_for_single_image(image, graph):
  with graph.as_default():
    with tf.compat.v1.Session() as sess:
      ops = tf.compat.v1.get_default_graph().get_operations()
      all_tensor_names = {output.name for op in ops for output in op.outputs}
      tensor_dict = {}
      for key in [
          'num_detections', 'detection_boxes', 'detection_scores',
          'detection_classes', 'detection_masks'
      ]:
        tensor_name = key + ':0'
        if tensor_name in all_tensor_names:
          tensor_dict[key] = tf.compat.v1.get_default_graph().get_tensor_by_name(
              tensor_name)
      if 'detection_masks' in tensor_dict:
        detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
        detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
        real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
        detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
        detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
        detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
            detection_masks, detection_boxes, image.shape[0], image.shape[1])
        detection_masks_reframed = tf.cast(
            tf.greater(detection_masks_reframed, 0.5), tf.uint8)
        tensor_dict['detection_masks'] = tf.expand_dims(
            detection_masks_reframed, 0)
      image_tensor = tf.compat.v1.get_default_graph().get_tensor_by_name('image_tensor:0')

      # Run inference
      output_dict = sess.run(tensor_dict,
                             feed_dict={image_tensor: np.expand_dims(image, 0)})

      # all outputs are float32 numpy arrays, so convert types as appropriate
      output_dict['num_detections'] = int(output_dict['num_detections'][0])
      output_dict['detection_classes'] = output_dict[
          'detection_classes'][0].astype(np.uint8)
      output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
      output_dict['detection_scores'] = output_dict['detection_scores'][0]
      if 'detection_masks' in output_dict:
        output_dict['detection_masks'] = output_dict['detection_masks'][0]
  return output_dict

'''
interface for element detection
input: orgin image type:Image
output: image_np, the showing element's [box kind index](highly quality), all the box and kind index, the necessary index list
'''
def detect_image(image):
    image_np = load_image_into_numpy_array(image)
    output_dict = run_inference_for_single_image(image_np, detection_graph)
    detection_boxes, detection_classes, detection_scores = output_dict['detection_boxes'], output_dict['detection_classes'], output_dict['detection_scores'],
    boxs, classes, scores = [], [], []
    for i in range(len(detection_scores)):
        score = detection_scores[i]
        if score >= threshold:
            boxs.append(detection_boxes[i])
            classes.append(detection_classes[i])
            scores.append(score)
    return image_np, {'detection_boxes': boxs, 'detection_classes':classes, 'detection_scores':scores}, output_dict, category_index

kind_names = {0:'person', 1:'vehicle', 2:'facilities', 3:'scenery', 4:'animal',
         5:'daily use', 6:'sports goods', 7:'tableware', 8:'fruits', 9:'food',
         10:'vegetables', 11:'furniture', 12:'plant', 13:'Special location',14:'electronic product'}
kind_table = {1: 0, 2:1, 3:1, 4:1, 5:1, 6:1, 7:1, 8:1, 9:1, 10:2, 11:2, 12:2,
    13:2, 14:2, 15:3, 16:4, 17:4, 18:4, 19:4, 20:4, 21:4, 22:4, 23:4, 24:4,
    25:4, 27:5, 28:5, 31:5, 32:5, 33:5, 34:6, 35:6, 36:6, 37:6, 38:6, 39:6,
    40:6, 41:6, 42:6, 43:6, 44:7, 46:7, 47:7, 48:7, 49:7, 50:7, 51:7, 52:8,
    53:8, 54:9, 55:8, 56:10, 57:10, 58:9, 59: 9, 60: 9, 61:9, 62:11, 63:11,
    64:12, 65:11, 67: 11, 70:13, 72:11, 73:14, 74:14, 75:14, 76:14, 77:14,
    78:[11, 14], 79:[11,14], 80:[11,14], 81:11, 82:[11,14], 84: 5, 85: 5,
    86:5, 87:5, 88:5, 89:[11,14], 90:5}
category_contains_dict = {7:5, 8:9, 10:9, 14:5}


def image_kind(image):
    _, showing_output_dict, _, _ = detect_image(image)
    kind_name_list = []
    for class_index in showing_output_dict['detection_classes']:
        kind_index = kind_table[class_index]
        kind_name_list.append(kind_names[kind_index])
        if kind_index in category_contains_dict:
            kind_name_list.append(kind_names[category_contains_dict[kind_index]])
    return list(set(kind_name_list))
