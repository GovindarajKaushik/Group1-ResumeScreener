import uuid
import os
import re

class Resume:
    def __init__(self, file_path):
        self.__id = uuid.uuid4().hex
        self.__file_path = os.path.abspath(file_path)
        self.__file_name = os.path.basename(file_path)
        self.__text = ""

        self.validate_file()
        self.__text = self.extract_resume_text()

        if not self.__text:
            raise ValueError(f"No readable text found in {self.__file_name}.")

        self.__text = self.anonymize_resume_text(self.__text)

        if not self.__text:
            raise ValueError(f"No resume content remains after anonymising " f"{self.__file_name}.")

