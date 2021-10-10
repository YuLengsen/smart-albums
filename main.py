# ///////////////////////////////////////////////////////////////
#
# BY: WANDERSON M.PIMENTA
# PROJECT MADE WITH: Qt Designer and PySide6
# V: 1.0.0
#
# This project can be used freely for all uses, as long as they maintain the
# respective credits only in the Python scripts, any information in the visual
# interface (GUI) can be modified without any implication.
#
# There are limitations on Qt licenses if you want to use your products
# commercially, I recommend reading them on the official website:
# https://doc.qt.io/qtforpython/licenses.html
#
# ///////////////////////////////////////////////////////////////
import imghdr
from tkinter import filedialog

import sys
import os
import platform

# IMPORT / GUI AND MODULES AND WIDGETS
# ///////////////////////////////////////////////////////////////
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QMainWindow, QGridLayout, QFileDialog, QMessageBox

import image_process_util
import myutil
from modules import *
import sqlite_util
from PIL import Image, ImageQt
import PIL
import time
from utils import visualization_utils as vis_util

from myutil import detect_image
from video_process_util import read_video

os.environ["QT_FONT_DPI"] = "96" # FIX Problem for High DPI and Scale above 100%

# SET AS GLOBAL WIDGETS
# ///////////////////////////////////////////////////////////////
widgets = None

class MyCheckBox(QCheckBox):
    face_id = -1
    image = None

g_checkbox_list = []

class MyLabel(QLabel):
    clicked = Signal()
    image = None
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            self.clicked.emit()

def _toqclass_helper(im):
    data = None
    colortable = None

    # handle filename, if given instead of image name
    if hasattr(im, "toUtf8"):
        im = str(im.toUtf8(), "utf-8")

    if im.mode == "1":
        format = QImage.Format_Mono
    elif im.mode == "L":
        format = QImage.Format_Indexed8
        colortable = []
        for i in range(256):
            colortable.append(PIL.rgb(i, i, i))
    elif im.mode == "P":
        format = QImage.Format_Indexed8
        colortable = []
        palette = im.getpalette()
        for i in range(0, len(palette), 3):
            colortable.append(PIL.rgb(*palette[i : i + 3]))
    elif im.mode == "RGB":
        data = im.tobytes("raw", "BGRX")
        format = QImage.Format_RGB32
    elif im.mode == "RGBA":
        try:
            data = im.tobytes("raw", "BGRA")
        except SystemError:
            # workaround for earlier versions
            r, g, b, a = im.split()
            im = Image.merge("RGBA", (b, g, r, a))
        format = QImage.Format_ARGB32
    else:
        raise ValueError("unsupported image mode %r" % im.mode)

    __data = data or PIL.align8to32(im.tobytes(), im.size[0], im.mode)
    return {"data": __data, "im": im, "format": format, "colortable": colortable}

class QtImage(QImage):
    def __init__(self, im):
        as_file = False
        self.img = im
        if as_file:
            im.save('./tmp.png')
            super().__init__('./tmp.png')
            return
        im_data = _toqclass_helper(im.convert('RGBA'))
        # must keep a reference, or Qt will crash!
        # All QImage constructors that take data operate on an existing
        # buffer, so this buffer has to hang on for the life of the image.
        # Fixes https://github.com/python-pillow/Pillow/issues/1370
        self.__data = im_data["data"]
        image = super().__init__(
            self.__data,
            im_data["im"].size[0],
            im_data["im"].size[1],
            im_data["format"],
        )
        if not im_data["colortable"] is None:
            image.setColorTable(im_data["colortable"])

        im_data['data'] = None
        print(im_data)
    def getImage(self):
        return self.img


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        # SET AS GLOBAL WIDGETS
        # ///////////////////////////////////////////////////////////////
        self.ui = Ui_MainWindow()
        # os.remove("智能相册.db")
        self.ui.setupUi(self)
        global widgets
        widgets = self.ui

        # USE CUSTOM TITLE BAR | USE AS "False" FOR MAC OR LINUX
        # ///////////////////////////////////////////////////////////////
        Settings.ENABLE_CUSTOM_TITLE_BAR = True

        # TOGGLE MENU
        # ///////////////////////////////////////////////////////////////
        widgets.toggleButton.clicked.connect(lambda: UIFunctions.toggleMenu(self, True))

        # SET UI DEFINITIONS
        # ///////////////////////////////////////////////////////////////
        UIFunctions.uiDefinitions(self)

        # QTableWidget PARAMETERS
        # ///////////////////////////////////////////////////////////////
        #widgets.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # BUTTONS CLICK
        # ///////////////////////////////////////////////////////////////

        # LEFT MENUS
        widgets.btn_home.clicked.connect(self.buttonClick)
        widgets.jieTu.clicked.connect(self.buttonClick)
        widgets.jianCe.clicked.connect(self.buttonClick)
        widgets.leiBieBiaoQian.clicked.connect(self.buttonClick)
        widgets.quChuChongFu.clicked.connect(self.buttonClick)
        widgets.daoRu.clicked.connect(self.buttonClick)
        widgets.daoChu.clicked.connect(self.buttonClick)
        # widgets.btn_new.clicked.connect(self.buttonClick)
        #widgets.btn_save.clicked.connect(self.buttonClick)

        # EXTRA LEFT BOX
        #def openCloseLeftBox():
            #UIFunctions.toggleLeftBox(self, True)
        #widgets.toggleLeftBox.clicked.connect(openCloseLeftBox)
        #widgets.extraCloseColumnBtn.clicked.connect(openCloseLeftBox)

        # EXTRA RIGHT BOX
        def openCloseRightBox():
            UIFunctions.toggleRightBox(self, True)
        widgets.settingsTopBtn.clicked.connect(openCloseRightBox)

        # SHOW APP
        # ///////////////////////////////////////////////////////////////
        self.show()

        # SET CUSTOM THEME
        # ///////////////////////////////////////////////////////////////
        useCustomTheme = False
        themeFile = "themes\py_dracula_light.qss"

        # SET THEME AND HACKS
        if useCustomTheme:
            # LOAD AND APPLY STYLE
            UIFunctions.theme(self, themeFile, True)

            # SET HACKS
            AppFunctions.setThemeHack(self)

        # SET HOME PAGE AND SELECT MENU
        # ///////////////////////////////////////////////////////////////
        widgets.stackedWidget.setCurrentWidget(widgets.home)
        widgets.btn_home.setStyleSheet(UIFunctions.selectMenu(widgets.btn_home.styleSheet()))


        widgets.search_button.clicked.connect(self.on_search_clicked)
        # widgets.daoRu.clicked.connect(self.on_daoRu_clicked)
        # 导入按钮这么写
        self._start_date = None
        self.current_picture = None
        self._end_date = None
        self.update_photo_list()
        self.update_checkbox_list()
    def info(self, text):
        msgBox = QMessageBox.about(self, u'提示', text)
        msgBox.setWindowFlags(Qt.CustomizeWindowHint)
        msgBox.exec_()  # 模态对话框

    def select_image_dir(self):
        img_end = {'jpg', 'bmp', 'png', 'jpeg', 'rgb', 'tif', 'tiff', 'gif', 'GIF'}
        dir_path = QFileDialog.getExistingDirectory(None,"选取文件夹")
        # try:
        image_files = []
        for image_file in os.listdir(dir_path):
            image_path = os.path.join(dir_path, image_file)
            if os.path.isfile(image_path) and imghdr.what(image_path) in img_end:
                image_files.append(image_path)
        for index, image_path in enumerate(image_files):
            print('开始处理', image_path, '进度', (index + 1), '/', len(image_files))
            # exif = image_process_util.get_exif(image_path)
            # print(exif)
            image_process_util.import_image(image_path)
        self.update_checkbox_list()
        self.update_photo_list()
        self.info("成功导入图片")

    def on_small_photo_clicked(self):
        small_photo_label = self.sender()
        self.current_picture = small_photo_label.image
        self.ui.photo_label.setPixmap(QPixmap.fromImage(small_photo_label.image.scaled(500,400)))
        self.ui.photo_classfy_label.setPixmap(QPixmap.fromImage(small_photo_label.image.scaled(50, 50)))
        self.ui.photo_classfy_label_1.setText("")

    def update_checkbox_list(self):
        ids, images, _ = sqlite_util.get_known_face_encodings()   #后端加接口？？？
        print('checkbox_list.count()', self.ui.checkbox_list.count())
        while self.ui.checkbox_list.count() > 0:
            self.ui.checkbox_list.takeAt(0).widget().deleteLater()

        for face_id, image in zip(ids, images):
            checkbox = MyCheckBox()
            checkbox.face_id = face_id;
            if isinstance(image, str):
                checkbox.setText(image)
            else:
                checkbox.image = QtImage(image).scaledToHeight(80)
                checkbox.setIcon(QPixmap.fromImage(checkbox.image))
                checkbox.setIconSize(QSize(80, 80))
            self.ui.checkbox_list.addWidget(checkbox)

    def export(self):
        dir_path = QFileDialog.getExistingDirectory(None, "导出到文件夹")
        face_ids = []
        for i in range(self.ui.checkbox_list.count()):
            checkbox = self.ui.checkbox_list.itemAt(i).widget()
            # checkbox = MyCheckBox()
            if checkbox.isChecked():
                face_ids.append(checkbox.face_id)

        layout = self.ui.photo_list.widget().layout()
        if layout is None:
            layout = QGridLayout()
            self.ui.photo_list.widget().setLayout(layout)
        else:
            while layout.count() > 0:
                layout.takeAt(0).widget().deleteLater()

        image_ids = sqlite_util.get_selected_image_ids(face_ids, (self._start_date, self._end_date))
        images = sqlite_util.get_selected_images(image_ids)
        for i in range(len(images)):
            images[i].save(os.path.join(dir_path,"{}.jpg".format(image_ids[i])))
        self.info("成功导出图片")


    def update_photo_list(self):
        face_ids = []
        for i in range(self.ui.checkbox_list.count()):
            checkbox = self.ui.checkbox_list.itemAt(i).widget()
            # checkbox = MyCheckBox()
            if checkbox.isChecked():
                face_ids.append(checkbox.face_id)


        layout = self.ui.photo_list.widget().layout()
        if layout is None:
            layout = QGridLayout()
            self.ui.photo_list.widget().setLayout(layout)
        else:
            while layout.count() > 0:
                layout.takeAt(0).widget().deleteLater()

        image_ids = sqlite_util.get_selected_image_ids(face_ids, (self._start_date, self._end_date))
        images = sqlite_util.get_selected_images(image_ids)
        show_box_height = self.ui.photo_list.minimumHeight() - 25
        for i, image in enumerate(images):
            #scale_image = image.resize((int(image.size[0] * show_box_height / image.size[1]),
            #                            int(image.size[1] * show_box_height / image.size[1])), Image.BILINEAR)
            qimage = QtImage(image)
            scale_image = qimage.scaledToHeight(show_box_height)
            small_photo_label = MyLabel()
            small_photo_label.setPixmap(QPixmap.fromImage(scale_image))
            small_photo_label.image = qimage
            small_photo_label.clicked.connect(self.on_small_photo_clicked)
            small_photo_label.setMinimumHeight(show_box_height)
            layout.addWidget(small_photo_label, 0, i)

    def on_search_clicked(self):
        self._start_date = self.ui.start_edit.text()
        self._end_date = self.ui.end_edit.text()
        print('search', self._start_date, self._end_date)
        self._start_date = time.mktime(time.strptime(self._start_date, '%Y/%m/%d'))
        self._end_date = time.mktime(time.strptime(self._end_date, '%Y/%m/%d'))
        print('search', self._start_date, self._end_date)
        self.update_photo_list()

    def jietu(self):
        img_end = {'jpg', 'bmp', 'png', 'jpeg', 'rgb', 'tif', 'tiff', 'gif', 'GIF'}
        openfile_name = QFileDialog.getOpenFileName(self, '选择视频', '')
        # read_video(openfile_name)
        dir_path = "tmp"
        image_files = []
        for image_file in os.listdir(dir_path):
            image_path = os.path.join(dir_path, image_file)
            if os.path.isfile(image_path) and imghdr.what(image_path) in img_end:
                image_files.append(image_path)
        for index, image_path in enumerate(image_files):
            print('开始处理', image_path, '进度', (index + 1), '/', len(image_files))
            # exif = image_process_util.get_exif(image_path)
            # print(exif)
            # image_process_util.import_image(image_path)
        self.update_checkbox_list()
        self.update_photo_list()
        self.info("已导入视频中标识人脸截图")

    def jiance(self):
        if self.current_picture != None:
            image = self.current_picture.getImage()
            print(type(image))
            image_np, myshow_output_dict, output_dict, category_index = detect_image(image)
            # Visualization of the results of a detection.
            vis_util.visualize_boxes_and_labels_on_image_array(
                image_np,
                output_dict['detection_boxes'],
                output_dict['detection_classes'],
                output_dict['detection_scores'],
                category_index,
                instance_masks=output_dict.get('detection_masks'),
                use_normalized_coordinates=True,
                line_thickness=8, min_score_thresh=myutil.threshold)
            obj_image = ImageQt.ImageQt(Image.fromarray(image_np))
            self.ui.photo_label.setPixmap(QPixmap.fromImage(obj_image.scaled(500, 400)))

    def getbiaoqian(self):
        if self.current_picture != None:
            image = self.current_picture.getImage()
            kind_name_list = myutil.image_kind(image)
            self.ui.photo_classfy_label_1.setText('\n'.join(kind_name_list))
    # BUTTONS CLICK
    # Post here your functions for clicked buttons
    # ///////////////////////////////////////////////////////////////
    def buttonClick(self):
        # GET BUTTON CLICKED
        btn = self.sender()
        btnName = btn.objectName()

        # SHOW HOME PAGE
        if btnName == "btn_home":
            widgets.stackedWidget.setCurrentWidget(widgets.home)
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        # SHOW WIDGETS PAGE
        if btnName == "daoRu":
            self.select_image_dir()
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        # SHOW WIDGETS PAGE
        if btnName == "daoChu":
            self.export()
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        # SHOW WIDGETS PAGE
        if btnName == "jieTu":
            self.jietu()
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        # SHOW WIDGETS PAGE
        if btnName == "quChuChongFu":
            self.set()
            self.info("已成功去重！")
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        # SHOW WIDGETS PAGE
        if btnName == "jianCe":
            self.jiance()
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        # SHOW WIDGETS PAGE
        if btnName == "leiBieBiaoQian":
            self.getbiaoqian()
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        #if btnName == "btn_save":
            #print("Save BTN clicked!")

        # PRINT BTN NAME
        print(f'Button "{btnName}" pressed!')



    # RESIZE EVENTS
    # ///////////////////////////////////////////////////////////////
    def resizeEvent(self, event):
        # Update Size Grips
        UIFunctions.resize_grips(self)

    # MOUSE CLICK EVENTS
    # ///////////////////////////////////////////////////////////////
    def mousePressEvent(self, event):
        # SET DRAG POS WINDOW
        self.dragPos = event.globalPos()

        # PRINT MOUSE EVENTS
        if event.buttons() == Qt.LeftButton:
            print('Mouse click: LEFT CLICK')
        if event.buttons() == Qt.RightButton:
            print('Mouse click: RIGHT CLICK')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.ico"))
    window = MainWindow()
    sys.exit(app.exec())
