import os
import json
from pathlib import Path

# -------- CONFIG --------
current_file_path = Path(__file__).resolve()
PROJECT_ROOT = current_file_path.parent
BASE_DIR = current_file_path.parent
METADATA_DIR = os.path.join(BASE_DIR, "metadata")
CHUNKS_DIR = os.path.join(BASE_DIR, "chunks")
# ------------------------


def split_into_sections(text: str):
    """
    Split document into (section_title, section_body) pairs based on lines starting with '## '.
    Returns:
        title: document title (from '# ' line)
        sections: list of (section_title, section_body)
    """
    lines = text.splitlines()

    doc_title = ""
    sections = []

    current_section_title = None
    current_lines = []

    for line in lines:
        stripped = line.strip()

        # Document title
        if stripped.startswith("# ") and not doc_title:
            doc_title = stripped[2:].strip()
            continue

        # Section heading
        if stripped.startswith("## "):
            # Save previous section if exists
            if current_section_title is not None:
                section_body = "\n".join(current_lines).strip()
                sections.append((current_section_title, section_body))

            current_section_title = stripped[3:].strip()
            current_lines = []
        else:
            if current_section_title is not None:
                current_lines.append(line)

    # Save last section
    if current_section_title is not None:
        section_body = "\n".join(current_lines).strip()
        sections.append((current_section_title, section_body))

    # If no sections found, treat entire doc as one section
    if not sections:
        sections = [("Full Document", text)]

    return doc_title, sections


def ensure_chunks_dir():
    Path(CHUNKS_DIR).mkdir(parents=True, exist_ok=True)


def main():
    ensure_chunks_dir()

    metadata_dir = Path(METADATA_DIR)
    all_chunks = []

    json_files = sorted(metadata_dir.glob("*.json"))

    chunk_counter_global = 0

    for file_path in json_files:
        file_name = file_path.name
        print(f"Processing document: {file_name}")

        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"  WARNING: Could not decode JSON {file_name}, skipping.")
            continue

        # Extract content and metadata
        text = data.get("content", "")
        if not text:
            print(f"  WARNING: No content in {file_name}, skipping.")
            continue

        # Prepare metadata dict (exclude content to save space in metadata)
        doc_meta = {k: v for k, v in data.items() if k != "content"}
        doc_id = doc_meta.get("doc_id", file_name)

        doc_title, sections = split_into_sections(text)

        # Fall back to metadata title if parsing didn't find one
        if not doc_title:
            doc_title = doc_meta.get("title", file_name)

        for idx, (section_title, section_body) in enumerate(sections, start=1):
            chunk_counter_global += 1
            chunk_id = f"{doc_id}_CHUNK_{idx:03d}"

            # Build chunk text (nice to have title + section)
            chunk_text = f"# {doc_title}\n## {section_title}\n\n{section_body}\n"

            # Write chunk to file
            chunk_file_name = f"{chunk_id}.txt"
            chunk_file_path = Path(CHUNKS_DIR) / chunk_file_name
            with chunk_file_path.open("w", encoding="utf-8") as cf:
                cf.write(chunk_text)

            # Build chunk metadata record
            chunk_record = {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "file_name": file_name,
                "chunk_file": chunk_file_name,
                "title": doc_title,
                "section_title": section_title,
                "section_index": idx,
                "text": chunk_text.strip(),
                # Merge doc_meta into chunk_record
                **doc_meta
            }

            all_chunks.append(chunk_record)

    # Write all chunks metadata to JSON
    chunks_meta_path = Path(CHUNKS_DIR) / "chunks_metadata.json"
    with chunks_meta_path.open("w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"\nTotal chunks created: {len(all_chunks)}")
    print(f"Chunks directory: {CHUNKS_DIR}")
    print(f"Chunks metadata: {chunks_meta_path}")


if __name__ == "__main__":
    main()