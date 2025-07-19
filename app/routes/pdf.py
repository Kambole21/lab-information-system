from pypdf import PdfWriter

# Load and clone the original PDF
writer = PdfWriter(clone_from="input.pdf")

# Compress the contents of each page
for page in writer.pages:
    page.compress_content_streams