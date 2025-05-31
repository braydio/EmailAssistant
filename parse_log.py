import re
import sys


def extract_raw_emails(file_path, output_path=None):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex to extract text between EMAIL DETAILS: and last line marker
    pattern = re.compile(
        r"EMAIL DETAILS:\n(.*?)If there are any actions, tasks, or urgent items mentioned, please highlight them\.",
        re.DOTALL,
    )

    matches = pattern.findall(content)
    if not matches:
        print("No emails found between markers.")
        return

    extracted = []
    for i, match in enumerate(matches, 1):
        extracted.append(f"\n--- EMAIL #{i} ---\n{match.strip()}")

    full_output = "\n".join(extracted)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_output)
        print(f"Extracted {len(matches)} emails to {output_path}")
    else:
        print(full_output)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_exact_emails.py <log_file> [output_file]")
    else:
        extract_raw_emails(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
