import re
import subprocess
from pathlib import Path


SEGMENT_DELIMITER_PATTERN = re.compile(r"(?m)^\s*##SEGMENT\s*$")
SUPPORTED_SOURCE_EXTENSIONS = {".txt", ".pdf", ".docx", ".doc"}


class CampaignProcessingError(ValueError):
    pass


def get_source_file_type(file_name: str) -> str:
    extension = Path(file_name or "").suffix.lower()
    if extension not in SUPPORTED_SOURCE_EXTENSIONS:
        raise CampaignProcessingError("Only .txt, .pdf, .doc, and .docx files are supported.")
    return extension.lstrip(".")


def extract_text_from_source_file(source_file) -> str:
    file_type = get_source_file_type(source_file.name)
    source_file.open("rb")
    try:
        if file_type == "txt":
            raw = source_file.read()
            text = raw.decode("utf-8-sig", errors="ignore")
        elif file_type == "pdf":
            try:
                from pypdf import PdfReader
            except ModuleNotFoundError as exc:
                raise CampaignProcessingError("PDF support requires the 'pypdf' package to be installed.") from exc
            reader = PdfReader(source_file)
            text = "\n".join((page.extract_text() or "").strip() for page in reader.pages)
        elif file_type == "docx":
            try:
                from docx import Document
            except ModuleNotFoundError as exc:
                raise CampaignProcessingError("DOCX support requires the 'python-docx' package to be installed.") from exc
            document = Document(source_file)
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        else:
            raise CampaignProcessingError(".doc files are not supported in v1. Please convert the file to .docx.")
    except CampaignProcessingError:
        raise
    except Exception as exc:
        raise CampaignProcessingError(f"Could not extract text from the uploaded {file_type.upper()} file.") from exc
    finally:
        source_file.close()

    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        raise CampaignProcessingError("Could not extract readable text from the uploaded file.")
    return normalized


def parse_segments(source_text: str) -> list[str]:
    if not SEGMENT_DELIMITER_PATTERN.search(source_text):
        raise CampaignProcessingError("The source file must include ##SEGMENT on its own line for each segment.")

    raw_chunks = SEGMENT_DELIMITER_PATTERN.split(source_text)
    segments = [chunk.strip() for chunk in raw_chunks if chunk.strip()]
    if not segments:
        raise CampaignProcessingError("No segment content was found after parsing ##SEGMENT blocks.")
    return segments


def get_video_duration_seconds(media_asset) -> int:
    input_target = ""
    if getattr(media_asset, "file", None):
        try:
            input_target = media_asset.file.path
        except Exception:
            input_target = ""
    if not input_target:
        input_target = media_asset.get_file_url()
    if not input_target:
        raise CampaignProcessingError("Could not resolve a video source to inspect its duration.")

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_target,
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CampaignProcessingError("Could not read the source video duration.") from exc

    output = (result.stdout or "").strip()
    try:
        duration_value = float(output)
    except ValueError as exc:
        raise CampaignProcessingError("Could not parse the source video duration.") from exc

    duration_seconds = max(1, int(round(duration_value)))
    return duration_seconds


def build_segment_ranges(total_duration_seconds: int, segment_count: int) -> list[tuple[int, int]]:
    if total_duration_seconds <= 0:
        raise CampaignProcessingError("Video duration must be greater than zero.")
    if segment_count <= 0:
        raise CampaignProcessingError("At least one segment is required.")

    base_duration = total_duration_seconds // segment_count
    remainder = total_duration_seconds % segment_count
    ranges: list[tuple[int, int]] = []
    start = 0
    for index in range(segment_count):
        duration = base_duration
        if index == segment_count - 1:
            duration += remainder
        end = start + duration
        ranges.append((start, end))
        start = end
    return ranges
