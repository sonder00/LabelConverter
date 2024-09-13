import base64
import os
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom

from PIL import Image
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QWidget, QLabel, \
    QMessageBox, QInputDialog
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QDialog, QPushButton

import json


class LabelConverter(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("数据标签转换器")
        self.setGeometry(200, 200, 400, 300)

        # 初始化标签映射字典
        self.label_mapping = {}
        # 创建界面组件
        self.label = QLabel("请选择一个文件夹进行转换", self)
        self.load_button = QPushButton("加载数据", self)
        self.load_button.clicked.connect(self.on_load_button_clicked)

        # 布局
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.load_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def convert_files(self, folder_path, format_choice, image_folder_path):
        """转换主逻辑"""
        files = os.listdir(folder_path)
        json_files = [f for f in files if f.endswith('.json')]
        xml_files = [f for f in files if f.endswith('.xml')]
        yolo_files = [f for f in files if f.endswith('.txt')]
        output_folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")

        # 检查 YOLO 格式转换时标签是否为数字
        if format_choice in ["YOLO检测", "YOLO分割", "JSON 转 YOLO", "XML 转 YOLO"]:
            all_labels = set()

            # 获取所有的标签
            for json_file in json_files:
                with open(os.path.join(folder_path, json_file), 'r') as f:
                    data = json.load(f)
                    for shape in data['shapes']:
                        label = shape['label']
                        # 优先使用修改后的标签
                        label = self.label_mapping.get(label, label)
                        all_labels.add(label)

            for xml_file in xml_files:
                tree = ET.parse(os.path.join(folder_path, xml_file))
                root = tree.getroot()
                for obj in root.findall('object'):
                    class_id = obj.find('name').text
                    # 优先使用修改后的标签
                    class_id = self.label_mapping.get(class_id, class_id)
                    all_labels.add(class_id)

            # 检查是否有非数字标签
            non_numeric_labels = [label for label in all_labels if not self.is_numeric_label(label)]
            if non_numeric_labels:
                # 弹出错误提示，要求标签为数字
                QMessageBox.warning(self, "警告", "YOLO 格式要求标签为数字。请修改标签。")

                # 强制弹出修改标签窗口
                self.show_label_change_dialog(all_labels, folder_path, image_folder_path)
                return  # 终止转换，等待用户修改标签

        if not output_folder:
            QMessageBox.warning(self, "警告", "未选择输出文件夹，操作已取消。")
            return
        if format_choice == "XML 转 JSON" and json_files:
            QMessageBox.critical(self, "错误", "已加载 JSON 文件，无法执行 XML 转 JSON 转换。")
            return
        if format_choice == "JSON 转 XML" and xml_files:
            QMessageBox.critical(self, "错误", "已加载 XML 文件，无法执行 JSON 转 XML 转换。")
            return
        if format_choice == "YOLO 转 XML" and (xml_files or json_files):
            QMessageBox.critical(self, "错误", "已加载 XML 或 JSON 文件，无法执行 YOLO 转 XML 转换。")
            return
        if format_choice == "YOLO 转 JSON" and json_files:
            QMessageBox.critical(self, "错误", "已加载 JSON 文件，无法执行 YOLO 转 JSON 转换。")
            return
        if format_choice == "YOLO检测" and yolo_files:
            QMessageBox.critical(self, "错误", "已加载 YOLO 文件，无法执行 YOLO 转换。")
            return
        if format_choice == "YOLO分割" and yolo_files:
            QMessageBox.critical(self, "错误", "已加载 YOLO 文件，无法执行 YOLO 转换。")
            return
        # 如果选择了 "JSON 转 XML"，先检查所有 JSON 文件是否包含非 rectangle 的 shape_type
        if format_choice == "JSON 转 XML":
            if not self.check_json_files_for_rectangle(json_files, folder_path):
                QMessageBox.critical(self, "错误", "文件夹中包含非矩形标注 (shape_type 不是 rectangle)，无法进行转换！")
                return
        # 执行转换时根据 self.label_mapping 替换标签名
        for json_file in json_files:
            if format_choice == "JSON 转 XML":
                self.convert_json_to_xml(os.path.join(folder_path, json_file), output_folder)
            else:
                self.convert_json_to_txt(os.path.join(folder_path, json_file), format_choice, output_folder)
        for xml_file in xml_files:
            if format_choice == "XML 转 JSON":
                image_file = self.find_image_for_file(xml_file, image_folder_path)
                if image_file:
                    self.convert_xml_to_json(os.path.join(folder_path, xml_file), output_folder, image_file)
            elif format_choice == "YOLO检测":
                self.convert_xml_to_yolo(os.path.join(folder_path, xml_file), output_folder)
            elif format_choice == "YOLO分割":
                QMessageBox.critical(self, "错误", "无法将xml文件转为YOLO分割格式。")
                return
            else:
                QMessageBox.critical(self, "错误","错误加载了xml文件。")
                return
        for yolo_file in yolo_files:
            if format_choice == "YOLO 转 XML":
                result = self.convert_yolo_to_xml(os.path.join(folder_path, yolo_file), output_folder)
                if result == "error":  # 检测到错误时，停止整个转换流程
                    return
            elif format_choice == "YOLO 转 JSON":
                image_file = self.find_image_for_file(yolo_file, image_folder_path)
                if image_file:
                    self.convert_yolo_to_json(os.path.join(folder_path, yolo_file), output_folder, image_file)
        # 在转换完成后清空标签映射
        self.label_mapping = {}
        self.label.setText("转换完成!")

    def get_image_data(self, image_path):
        """读取图像文件，返回其 Base64 编码数据以及图像宽度和高度"""
        with open(image_path, 'rb') as img_file:
            image_data = img_file.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')

        with Image.open(image_path) as img:
            image_width, image_height = img.size

        return image_base64, image_width, image_height
    
    def find_image_for_file(self, annotation_file, image_folder_path):
        """根据标注文件找到对应的图像文件"""
        base_name = os.path.splitext(os.path.basename(annotation_file))[0]  # 获取文件名，不带扩展名
        image_extensions = ['.jpg', '.jpeg', '.png']  # 常见图像格式

        # 遍历图像文件夹中的图像，找到匹配的图像
        for ext in image_extensions:
            image_path = os.path.join(image_folder_path, base_name + ext)
            if os.path.exists(image_path):
                return image_path

        # 如果没有找到匹配的图像文件，返回 None
        QMessageBox.warning(self, "警告", f"未找到与 {annotation_file} 对应的图像文件。")
        return None

    def on_load_button_clicked(self):
        # 选择数据文件夹
        folder_path = QFileDialog.getExistingDirectory(self, "选择数据文件夹")

        if folder_path:
            # 检查文件夹中的文件类型
            files = os.listdir(folder_path)
            json_files = [f for f in files if f.endswith('.json')]
            xml_files = [f for f in files if f.endswith('.xml')]
            yolo_files = [f for f in files if f.endswith('.txt')]
            if not json_files and not xml_files and not yolo_files:
                QMessageBox.warning(self, "警告", "文件夹中没有可转换的文件（JSON、XML 或 YOLO）")
                return

            # 选择图像文件夹
            image_folder_path = QFileDialog.getExistingDirectory(self, "选择图像文件夹")
            if not image_folder_path:
                QMessageBox.warning(self, "警告", "未选择图像文件夹，操作已取消。")
                return

            # 提取所有类别名并提示
            has_polygon = False
            has_rectangle = False
            has_yolo = False
            all_labels = set()  # 用于存储所有类别名

            # 从文件夹中提取标注信息
            for json_file in json_files:
                with open(os.path.join(folder_path, json_file), 'r') as f:
                    data = json.load(f)
                    for shape in data['shapes']:
                        shape_type = shape.get('shape_type')
                        if shape_type == 'polygon':
                            has_polygon = True
                        elif shape_type == 'rectangle':
                            has_rectangle = True
                        all_labels.add(shape['label'])

            # 处理 XML 文件
            for xml_file in xml_files:
                tree = ET.parse(os.path.join(folder_path, xml_file))
                root = tree.getroot()
                for obj in root.findall('object'):
                    class_id = obj.find('name').text
                    all_labels.add(class_id)

            # 提取 YOLO 文件中的类别名
            for yolo_file in yolo_files:
                with open(os.path.join(folder_path, yolo_file), 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            class_id = parts[0]
                            all_labels.add(class_id)
                has_yolo = True

            # 根据检测到的标注类型，统一弹出提示框
            if has_polygon and has_rectangle:
                QMessageBox.information(self, "信息", "文件夹中包含多边形和矩形标注")
            elif has_polygon:
                QMessageBox.information(self, "信息", "文件夹中包含多边形标注（polygon）")
            elif has_rectangle:
                QMessageBox.information(self, "信息", "文件夹中包含矩形标注（rectangle）")
            elif has_yolo:
                QMessageBox.information(self, "信息", "文件夹中包含 YOLO 格式文件")

            # 显示所有类别名
            if all_labels:
                labels_list = "\n".join(sorted(all_labels))
                QMessageBox.information(self, "类别名", f"标签名包含以下类别:\n{labels_list}")

            # 询问是否要更改标签名
            reply = QMessageBox.question(self, "更改标签名", "是否要更改标签名？", QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)

            if reply == QMessageBox.Yes:
                # 调用函数弹出标签修改窗口
                self.show_label_change_dialog(all_labels, folder_path, image_folder_path)
            else:
                # 选择转换格式
                format_options = ["YOLO检测", "YOLO分割", "JSON 转 XML", "XML 转 JSON", "YOLO 转 XML", "YOLO 转 JSON"]
                format_choice, ok = QInputDialog.getItem(self, "选择格式", "请选择转换格式:", format_options, 0, False)

                if ok:
                    self.convert_files(folder_path, format_choice, image_folder_path)

    def check_json_files_for_rectangle(self, json_files, folder_path):
        """检查所有 JSON 文件是否包含非 rectangle 的 shape_type"""
        for json_file in json_files:
            with open(os.path.join(folder_path, json_file), 'r') as f:
                data = json.load(f)

            shapes = data.get('shapes', [])
            for shape in shapes:
                shape_type = shape.get('shape_type')
                if shape_type != 'rectangle':
                    return False
        return True

    def is_numeric_label(self, label):
        """检查标签是否为数字"""
        try:
            float(label)  # 尝试将标签转换为浮点数
            return True
        except ValueError:
            return False

    def show_label_change_dialog(self, all_labels, folder_path, image_folder_path):
        """改标签窗口"""
        dialog = QDialog(self)
        dialog.setWindowTitle("更改标签名")

        # 创建表格
        table = QTableWidget(len(all_labels), 2)
        table.setHorizontalHeaderLabels(["原标签名", "新标签名"])

        # 填充左边的表格为原标签名
        for row, label in enumerate(sorted(all_labels)):
            table.setItem(row, 0, QTableWidgetItem(label))
            table.setItem(row, 1, QTableWidgetItem(""))  # 右边一栏供用户输入新标签名

        # 完成按钮
        done_button = QPushButton("完成")
        done_button.clicked.connect(lambda: self.save_label_changes(dialog, table, all_labels, folder_path, image_folder_path))

        # 布局
        layout = QVBoxLayout()
        layout.addWidget(table)
        layout.addWidget(done_button)
        dialog.setLayout(layout)
        dialog.exec_()

    def save_label_changes(self, dialog, table, all_labels, folder_path, image_folder_path):
        """保存标签更改并生成原标签到新标签的映射"""
        self.label_mapping = {}  # 初始化原标签到新标签的映射
        for row, label in enumerate(sorted(all_labels)):
            original_label = label
            new_label = table.item(row, 1).text().strip()  # 获取用户输入的新标签名
            if new_label:
                if not self.is_numeric_label(new_label):  # 检查新标签是否为数字
                    QMessageBox.warning(self, "警告", f"标签 '{new_label}' 不是数字。YOLO 格式要求标签为数字。")
                    return  # 如果标签不是数字，阻止保存并警告
                self.label_mapping[original_label] = new_label  # 如果用户输入新标签，则进行映射
            else:
                self.label_mapping[original_label] = original_label  # 如果没有输入新标签，则保持不变
        dialog.accept()

        # 弹出格式选择对话框
        format_options = ["YOLO检测", "YOLO分割", "JSON 转 XML", "XML 转 JSON", "YOLO 转 XML", "YOLO 转 JSON"]
        format_choice, ok = QInputDialog.getItem(self, "选择格式", "请选择转换格式:", format_options, 0, False)

        if ok:
            # 调用文件转换函数，传递实际的文件夹路径
            self.convert_files(folder_path, format_choice, image_folder_path)
    def convert_xml_to_yolo(self, xml_file, output_folder):
        """将 XML 文件转换为 YOLO 格式 TXT 文件"""
        tree = ET.parse(xml_file)
        root = tree.getroot()
        output_file = os.path.join(output_folder, os.path.basename(xml_file).replace('.xml', '.txt'))

        with open(output_file, 'w') as out_file:
            for obj in root.findall('object'):  # 处理多个标签
                class_id = obj.find('name').text

                # 如果 label_mapping 为空，则直接使用原始的标签名
                if self.label_mapping:
                    class_id = self.label_mapping.get(class_id, class_id)

                bbox = obj.find('bndbox')
                xmin = float(bbox.find('xmin').text)
                ymin = float(bbox.find('ymin').text)
                xmax = float(bbox.find('xmax').text)
                ymax = float(bbox.find('ymax').text)

                # 计算中心点坐标和宽高
                center_x = (xmin + xmax) / 2
                center_y = (ymin + ymax) / 2
                width = xmax - xmin
                height = ymax - ymin
                # 输出为 YOLO 格式：class_id center_x center_y width height
                out_file.write(f"{class_id} {center_x} {center_y} {width} {height}\n")

    def convert_json_to_txt(self, json_file, format_choice, output_folder):
        """将 JSON 文件转换为 YOLO检测/分割格式的 TXT 文件"""
        with open(json_file, 'r') as f:
            data = json.load(f)

        output_file = os.path.join(output_folder, os.path.basename(json_file).replace('.json', '.txt'))
        image_width = data.get('imageWidth', 1)  # 防止除以 0，默认宽度为 1
        image_height = data.get('imageHeight', 1)  # 防止除以 0，默认高度为 1

        with open(output_file, 'w') as out_file:
            for shape in data['shapes']:
                label = shape['label']

                # 如果 label_mapping 为空，则直接使用原始的标签名
                class_id = self.label_mapping.get(label, label) if self.label_mapping else label

                if format_choice == "YOLO检测" and shape['shape_type'] == 'rectangle':
                    # 处理 rectangle 目标检测格式
                    points = shape['points']
                    xmin, ymin = points[0]
                    xmax, ymax = points[1]
                    center_x = (xmin + xmax) / 2
                    center_y = (ymin + ymax) / 2
                    width = xmax - xmin
                    height = ymax - ymin
                    out_file.write(f"{class_id} {center_x} {center_y} {width} {height}\n")
                elif format_choice == "YOLO分割" and shape['shape_type'] == 'polygon':
                    # 处理 polygon 分割格式
                    points = shape['points']
                    out_file.write(f"{class_id} ")
                    for point in points:
                        x_normalized = point[0] / image_width
                        y_normalized = point[1] / image_height
                        out_file.write(f"{x_normalized} {y_normalized} ")
                    out_file.write("\n")

    def convert_json_to_xml(self, json_file, output_folder):
        """将包含矩形标注的 JSON 转换为 XML"""
        with open(json_file, 'r') as f:
            data = json.load(f)

        shapes = data.get('shapes', [])

        # 用于记录是否存在非矩形的 shape_type
        non_rectangle_shapes = [shape for shape in shapes if shape.get('shape_type') != 'rectangle']

        if non_rectangle_shapes:
            # 弹出错误提示，只弹出一次，说明只支持 rectangle 转换
            QMessageBox.critical(self, "错误", "JSON 文件中包含非矩形标注 (shape_type 不是 rectangle)，无法进行转换！")
            return

        # 创建 XML 根节点
        root = ET.Element("annotation")

        for shape in shapes:
            if shape.get('shape_type') == 'rectangle':
                points = shape['points']
                xmin, ymin = points[0]
                xmax, ymax = points[1]

                # 创建 XML 对象节点
                obj = ET.SubElement(root, "object")
                name = ET.SubElement(obj, "name")
                name.text = shape['label']

                bndbox = ET.SubElement(obj, "bndbox")
                ET.SubElement(bndbox, "xmin").text = str(int(xmin))
                ET.SubElement(bndbox, "ymin").text = str(int(ymin))
                ET.SubElement(bndbox, "xmax").text = str(int(xmax))
                ET.SubElement(bndbox, "ymax").text = str(int(ymax))

        # 保存为 XML 文件
        xml_file = os.path.join(output_folder, os.path.basename(json_file).replace('.json', '.xml'))
        xml_str = ET.tostring(root, encoding='unicode')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="   ")

        with open(xml_file, 'w') as f:
            f.write(pretty_xml)
        print(f"文件已成功转换为 {xml_file}")

    def convert_xml_to_json(self, xml_file, output_folder, image_file):
        """将包含矩形标注的 XML 转换为 LabelMe JSON 格式"""
        tree = ET.parse(xml_file)
        root = tree.getroot()
        shapes = []
        # 调用时只传递 image_file 路径
        image_data, image_width, image_height = self.get_image_data(image_file)

        for obj in root.findall('object'):
            name = obj.find('name').text
            bbox = obj.find('bndbox')
            xmin = int(float(bbox.find('xmin').text))
            ymin = int(float(bbox.find('ymin').text))
            xmax = int(float(bbox.find('xmax').text))
            ymax = int(float(bbox.find('ymax').text))

            shapes.append({
                "label": name,
                "points": [[xmin, ymin], [xmax, ymax]],
                "group_id": None,
                "shape_type": "rectangle",
                "flags": {}
            })

        json_data = {
            "version": "5.0.2.1",
            "flags": {},
            "shapes": shapes,
            "imagePath": os.path.basename(image_file),
            "imageData": image_data,
            "imageHeight": image_height,
            "imageWidth": image_width,
        }

        json_file = os.path.join(output_folder, os.path.basename(xml_file).replace('.xml', '.json'))
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=4)

        print(f"文件已成功转换为 {json_file}")

    def convert_yolo_to_xml(self, yolo_file, output_folder):
        """将 YOLO 矩形框格式转换为 XML 格式"""
        output_file = os.path.join(output_folder, os.path.basename(yolo_file).replace('.txt', '.xml'))
        root = ET.Element("annotation")
        with open(yolo_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                class_id = parts[0]

                # 如果 YOLO 文件包含超过 5 个字段，表示可能是分割格式
                if len(parts) > 5:
                    QMessageBox.warning(self, "警告", f"文件 {yolo_file} 包含分割格式，无法转换为 XML。")
                    return "error"  # 立即返回错误标志，停止处理
                # 使用用户提供的标签映射
                if self.label_mapping:
                    class_id = self.label_mapping.get(class_id, class_id)
                # 处理矩形框格式
                center_x, center_y, width, height = map(float, parts[1:5])
                xmin = center_x - width / 2
                ymin = center_y - height / 2
                xmax = center_x + width / 2
                ymax = center_y + height / 2
                # 创建 XML 结构
                obj = ET.SubElement(root, "object")
                name = ET.SubElement(obj, "name")
                name.text = class_id  # 确保使用映射后的标签名
                bndbox = ET.SubElement(obj, "bndbox")
                ET.SubElement(bndbox, "xmin").text = str(int(xmin))
                ET.SubElement(bndbox, "ymin").text = str(int(ymin))
                ET.SubElement(bndbox, "xmax").text = str(int(xmax))
                ET.SubElement(bndbox, "ymax").text = str(int(ymax))
        # 保存为 XML 文件
        xml_str = ET.tostring(root, encoding='unicode')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="   ")
        with open(output_file, 'w') as f:
            f.write(pretty_xml)
        return "success"
        print(f"文件 {yolo_file} 已成功转换为 {output_file}")

    def convert_yolo_to_json(self, yolo_file, output_folder, image_file):
        """将 YOLO 格式转换为 LabelMe JSON 格式，并从图像文件中读取信息"""
        output_file = os.path.join(output_folder, os.path.basename(yolo_file).replace('.txt', '.json'))
        shapes = []

        # 从图像文件中获取 Base64 编码和图像尺寸
        image_data, image_width, image_height = self.get_image_data(image_file)

        with open(yolo_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                class_id = parts[0]  # 类别标签

                if len(parts) == 5:
                    # 处理矩形框的 YOLO 格式
                    center_x, center_y, width, height = map(float, parts[1:5])
                    xmin = center_x - width / 2
                    ymin = center_y - height / 2
                    xmax = center_x + width / 2
                    ymax = center_y + height / 2

                    shapes.append({
                        "label": str(class_id),
                        "points": [[xmin, ymin], [xmax, ymax]],
                        "group_id": None,
                        "shape_type": "rectangle",
                        "flags": {}
                    })
                else:
                    # 处理多边形的 YOLO 分割格式
                    points = list(map(float, parts[1:]))
                    polygon_points = [[points[i] * image_width, points[i + 1] * image_height] for i in
                                      range(0, len(points), 2)]

                    shapes.append({
                        "label": str(class_id),
                        "points": polygon_points,
                        "group_id": None,
                        "shape_type": "polygon",
                        "flags": {}
                    })

        # 创建符合 LabelMe 的 JSON 数据
        json_data = {
            "version": "5.0.2.1",
            "flags": {},
            "shapes": shapes,  # 包含所有形状
            "imagePath": os.path.basename(image_file),  # 从图像文件路径中提取文件名
            "imageData": image_data,  # Base64 编码后的图像数据
            "imageHeight": image_height,
            "imageWidth": image_width,
        }

        # 将数据写入 JSON 文件
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=4)

        print(f"文件已成功转换为 {output_file}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LabelConverter()
    window.show()
    sys.exit(app.exec_())
