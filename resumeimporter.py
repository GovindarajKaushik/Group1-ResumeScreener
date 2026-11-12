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

    def __extract_text(self, path: Path) -> str:
        extension = path.suffix.lower()

        if extension == ".pdf":
            return self.__extract_pdf(path)

        elif extension == ".docx":
            return self.__extract_docx(path)

        else:
            raise ValueError("Unsupported resume file format.")

    def __extract_pdf(self, path: Path) -> str:
        text = ""

        try:
            reader = PdfReader(str(path))

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        except Exception as error:
            raise ValueError(f"Unable to read PDF: {error}")

        return text

    def __extract_docx(self, path : Path) -> str:
        """Extract plain text from a DOCX file, including table cells."""

        text_parts = ""
        try:
            document = Document(str(path))
            for paragraph in document.paragraphs:
                text += paragraph.text + "\n"

            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += cell.text + "\n"

        except Exception as error:
            raise ValueError(f"Error reading DOCX: {error}")

        return text

    def __clean_text(self, text: str) -> str:
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

    def __anonymize_text(self, text: str) -> str:
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
        for line in text.split("\n"):
            line = line.lower()
            if re.match(personal_label, line, flags=re.IGNORECASE):
                continue
            line = re.sub(email_pattern, "[EMAIL REMOVED]", line)
            line = re.sub(phone_pattern, "[PHONE REMOVED]", line)
            remaining_text = line.replace("[EMAIL REMOVED]", "").replace("[PHONE REMOVED]", "")
            # Omit lines containing only removed contacts or punctuation.
            if re.search(r"\w", remaining_text):
                lines.append(line.strip())
        return "\n".join(lines)