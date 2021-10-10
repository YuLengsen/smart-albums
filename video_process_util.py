import cv2
import image_process_util
import face_recognition
from PIL import Image
import numpy
import sqlite_util
import time


def precess_one_direction(image):
    print(type(image))
    image = Image.fromarray(image)
    print(type(image))
    face_list = []
    image_np = numpy.array(image)
    # 将图片中的人脸与库中人脸进行对比
    face_locations = face_recognition.face_locations(image_np, 1, model='cnn')
    # face_locations = face_recognition.face_locations(image_np, 1)
    # encodings = face_recognition.face_encodings(image_np, face_locations, 1, model='large')
    # print('特征抽取成功')
    for index, (top, right, bottom, left) in enumerate(face_locations):
        # top, right, bottom, left = face_locations[index]
        new_right = min(int(1.5 * right - 0.5 * left), image_np.shape[1])
        new_left = max(int(1.5 * left - 0.5 * right), 0)
        new_top = max(int(1.5 * top - 0.5 * bottom), 0)
        new_bottom = min(int(1.5 * bottom - 0.5 * top), image_np.shape[0])
        crop_image = image.crop((new_left, new_top, new_right, new_bottom))
        # crop_image.save('{}_{}_{}_{}_{}.jpg'.format(index, top, right, bottom, left))

        # 计算面部4个方向的特征表示，判断面部是否已存在
        crop_images = [crop_image, crop_image.transpose(Image.ROTATE_90), crop_image.transpose(Image.ROTATE_180), crop_image.transpose(Image.ROTATE_270)]
        # crop_images = [crop_image]

        encoding = None
        crop_image = None
        face_id = None
        face_image = None
        min_face_distance = 1
        candidate_face_id = []

        for ci in crop_images:
            # 使用cnn对截取的人脸做二次检测，排除错误面部
            # tmp = face_recognition.face_locations(numpy.array(ci), 2, model='cnn')
            encodings = face_recognition.face_encodings(numpy.array(ci), model='large')
            for ec in encodings:
                if encoding is None:
                    encoding = ec
                    crop_image = ci

                results = face_recognition.face_distance(image_process_util.known_face_encodings, ec)

                for i, result in enumerate(results):
                    if result < min_face_distance:
                        min_face_distance = result
                        crop_image = ci
                        encoding = ec
                        face_id = i

        # 利用2次检测，排除错误是宝宝的人脸
        if encoding is None:
            continue

        if face_id is not None:
            face_image = image_process_util.known_face_images[face_id]
            face_id = image_process_util.known_face_ids[face_id]

        # 若找到匹配人脸，在图片id与人脸id之间构建关联关系
        if min_face_distance < image_process_util.face_threshold:
            face_list.append((face_id, min_face_distance))

    return face_list


def read_video(video_path):
    vc = cv2.VideoCapture(video_path)
    c = 0
    if vc.isOpened():  # 判断是否正常打开
        print("yes")
        rval, frame = vc.read()
    else:
        rval = False
        print("false")
    rval = False
    timeF = 180
    while rval:  # 循环读取视频帧
        rval, frame = vc.read()
        if c % timeF == 0:  # 每隔timeF帧进行操作
            face_list = precess_one_direction(frame)
            if len(face_list) > 0:
                img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image_id = sqlite_util.insert_image(img_pil, time.time(), video_path + '_', str(c))
                for face in face_list:
                    face_id = face[0]
                    min_face_distance = face[1]
                    sqlite_util.insert_images_to_face_connect(image_id, face_id, min_face_distance)
        c = c + 1
    cv2.waitKey(1)
    vc.release()

if __name__ == "__main__":
    read_video("/home/dmx/桌面/smart-albums-interfaces/video.mp4")