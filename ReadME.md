# Label Converter - README

---


### Introduction
The Label Converter is a tool designed for converting between various annotation formats such as JSON, XML, and YOLO. It supports both rectangular and polygon annotations, with an option to modify label names to conform to YOLO's requirement of numeric labels. The tool provides a user-friendly GUI, making it suitable for large-scale annotation data processing.

### Features
- Conversion between JSON and XML formats.
- YOLO detection (rectangular) and YOLO segmentation (polygon) format conversion.
- Automatic label name validation and modification to ensure YOLO labels are numeric.
- Supports batch file conversion for automated processing in annotation projects.

### How to Use
1. Open the application and click the "Load Data" button to select a folder containing annotation files (JSON, XML, YOLO formats).
2. Select the folder containing the corresponding image files.
3. The program will automatically analyze the annotation formats in the folder and prompt whether label names need to be modified.
4. Choose whether to modify label names or directly select the conversion format to proceed.
5. Once conversion is complete, the output will be saved in the folder specified by the user.

### System Requirements
- Python 3.6+
- Required dependencies: Pillow, PyQt5, json, xml.etree.ElementTree, minidom

### 安装
1. Clone or download this project to your local machine.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
3. Run the program:
   ```bash
   python LabelConverter.py

