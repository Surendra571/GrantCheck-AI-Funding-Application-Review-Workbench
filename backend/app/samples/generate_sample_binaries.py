import os
import fitz  # PyMuPDF
from docx import Document as DocxDocument

samples_dir = os.path.dirname(os.path.abspath(__file__))

def create_sample_docx():
    doc = DocxDocument()
    doc.add_heading("UK CleanTech Horizon Grant 2026 — Program Guidelines", 0)
    
    doc.add_heading("1. Eligibility Criteria", level=1)
    doc.add_paragraph("The lead applicant must be a UK-registered SME operating for at least 12 months with fewer than 250 employees. Academic institutions and non-UK entities are eligible only as secondary consortium partners.")
    
    doc.add_heading("2. Financial Documentation", level=1)
    doc.add_paragraph("Applications must include audited financial statements for the previous two financial years (FY2023-2024 and FY2024-2025) or certified accountant reports for companies trading less than three years.")
    
    doc.add_heading("3. Technical & Environmental Impact", level=1)
    doc.add_paragraph("Projects must achieve a minimum 40% reduction in carbon emissions verified by life-cycle analysis. All experimental test procedures must comply with ISO 14040 standards.")
    
    doc.add_heading("4. Commercial Partner Validation", level=1)
    doc.add_paragraph("Applicants should provide letters of support from at least two commercial pilot partners indicating intent to test the developed technology upon project milestone completion.")
    
    out_path = os.path.join(samples_dir, "sample_guideline.docx")
    doc.save(out_path)
    print(f"Created DOCX: {out_path}")

def create_sample_pdf():
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page()
    text1 = (
        "Grant Application Draft — EcoFilter Clean Water Reclamation\n\n"
        "Section A: Company Profile & Eligibility\n"
        "EcoFilter Ltd is a UK-registered micro-SME (Companies House #09876543) incorporated in March 2023, "
        "operating continuously for 30 months from our headquarters in Manchester, UK with 14 full-time employees.\n\n"
        "Section B: Project Objectives\n"
        "Our project scales next-generation graphene-membrane filtration systems for industrial wastewater recycling. "
        "Our membrane technology reduces filtration energy consumption by 65% compared to all market alternatives."
    )
    page1.insert_text((50, 72), text1, fontsize=11)

    # Page 2
    page2 = doc.new_page()
    text2 = (
        "Section C: Environmental Impact\n"
        "Our pilot data indicates an estimated 35-45% decrease in plant greenhouse emissions across operational trial sites "
        "during steady-state filtration cycles.\n\n"
        "Section D: Commercial Partners\n"
        "Two letters of intent are attached from Yorkshire Water and Northumbrian Water plc confirming partner deployment.\n\n"
        "Section E: Financial Overview\n"
        "Total project budget is £450,000 requesting £315,000 in grant contribution."
    )
    page2.insert_text((50, 72), text2, fontsize=11)

    out_path = os.path.join(samples_dir, "sample_application.pdf")
    doc.save(out_path)
    print(f"Created PDF: {out_path}")

if __name__ == "__main__":
    create_sample_docx()
    create_sample_pdf()
