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

    def __extract_pdf_text(self):
        text_parts = ""

        try:
            reader = PdfReader(self.__file_path)

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        except Exception as e:
            print(f"Error reading PDF '{self.__file_path}': {e}")
            return ""

        return "\n".join(text_parts)

    def __extract_docx_text(self):
        """Extract plain text from a DOCX file, including table cells."""

        text_parts = ""
        try:
            document = Document(self.__file_path)
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            for table in document.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_parts.append(" | ".join(row_text))

        except Exception as e:
            print(f"Error reading DOCX '{self.__file_path}': {e}")
            return ""

        return "\n".join(text_parts)

    def clean_resume_text(self, text):
        """Normalize line endings and strip blank/whitespace-only lines."""
        if not self.__text:
            return ""

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)

        return "\n".join(lines)

    def anonymize_resume_text(self):
        if not self.__text:
            return ""
        # Remove labelled personal details and replace recognizable contact details.
        # Unlabelled names and personal details inside sentences may remain.
        personal_label = (
            r"^\s*(?:[-*•]\s*)?(?:full name|candidate name|name|"
            r"home address|postal address|address|date of birth|dob|age|"
            r"gender|sex|race|ethnicity|marital status|nationality|"
            r"e-?mail|phone(?: number)?|telephone|mobile(?: number)?|contact number)\s*[:：-]"
        )
        email_pattern = r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"
        # Recognize international numbers, Singapore numbers, and US-style numbers.
        # Avoid broad digit matching so employment year ranges remain unchanged.
        phone_pattern = (
            r"(?<!\w)(?:"
            r"(?:\+65[ .-]?)?[689]\d{3}[ .-]?\d{4}|"
            r"(?:\+1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]?\d{3}[ .-]\d{4}|"
            r"\+\d{1,3}[ .-]\d{1,4}[ .-]\d{3,4}[ .-]\d{4}"
            r")(?!\w)"
        )
        lines = []
        for line in self.__text.splitlines():
            if re.match(personal_label, line, flags=re.IGNORECASE):
                continue
            line = re.sub(email_pattern, "[EMAIL REMOVED]", line)
            line = re.sub(phone_pattern, "[PHONE REMOVED]", line)
            remaining_text = line.replace("[EMAIL REMOVED]", "").replace("[PHONE REMOVED]", "")
            # Omit lines containing only removed contacts or punctuation.
            if re.search(r"\w", remaining_text):
                lines.append(line.strip())
        return "\n".join(lines)