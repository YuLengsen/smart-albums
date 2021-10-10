import sqlite3
import sys
from PIL import Image
import numpy
import time


db_name = './智能相册.db'


def create_images_to_face_table(cursor=None):
    conn = None
    need_close = False
    if cursor is None:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        need_close = True

    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS IMAGES_TO_FACE (IMAGE_ID INTEGER, FACE_ID INTEGER, DISTANCE DOUBLE, PRIMARY KEY (IMAGE_ID, FACE_ID));""")
    except Exception:
        print('创建IMAGES_TO_FACE表失败！')
        print(sys.exc_info()[1])

    if need_close:
        conn.commit()
        conn.close()


def insert_images_to_face_connect(image_id, face_id, distance, cursor=None):
    conn = None
    need_close = False
    if cursor is None:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        need_close = True

    create_images_to_face_table(cursor)
    try:
        cursor.execute("INSERT INTO IMAGES_TO_FACE (IMAGE_ID, FACE_ID, DISTANCE) VALUES (?, ?, ?);", (image_id, face_id, distance))
        # print(image_id, face_id, '成功插入')
    except Exception:
        print('插入image2face关系失败！')
        print(sys.exc_info())

    if need_close:
        conn.commit()
        conn.close()


# 尝试创建图片表
def create_images_table(cursor=None):
    conn = None
    need_close = False
    if cursor is None:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        need_close = True

    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS IMAGES (ID INTEGER PRIMARY KEY, IMAGE LONGBOLB UNIQUE, ROWS INTEGER, COLS INTEGER, DATETIME DOUBLE, NAME TEXT);""")
    except Exception:
        print('创建IMAGES表失败！')
        print(sys.exc_info()[1])

    if need_close:
        conn.commit()
        conn.close()


# 将图片加入图片表中
def insert_image(image, datetime, image_name, cursor=None):
    conn = None
    need_close = False
    if cursor is None:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        need_close = True

    # create_images_table(cursor)
    try:
        image_bytes = image.tobytes()
        rows, cols = image.size
        cursor.execute("INSERT INTO IMAGES (IMAGE, ROWS, COLS, DATETIME, NAME) VALUES (?, ?, ?, ?, ?);", (image_bytes, rows, cols, datetime, image_name))
    except Exception as e:
        print('插入图片失败！', e)
        print(sys.exc_info()[1])
        return -1

    image_id = cursor.lastrowid

    if need_close:
        conn.commit()
        conn.close()

    return image_id


def get_selected_images(image_ids, cursor=None):
    if not image_ids:
        return []

    conn = None
    need_close = False
    if cursor is None:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        need_close = True
    pass

    image_ids_condition = ''
    for image_id in image_ids:
        if image_ids_condition != '':
            image_ids_condition = image_ids_condition + ' OR'
        image_ids_condition = image_ids_condition + ' ID={}'.format(image_id)

    _images = []
    sql = 'SELECT IMAGE, COLS, ROWS FROM IMAGES'
    if image_ids_condition != '':
        sql = sql + ' WHERE' + image_ids_condition
    sql = sql + ' ORDER BY DATETIME ASC;'
    try:
        results = cursor.execute(sql)
        for _image, _cols, _rows in results:
            _images.append(Image.frombytes('RGB', (_rows, _cols), _image))
    except Exception:
        print('查询图片失败！')
        print(sys.exc_info()[1])

    if need_close:
        conn.commit()
        conn.close()

    return _images


def get_selected_image_ids(face_ids, date, cursor=None):
    conn = None
    need_close = False
    if cursor is None:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        need_close = True
    create_images_table(cursor)
    image_ids = []
    try:
        results = cursor.execute('SELECT ID FROM IMAGES;')
        for (image_id,) in results:
            image_ids.append(image_id)
        image_ids = set(image_ids)
    except Exception:
        results = []
        print('图片查询失败！')
        print(sys.exc_info()[1])

    for face_id in face_ids:
        try:
            results = cursor.execute('SELECT IMAGE_ID FROM IMAGES_TO_FACE WHERE FACE_ID=?;', (face_id,))
            selected_image = []
            for (image_id,) in results:
                selected_image.append(image_id)
            selected_image = set(selected_image)
            image_ids = image_ids & selected_image
        except Exception:
            results = []
            print(face_id, '查询失败！')
            print(sys.exc_info()[1])

        try:
            results = cursor.execute('SELECT IMAGE_ID FROM IMAGES_TO_FACE WHERE FACE_ID=?;', (face_id,))
            selected_image = []
            for (image_id,) in results:
                selected_image.append(image_id)
            selected_image = set(selected_image)
            image_ids = image_ids & selected_image
        except Exception:
            results = []
            print(face_id, '查询失败！')
            print(sys.exc_info()[1])

    if date[0] is not None:
        try:
            results = cursor.execute('SELECT ID FROM IMAGES WHERE DATETIME>?;', (date[0],))

            selected_image = []
            for (image_id,) in results:
                selected_image.append(image_id)
            selected_image = set(selected_image)
            image_ids = image_ids & selected_image
        except Exception:
            results = []
            print(date[0], '查询失败！')
            print(sys.exc_info()[1])

    if date[1] is not None:
        try:
            results = cursor.execute('SELECT ID FROM IMAGES WHERE DATETIME<?;', (date[1],))
            selected_image = []
            for (image_id,) in results:
                selected_image.append(image_id)
            selected_image = set(selected_image)
            image_ids = image_ids & selected_image
        except Exception:
            results = []
            print(date[1], '查询失败！')
            print(sys.exc_info()[1])

    image_ids = list(image_ids)

    if need_close:
        conn.commit()
        conn.close()

    return image_ids


def create_face_encodings_table(cursor=None):
    conn = None
    need_close = False
    if cursor is None:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        need_close = True

    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS FACE_ENCODINGS (ID INTEGER PRIMARY KEY, IMAGE LONGBOLB, ENCODING LONGBOLB, COLS INTEGER, ROWS INTEGER);""")
    except Exception:
        print('创建FACE_ENCODINGS表失败！')
        print(sys.exc_info()[1])

    if need_close:
        conn.commit()
        conn.close()


def get_known_face_encodings(cursor=None):
    conn = None
    need_close = False
    if cursor is None:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        need_close = True

    create_face_encodings_table(cursor)
    results = cursor.execute("SELECT ID, IMAGE, ENCODING, COLS, ROWS FROM FACE_ENCODINGS;")
    _ids = []
    _images = []
    _encodings = []
    for _id, _image, _encoding, _cols, _rows in results:
        _ids.append(_id)
        _images.append(Image.frombytes('RGB', (_rows, _cols), _image))
        _encodings.append(numpy.frombuffer(_encoding, dtype=float))

    if need_close:
        conn.commit()
        conn.close()

    return _ids, _images, _encodings


def insert_face_encoding(image, encoding, cursor=None):
    conn = None
    need_close = False
    if cursor is None:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        need_close = True

    create_images_table(cursor)
    try:
        image_bytes = image.tobytes()
        rows, cols = image.size
        encoding_bytes = encoding.tobytes()
        cursor.execute("INSERT INTO FACE_ENCODINGS (IMAGE, ENCODING, ROWS, COLS) VALUES (?, ?, ?, ?);", (image_bytes, encoding_bytes, rows, cols))
    except Exception:
        print('更新人脸失败！')
        print(sys.exc_info()[1])
        return -1

    face_id = cursor.lastrowid

    if need_close:
        conn.commit()
        conn.close()

    return face_id


def update_face_encoding(face_id, image, encoding, cursor=None):
    conn = None
    need_close = False
    if cursor is None:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        need_close = True

    create_images_table(cursor)
    try:
        image_bytes = image.tobytes()
        rows, cols = image.size
        encoding_bytes = encoding.tobytes()
        cursor.execute("UPDATE FACE_ENCODINGS SET IMAGE=?, ENCODING=?, ROWS=?, COLS=? WHERE ID=?;", (image_bytes, encoding_bytes, rows, cols, face_id))
        print('更新人脸{}成功'.format(face_id))
    except Exception:
        print('插入人脸失败！')
        print(sys.exc_info()[1])

    face_id = cursor.lastrowid

    if need_close:
        conn.commit()
        conn.close()

    return face_id


def main():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    results = cursor.execute("SELECT ID, IMAGE, ENCODING, COLS, ROWS FROM FACE_ENCODINGS;")
    _face_ids = []
    _face_images = []
    _face_encodings = []
    _face_id_to_index = {}
    for _id, _image, _encoding, _cols, _rows in results:
        _face_id_to_index[_id] = len(_face_ids)
        _face_ids.append(_id)
        _face_images.append(Image.frombytes('RGB', (_rows, _cols), _image))
        _face_encodings.append(_encoding)
        _face_images[-1].save('./test_result/face_{}.jpg'.format(str(_id)))

    results = cursor.execute("SELECT ID, IMAGE, COLS, ROWS, DATETIME, NAME FROM IMAGES;")
    _image_ids = []
    _images = []
    _image_id_to_index = {}
    for _id, _image, _cols, _rows, _datetime, _name in results:
        print(_id, _datetime, _name)
        _image_id_to_index[_id] = len(_image_ids)
        _image_ids.append(_id)
        _images.append(Image.frombytes('RGB', (_rows, _cols), _image))
        _images[-1].save('./test_result/image_{}.jpg'.format(str(_id)))

    results = cursor.execute("SELECT IMAGE_ID, FACE_ID, DISTANCE FROM IMAGES_TO_FACE;")
    for k, (image_id, face_id, distance) in enumerate(results):
        _image = _images[_image_id_to_index[image_id]]
        _face_image = _face_images[_face_id_to_index[face_id]]

        _face_image = _face_image.resize((_image.size[0], int(_face_image.size[1]*_image.size[0]/_face_image.size[0])), Image.BILINEAR)
        target_image = Image.new('RGB', (_image.size[0], _image.size[1] + _face_image.size[1]))
        target_image.paste(_face_image, (0, 0, _face_image.size[0], _face_image.size[1]))
        target_image.paste(_image, (0, _face_image.size[1], _image.size[0], _image.size[1] + _face_image.size[1]))
        target_image.save('./test_result/image2face_{}_{}.jpg'.format(str(k), distance))

    conn.close()


if __name__ == '__main__':
    main()
    # get_known_face_encodings()
