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

    def extract_text(self):
        extension = os.path.splitext(self.__file_path)[1].lower()

        if extension == ".pdf":
            self.__text = self.__extract_pdf_text()

        elif extension == ".docx":
            self.__text = self.__extract_docx_text()

        else:
            raise ValueError("Unsupported resume file format.")

        self.__text = self.__clean_text(self.__text)
        return self.__text
    