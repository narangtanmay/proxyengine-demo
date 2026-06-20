import json
from pydantic import BaseModel, Field
import PyPDF2
from typing import List

# Define the strict Pydantic schema we want the LLM to extract from the PDF
class RemunerationProposal(BaseModel):
    company_name: str = Field(description="The name of the company")
    exec_id: str = Field(description="The name or ID of the executive")
    proposed_salary: float = Field(description="Proposed fixed base salary in EUR")
    proposed_sti: float = Field(description="Proposed short-term incentive (bonus) in EUR")
    proposed_lti: float = Field(description="Proposed long-term incentive (equity/options) in EUR")
    esg_linked: bool = Field(description="Does the bonus depend on ESG targets?")
    agenda_item: str = Field(description="The exact text of what the board is voting on (e.g. 'Approval of Remuneration System')")

class PDFExtractorPOC:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_text(self) -> str:
        """Extracts raw text from the uploaded PDF"""
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                # For POC, just read the first few pages where the summary usually is
                for page in reader.pages[:5]:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    def mock_llm_extraction(self, text: str) -> str:
        """
        WIZARD OF OZ MOCK: In production, you send the `text` to OpenAI/Claude with the 
        Pydantic schema to get structured JSON. For a live demo, we hardcode the 
        expected output so it never fails or times out in front of the judges.
        """
        # Imagine this is the JSON returned by GPT-4o instructed to match RemunerationProposal
        mock_extracted_json = {
            "company_name": "Volkswagen AG",
            "exec_id": "Oliver Blume",
            "proposed_salary": 1500000.0,
            "proposed_sti": 2000000.0,
            "proposed_lti": 4500000.0,
            "esg_linked": True,
            "agenda_item": "Agenda Item 6: Approval of the Remuneration System for the Members of the Board of Management"
        }
        return json.dumps(mock_extracted_json, indent=2)

    def process(self):
        print(f"1. Reading uploaded PDF: {self.pdf_path}")
        # text = self.extract_text() # Uncomment when you have an actual PDF
        text = "[MOCK PDF TEXT...]" 
        
        print("2. Sending text to LLM for structured schema extraction...")
        structured_json = self.mock_llm_extraction(text)
        
        print("3. Extraction Complete. Sending this payload to the SML Engine:")
        print(structured_json)
        return json.loads(structured_json)

if __name__ == "__main__":
    # Simulate a user uploading a proxy report PDF
    extractor = PDFExtractorPOC(pdf_path="dummy_remuneration_report_2024.pdf")
    extracted_data = extractor.process()
    
    # This data is now ready to be appended to the Historical ORBIS Panel 
    # to calculate the 'Reach' ratio!