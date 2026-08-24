import os
from pathlib import Path

def convert_crlf(file_path: Path):
    if not file_path.exists():
        return
    try:
        # Unhide/unprotect if needed
        os.system(f'attrib -r -h -s "{file_path}"')
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Decode text cleanly
        text = content.decode("utf-8", errors="ignore")
        
        # Normalize line endings to CRLF (\r\n)
        lines = text.splitlines()
        clean_text = "\r\n".join(lines) + "\r\n"
        
        with open(file_path, "wb") as f:
            f.write(clean_text.encode("utf-8"))
        print(f"[OK] Fixed CRLF for: {file_path}")
    except Exception as e:
        print(f"[ERROR] Failed {file_path}: {e}")

if __name__ == "__main__":
    targets = [
        Path(r"C:\Test"),
        Path(r"D:\Test"),
        Path(r"C:\ProgramData\ParentalControl"),
        Path(r"d:\Hoàng\PMQL\parental-control"),
        Path(r"d:\Hoàng\PMQL\parental-control\agent"),
    ]
    
    for t in targets:
        if t.exists():
            for p in t.glob("*.bat"):
                convert_crlf(p)
