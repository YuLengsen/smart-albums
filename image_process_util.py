import face_recognition
from PIL import Image, ExifTags
import numpy
import os
import sqlite_util
import time


known_face_ids, known_face_images, known_face_encodings = sqlite_util.get_known_face_encodings()
face_threshold = 0.41


def get_exif(image_path):
    img = Image.open(image_path)
    exif = {ExifTags.TAGS[k]: v
            for k, v in img.getexif().items()
            if k in ExifTags.TAGS
            }
    if exif.get('DateTime') is None:
        exif['DateTime'] = os.path.getctime(image_path)
    else:
        exif['DateTime'] = time.mktime(time.strptime(exif['DateTime'], '%Y:%m:%d %H:%M:%S'))
    return exif


def precess_one_direction(image, image_id):
    global known_face_ids, known_face_images, known_face_encodings

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

                results = face_recognition.face_distance(known_face_encodings, ec)

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
            face_image = known_face_images[face_id]
            face_id = known_face_ids[face_id]

        # 若找到匹配人脸，在图片id与人脸id之间构建关联关系
        if min_face_distance < face_threshold:
            sqlite_util.insert_images_to_face_connect(image_id, face_id, min_face_distance)

            # 比较新面部与已有面部的像素，选择像素较多的（更清晰）作为新的基准入库
            if (new_right - new_left) * (new_bottom - new_top) > face_image.size[0] * face_image.size[1] * 1.1:
                sqlite_util.update_face_encoding(face_id, crop_image, encoding)
                known_face_ids, known_face_images, known_face_encodings = sqlite_util.get_known_face_encodings()

        # 若无法识别人脸，将新的人脸入库
        else:
            face_id = sqlite_util.insert_face_encoding(crop_image, encoding)
            if face_id == -1:
                return
            sqlite_util.insert_images_to_face_connect(image_id, face_id, 0)
            # crop_image.save('{}_{}.jpg'.format(index, min_face_distance))
            # 将新的人脸加入对比列表
            known_face_ids.append(face_id)
            known_face_encodings.append(encoding)
            known_face_images.append(crop_image)


def compress(img, des = 8e5):
    w, h = img.size
    size = w*h
    if size <= des:
        return img
    radio = des / size
    return img.resize((int(w*radio), int(h*radio)))

# 导入一张照片
# 将图片入库，获取入库后的图片id
# 将图片中的人脸与库中人脸进行对比，在图片id与人脸id之间构建关联关系
# 将无法识别的人脸入库
# 比较两个面部图片的分辨率，将分辨率高的更新进数据库
def import_image(image_path):
    image_np = face_recognition.load_image_file(image_path)
    image = Image.fromarray(image_np)
    image = compress(image)
    # print('载入图片成功')

    exif = get_exif(image_path)
    datetime = exif['DateTime']
    image_name = os.path.basename(image_path)
    # 将图片入库，获取入库后的图片id
    image_id = sqlite_util.insert_image(image, datetime, image_name)
    print('存入图片成功')
    if image_id == -1:
        return

    precess_one_direction(image, image_id)
    # precess_one_direction(image.transpose(Image.ROTATE_90), image_id)
    precess_one_direction(image.transpose(Image.ROTATE_180), image_id)
    # precess_one_direction(image.transpose(Image.ROTATE_270), image_id)


if __name__ == '__main__':
    # 将数据库中的嵌入加入列表
    # 比较照片中的人与数据库中的人
    # 如果没有相同的人，则将其加入数据库
    # 如果有匹配的人，用分辨率更高的那个替换现有项
    # 尝试分析人物面部朝向，取正面朝向的照片替换现有项
    # 增大识别出的面部范围框，以确保保存的人脸更完整，
    pass
    # image = face_recognition.load_image_file("./picture/证件照.jpg")
    # print(image.shape)
    # face_locations = face_recognition.face_locations(image)
    # img = Image.fromarray(image)
    # for top, right, bottom, left in face_locations:
    #     print(top, bottom)
    #     img_piece = img.crop((left, top, right, bottom))
    #     img_piece.save('test.jpg')

    # face_landmarks_list = face_recognition.face_landmarks(image)
    # print(face_landmarks_list)

    # known_face_encodings = []
    # image = face_recognition.load_image_file("./picture/证件照.jpg")
    # known_face_encodings.extend(face_recognition.face_encodings(image, num_jitters=5, model='large'))
    # image = face_recognition.load_image_file("./picture/报名照片.jpg")
    # known_face_encodings.extend(face_recognition.face_encodings(image, num_jitters=5, model='large'))
    #
    # image = face_recognition.load_image_file("./picture/识别照片4.jpg")
    # img = Image.fromarray(image)
    # face_locations = face_recognition.face_locations(image)
    # for k, (top, right, bottom, left) in enumerate(face_locations):
    #     img_piece = img.crop((left, top, right, bottom))
    #     img_piece.save('test_{}.jpg'.format(str(k)))
    # encodings = face_recognition.face_encodings(image, face_locations, 5, 'large')
    #
    # for encoding in encodings:
    #     results = face_recognition.compare_faces(known_face_encodings, encoding, 0.45)
    #     print(results)

