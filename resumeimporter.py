import re
from pathlib import Path
from pypdf import PdfReader
from docx import Document

class ResumeImporter:
    def __init__(self):
        self.__supported_extensions = (".pdf", ".docx")

    def collect_batch(self, folder: str) -> list[Path]:
        folder_path = Path(folder)

        if not folder_path.is_dir():
            raise ValueError("Invalid folder.")

        files = []

        for path in folder_path.iterdir():
            if not path.is_file():
                continue

            try:
                self.__validate_file(path)
                files.append(path)
            except (ValueError, OSError) as error:
                print(f"Skipped {path.name}: {error}")

        return files

    def prepare(self, files: list[Path]) -> list[dict]:
        resumes = []

        for path in files:
            try:
                self.__validate_file(path)

                text = self.__extract_text(path)
                text = self.__clean_text(text)
                text = self.__anonymize_text(text)

                if not text.strip():
                    raise ValueError("Resume contains no readable text.")

                resume = {
                    "file_path": str(path),
                    "file_name": path.name,
                    "text": text
                }

                resumes.append(resume)
            except (ValueError, OSError) as error:
                print(f"Unable to prepare {path}: {error}")

        return resumes

    def __validate_file(self, path: Path) -> None:
        if not path.is_file():
            raise ValueError("File does not exist.")

        if path.suffix.lower() not in self.__supported_extensions:
            raise ValueError("Unsupported file extension.")

        if path.stat().st_size == 0:
            raise ValueError("File is empty.")

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