import os
import re
from pypdf import PdfReader
from docx import Document

class Resume:
    def __init__(self, file_path):
        self.__file_path = os.path.abspath(file_path)
        self.__file_name = os.path.basename(file_path)
        self.__text = ""

    

