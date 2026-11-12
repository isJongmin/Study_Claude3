"""도면 PDF 저장: 파일명은 서버가 만든 UUID만 쓴다. 업로드 전 %PDF- 시그니처·30MB 확인."""
import uuid

from .. import config
from ..errors import AppError, bad


def save_pdf(data: bytes, original: str) -> tuple[str, str]:
    if len(data) > config.MAX_PDF:
        raise AppError(413, "FILE_TOO_LARGE", "파일 크기는 30MB 이하여야 합니다. 파일을 줄이거나 분할해 다시 올리세요.")
    if not data.startswith(b"%PDF-"):
        raise bad("PDF 파일만 업로드할 수 있습니다. 파일 형식을 확인하세요.", "NOT_PDF")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    fid = uuid.uuid4().hex
    (config.UPLOAD_DIR / f"{fid}.pdf").write_bytes(data)
    name = "".join(c for c in (original or "drawing.pdf").replace("\\", "/").split("/")[-1] if c.isprintable())[:150]
    return fid, name or "drawing.pdf"


def path_of(fid: str):
    p = config.UPLOAD_DIR / f"{fid}.pdf"
    return p if fid.isalnum() and p.is_file() else None


def drop(fid: str | None):
    p = path_of(fid) if fid else None
    if p:
        p.unlink(missing_ok=True)


def sample_pdf(no: str, rev: int, status: str, hull: str, disc: str) -> bytes:
    """업로드 파일이 없는 리비전용 샘플 PDF (목업 samplePdf 이식, ASCII 전용)."""
    def a(s):
        return "".join(c if 32 <= ord(c) < 127 else "?" for c in str(s)).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = "\n".join([
        "0.8 w 20 20 555 380 re S", "0.4 w 20 330 m 575 330 l S",
        "BT /F1 20 Tf 36 360 Td (SHIPYARD DRAWING - SAMPLE) Tj ET",
        f"BT /F1 14 Tf 36 305 Td (No   : {a(no)}) Tj ET", f"BT /F1 14 Tf 36 285 Td (Rev  : {rev}    Status: {a(status)}) Tj ET",
        f"BT /F1 14 Tf 36 265 Td (Hull : {a(hull)}    Discipline: {a(disc)}) Tj ET",
        "1.2 w 70 130 m 500 130 l 545 175 l 40 175 l h S", "0.6 w 120 175 m 120 215 l 200 215 l 200 175 S 330 175 m 330 205 l 400 205 l 400 175 S",
        "BT /F1 10 Tf 36 40 Td (No file uploaded for this revision - generated sample PDF) Tj ET",
    ])
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 420] /Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"]
    pdf, off = "%PDF-1.4\n", []
    for i, o in enumerate(objs):
        off.append(len(pdf))
        pdf += f"{i + 1} 0 obj\n{o}\nendobj\n"
    xr = len(pdf)
    pdf += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in off)
    pdf += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xr}\n%%EOF"
    return pdf.encode("latin-1")
