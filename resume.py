import os
import re
from pypdf import PdfReader
from docx import Document

class Resume:
    def __init__(self, file_path):
        self.__file_path = os.path.abspath(file_path)
        self.__file_name = os.path.basename(file_path)
        self.__text = ""

    def get_file_path(self):
        return self.__file_path

    def get_file_name(self):
        return self.__file_name

    def get_text(self):
        return self.__text

    