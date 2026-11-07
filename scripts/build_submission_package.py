"""Build the single-file Google Classroom submission package."""

import os
import zipfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ZIP_OUTPUT = os.path.join(ROOT_DIR, "NetPulse_Google_Classroom_Submission.zip")

FILES_TO_INCLUDE = [
    # Master Presentation
    ("NetPulse_Master_Presentation.pptx", "NetPulse_Master_Presentation.pptx"),

    # Documentation & Reports
    ("docs/PRODUCT_START_SHEET.docx", "docs/PRODUCT_START_SHEET.docx"),
    ("docs/PRODUCT_START_SHEET.md", "docs/PRODUCT_START_SHEET.md"),
    ("docs/PRODUCT_REPORT.docx", "docs/PRODUCT_REPORT.docx"),
    ("docs/PRODUCT_REPORT.md", "docs/PRODUCT_REPORT.md"),
    ("docs/VIRTUALBOX_SETUP_GUIDE.md", "docs/VIRTUALBOX_SETUP_GUIDE.md"),
    ("README.md", "README.md"),

    # Infrastructure
    ("cloudformation.yaml", "cloudformation.yaml"),
    ("template.yaml", "template.yaml"),
    ("package.json", "package.json"),
    ("requirements.txt", "requirements.txt"),
    (".gitignore", ".gitignore"),

    # Lambda Backend
    ("lambda/app.py", "lambda/app.py"),

    # Monitor
    ("monitor/netpulse_monitor.py", "monitor/netpulse_monitor.py"),

    # Dashboard Frontend
    ("dashboard/index.html", "dashboard/index.html"),
    ("dashboard/styles.css", "dashboard/styles.css"),
    ("dashboard/app.js", "dashboard/app.js"),
    ("dashboard/config.js", "dashboard/config.js"),

    # Scripts
    ("scripts/local_demo.py", "scripts/local_demo.py"),
    ("scripts/capture_screenshots.py", "scripts/capture_screenshots.py"),
    ("scripts/generate_docs.py", "scripts/generate_docs.py"),
    ("scripts/generate_presentation.py", "scripts/generate_presentation.py"),

    # Tests
    ("tests/test_lambda.py", "tests/test_lambda.py"),
    ("tests/test_monitor.py", "tests/test_monitor.py"),
    ("tests/test_local_server.py", "tests/test_local_server.py"),

    # Screenshots
    ("docs/screenshots/dashboard-operational-green.png", "docs/screenshots/dashboard-operational-green.png"),
    ("docs/screenshots/dashboard-degraded-amber.png", "docs/screenshots/dashboard-degraded-amber.png"),
    ("docs/screenshots/dashboard-failure-red.png", "docs/screenshots/dashboard-failure-red.png"),
    ("docs/screenshots/terminal-monitor-demo.png", "docs/screenshots/terminal-monitor-demo.png"),
    ("docs/screenshots/architecture-diagram.png", "docs/screenshots/architecture-diagram.png"),
]


def create_submission_zip():
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
        for rel_path, arc_path in FILES_TO_INCLUDE:
            full_path = os.path.join(ROOT_DIR, rel_path)
            if os.path.exists(full_path):
                z.write(full_path, arc_path)
                print(f"Added: {arc_path}")
            else:
                print(f"WARNING: File not found: {full_path}")

    size_mb = os.path.getsize(ZIP_OUTPUT) / (1024 * 1024)
    print(f"\nSuccessfully generated: {ZIP_OUTPUT}")
    print(f"Total package size: {size_mb:.2f} MB")


if __name__ == "__main__":
    create_submission_zip()
