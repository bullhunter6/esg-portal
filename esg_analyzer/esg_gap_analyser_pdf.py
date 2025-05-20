# esg_gap_analyser_pdf_v6.py

import os
import sys
import time
import traceback
from dotenv import load_dotenv
from fpdf import FPDF, XPos, YPos

# --- Core LangChain Components ---
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

# --- Configuration ---
# !!! IMPORTANT: Update these paths and NAME !!!
NATIONAL_POLICY_PDF_PATH = "Federal Decree-Law No. (11) of 2024 On the Reduction of Climate Change Effects.pdf"
COMPANY_ESG_REPORT_PATH = r"C:\Users\saikr\OneDrive\Documents\projects\esg\portal\Agthia_ESG_Policy_Mar24.pdf"
COMPANY_NAME = "Agthia" # <<<--- Ensure this is correct

COMPANY_VECTORSTORE_DIR = f"./chroma_db_{COMPANY_NAME.lower()}_report"

EMBEDDING_MODEL_NAME = "text-embedding-3-small"
LLM_MODEL_NAME = "gpt-4o-mini" # Or GPT-4
NATIONAL_POLICY_CHUNK_SIZE = 750
NATIONAL_POLICY_CHUNK_OVERLAP = 100
COMPANY_REPORT_CHUNK_SIZE = 1000
COMPANY_REPORT_CHUNK_OVERLAP = 150
SEARCH_RESULT_COUNT = 3
# !!! UPDATE Output filename !!!
GAP_ANALYSIS_PDF_OUTPUT_FILE = f"{COMPANY_NAME}_ESG_Gap_Analysis_Report_v6.pdf"

# --- Font Configuration ---
UNICODE_FONT_NAME = "DejaVu"
FONT_REGULAR_PATH = "fonts/DejaVuSans.ttf"
FONT_BOLD_PATH = "fonts/DejaVuSans-Bold.ttf"
FONT_ITALIC_PATH = "fonts/DejaVuSans-Oblique.ttf"

# --- Helper Functions (Unchanged from v5) ---
def load_environment_variables():
    load_dotenv(); api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: print("ERROR: OPENAI_API_KEY not found."); sys.exit(1)
    return api_key

def load_and_chunk_pdf(pdf_path, chunk_size, chunk_overlap, doc_type="Document"):
    if not os.path.exists(pdf_path): print(f"ERROR: {doc_type} PDF not found: {pdf_path}"); return None
    print(f"--- Loading {doc_type} PDF: {os.path.basename(pdf_path)} ---")
    try: loader = PyPDFLoader(pdf_path); documents = loader.load()
    except Exception as e: print(f"Error loading {doc_type} PDF {pdf_path}: {e}"); return None
    if not documents: print(f"ERROR: No content loaded from {doc_type} PDF: {pdf_path}"); return None
    print(f"Loaded {len(documents)} pages.")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len, add_start_index=True)
    chunks = text_splitter.split_documents(documents); print(f"Split into {len(chunks)} chunks.")
    if not chunks: print(f"ERROR: Splitting resulted in no chunks."); return None
    for i, chunk in enumerate(chunks):
        chunk.metadata["source_doc"] = os.path.basename(pdf_path)
        chunk.metadata["chunk_index"] = i
        chunk.metadata["source_page"] = chunk.metadata.get("page", -1) + 1 # Adjust 0-index
    return chunks

def create_vector_store(docs, embeddings, persist_directory=None, collection_name="default_collection"):
    doc_name = docs[0].metadata['source_doc'] if docs else "documents"; print(f"Vector store setup for {doc_name}...")
    if persist_directory:
        if os.path.exists(persist_directory):
            try:
                vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings, collection_name=collection_name)
                vectorstore.get_collection(name=collection_name); print(f"Loaded existing collection '{collection_name}' from {persist_directory}")
            except Exception:
                 print(f"Collection '{collection_name}' not found. Creating new..."); vectorstore = Chroma.from_documents(docs, embeddings, persist_directory=persist_directory, collection_name=collection_name); print(f"Vector store persisted.")
        else:
            print(f"Creating new vector store at {persist_directory}..."); vectorstore = Chroma.from_documents(docs, embeddings, persist_directory=persist_directory, collection_name=collection_name); print(f"Vector store persisted.")
    else:
        print("Creating new vector store in memory..."); vectorstore = Chroma.from_documents(docs, embeddings, collection_name=collection_name); print("Vector store created.")
    return vectorstore

def format_docs_for_eval(docs, company_name):
    if not docs: return f"No relevant excerpts found in the {company_name} report."
    return "\n\n---\n\n".join(f"Excerpt from {company_name} Report (Page {doc.metadata.get('source_page', 0)}):\n{doc.page_content}" for doc in docs)

def clean_llm_output(text):
    if not isinstance(text, str): return ""
    return ''.join(c for c in text if c.isprintable() or c in '\n\r\t')

# --- Generate Summary Function (Unchanged from v5) ---
def generate_summary(gaps_data, llm, company_name):
    if not gaps_data: return f"No potential substantive gaps applicable to {company_name} were identified."
    print(f"\n--- Generating Executive Summary for {company_name} ---")
    gap_summary_points = []
    for gap in gaps_data:
        policy_req_snippet = clean_llm_output(gap['policy_requirement'][:250].replace("\n", " ").strip()) + "..."
        assessment_parts = gap['assessment'].split(":", 1); assessment_reason = clean_llm_output(assessment_parts[1].strip()) if len(assessment_parts) > 1 else clean_llm_output(gap['assessment'])
        gap_summary_points.append(f"- Policy Pt (Pg {gap['policy_source_page']}): {policy_req_snippet}\n  Assessment Reason: {assessment_reason}")
    context_for_summary = "\n".join(gap_summary_points)
    summary_template = f"""
    You are an AI assistant creating an executive summary of an ESG gap analysis for '{company_name}'.
    The following lists potential gaps where {company_name}'s ESG report didn't seem to substantively address specific, applicable requirements from a national policy.
    Summarize the main themes of these gaps into 3-5 key bullet points or a short paragraph, highlighting major discrepancy types (e.g., missing procedural details, lack of discussion on mechanisms, reporting deficiencies). Focus only on the provided list of gaps.

    Identified Gaps List (Applicable to {company_name}):
    ```
    {{gap_list}}
    ```
    Executive Summary of Identified Gaps for {company_name}:"""
    summary_prompt = ChatPromptTemplate.from_template(summary_template); output_parser = StrOutputParser(); summary_chain = summary_prompt | llm | output_parser
    try: summary = summary_chain.invoke({"gap_list": context_for_summary}); summary_cleaned = clean_llm_output(summary); print("Summary generated."); return summary_cleaned
    except Exception as e: print(f"Error generating summary: {e}"); return f"Error generating summary for {company_name}."

# --- PDF Report Class (Adds Methods for Covered/NA Points) ---
class PDFReport(FPDF):
    def setup_fonts(self):
        fonts_to_check = {'Regular': FONT_REGULAR_PATH, 'Bold': FONT_BOLD_PATH, 'Italic': FONT_ITALIC_PATH}
        missing_fonts = [f"- {s}: Expected at '{p}'" for s, p in fonts_to_check.items() if not os.path.exists(p)]
        if missing_fonts: print("!!! FONT FILE(S) NOT FOUND !!!\nRequired font files missing:\n" + "\n".join(missing_fonts)); print("\nPlease ensure DejaVu TTF files are in the script's directory OR paths are correct."); return False
        try: self.add_font(UNICODE_FONT_NAME, '', FONT_REGULAR_PATH); self.add_font(UNICODE_FONT_NAME, 'B', FONT_BOLD_PATH); self.add_font(UNICODE_FONT_NAME, 'I', FONT_ITALIC_PATH); print(f"Added Unicode font '{UNICODE_FONT_NAME}'"); return True
        except Exception as e: print(f"!!! FONT LOADING ERROR !!!: {e}"); traceback.print_exc(); return False

    def header(self):
        self.set_font(UNICODE_FONT_NAME, 'B', 12)
        self.cell(0, 10, f'{COMPANY_NAME} - ESG Gap Analysis Report', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C'); self.ln(5)

    def footer(self):
        self.set_y(-15); self.set_font(UNICODE_FONT_NAME, 'I', 8); self.cell(0, 10, f'Page {self.page_no()}', border=0, align='C')

    def chapter_title(self, title):
        self.set_font(UNICODE_FONT_NAME, 'B', 14); self.cell(0, 10, title, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L'); self.ln(4)

    def chapter_body(self, body_text):
        self.set_font(UNICODE_FONT_NAME, '', 10); available_width = self.w - self.l_margin - self.r_margin; self.multi_cell(available_width, 5, clean_llm_output(body_text)); self.ln()

    def gap_details(self, gap_number, gap_data): # Unchanged
        available_width = self.w - self.l_margin - self.r_margin; indent_width = available_width - 5
        self.set_font(UNICODE_FONT_NAME, 'B', 11); self.cell(available_width, 8, f"Potential Gap #{gap_number}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_font(UNICODE_FONT_NAME, 'I', 9); self.cell(available_width, 5, f"Source: National Policy Page {gap_data['policy_source_page']} (Chunk approx. {gap_data['policy_chunk_index']})", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L'); self.ln(2)
        self.set_font(UNICODE_FONT_NAME, 'B', 10); self.cell(available_width, 5, "National Policy Requirement/Statement:", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_font(UNICODE_FONT_NAME, '', 10); self.set_x(self.l_margin + 5); self.multi_cell(indent_width, 5, clean_llm_output(gap_data['policy_requirement'])); self.set_x(self.l_margin); self.ln(2)
        self.set_font(UNICODE_FONT_NAME, 'B', 10); self.cell(available_width, 5, "Assessment:", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_font(UNICODE_FONT_NAME, '', 10); self.set_x(self.l_margin + 5); self.multi_cell(indent_width, 5, clean_llm_output(gap_data['assessment'])); self.set_x(self.l_margin); self.ln(5)

    # --- NEW Method for Covered Points ---
    def covered_point_details(self, point_number, point_data):
        available_width = self.w - self.l_margin - self.r_margin; indent_width = available_width - 5
        self.set_font(UNICODE_FONT_NAME, 'B', 11)
        self.cell(available_width, 8, f"Covered Point #{point_number}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_font(UNICODE_FONT_NAME, 'I', 9)
        self.cell(available_width, 5, f"Source: National Policy Page {point_data['policy_source_page']} (Chunk approx. {point_data['policy_chunk_index']})", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L'); self.ln(2)
        self.set_font(UNICODE_FONT_NAME, 'B', 10)
        self.cell(available_width, 5, "National Policy Requirement/Statement:", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_font(UNICODE_FONT_NAME, '', 10)
        self.set_x(self.l_margin + 5); self.multi_cell(indent_width, 5, clean_llm_output(point_data['policy_requirement'])); self.set_x(self.l_margin); self.ln(2)
        self.set_font(UNICODE_FONT_NAME, 'B', 10)
        self.cell(available_width, 5, "Assessment (Coverage Found):", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_font(UNICODE_FONT_NAME, '', 10)
        self.set_x(self.l_margin + 5); self.multi_cell(indent_width, 5, clean_llm_output(point_data['assessment'])); self.set_x(self.l_margin); self.ln(5)

    # --- NEW Method for Non-Applicable Points ---
    def not_applicable_point_details(self, point_number, point_data):
        available_width = self.w - self.l_margin - self.r_margin; indent_width = available_width - 5
        self.set_font(UNICODE_FONT_NAME, 'B', 11)
        self.cell(available_width, 8, f"Non-Applicable/Governmental Point #{point_number}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_font(UNICODE_FONT_NAME, 'I', 9)
        self.cell(available_width, 5, f"Source: National Policy Page {point_data['policy_source_page']} (Chunk approx. {point_data['policy_chunk_index']})", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L'); self.ln(2)
        self.set_font(UNICODE_FONT_NAME, 'B', 10)
        self.cell(available_width, 5, "National Policy Requirement/Statement:", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_font(UNICODE_FONT_NAME, '', 10)
        self.set_x(self.l_margin + 5); self.multi_cell(indent_width, 5, clean_llm_output(point_data['policy_requirement'])); self.set_x(self.l_margin); self.ln(2)
        self.set_font(UNICODE_FONT_NAME, 'B', 10)
        self.cell(available_width, 5, "Assessment (Reason for Non-Applicability):", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_font(UNICODE_FONT_NAME, '', 10)
        self.set_x(self.l_margin + 5); self.multi_cell(indent_width, 5, clean_llm_output(point_data['assessment'])); self.set_x(self.l_margin); self.ln(5)


# --- Create PDF Report Function (Accepts & Uses Covered/NA points) ---
def create_pdf_report(summary, gaps_data, covered_points, not_applicable_points, config, filename):
    """Creates the PDF report including all analysis categories."""
    print(f"\n--- Creating PDF Report: {filename} ---")
    try:
        pdf = PDFReport()
        if not pdf.setup_fonts(): print("PDF generation aborted."); return

        pdf.add_page()
        available_width = pdf.w - pdf.l_margin - pdf.r_margin

        # --- Report Metadata (Updated with all counts) ---
        pdf.set_font(UNICODE_FONT_NAME, 'B', 11)
        pdf.cell(available_width, 6, "Analysis Details", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.set_font(UNICODE_FONT_NAME, '', 10)
        pdf.multi_cell(available_width, 5, f"National Policy Document: {config['national_policy_path']}")
        pdf.multi_cell(available_width, 5, f"Company Analyzed: {config['company_name']} (Report: {config['company_report_path']})")
        pdf.cell(available_width, 5, f"Analysis Date: {config['analysis_date']}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.cell(available_width, 5, f"Potential Gaps Found (Applicable to Company): {config['total_gaps']}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.cell(available_width, 5, f"Points Covered by Company Report: {config['total_covered']}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.cell(available_width, 5, f"Policy Points Not Directly Applicable to Company Report: {config['total_not_applicable']}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.ln(10)

        # --- Executive Summary ---
        pdf.chapter_title(f"Executive Summary for {config['company_name']}")
        pdf.chapter_body(summary)
        pdf.ln(10)

        # --- Detailed Potential Gaps ---
        pdf.chapter_title("Detailed Potential Gaps")
        if not gaps_data:
            pdf.chapter_body(f"No significant gaps applicable to {config['company_name']} identified.")
        else:
            for idx, gap in enumerate(gaps_data):
                if pdf.get_y() > (pdf.h - 40): pdf.add_page(); pdf.chapter_title("Detailed Potential Gaps (Continued)")
                pdf.gap_details(idx + 1, gap)
        pdf.ln(5) # Space before next section

        # --- Covered Points Section ---
        pdf.add_page() # Start on a new page for clarity
        pdf.chapter_title("Covered Points")
        if not covered_points:
            pdf.chapter_body(f"No specific policy points were assessed as fully covered by the {config['company_name']} report excerpts.")
        else:
            for idx, point in enumerate(covered_points):
                if pdf.get_y() > (pdf.h - 40): pdf.add_page(); pdf.chapter_title("Covered Points (Continued)")
                pdf.covered_point_details(idx + 1, point)
        pdf.ln(5) # Space before next section

        # --- Non-Applicable Points Section ---
        pdf.add_page() # Start on a new page
        pdf.chapter_title("Non-Applicable / Governmental Points")
        if not not_applicable_points:
            pdf.chapter_body("No policy points were assessed as primarily non-applicable (e.g., definitions, government procedures).")
        else:
            for idx, point in enumerate(not_applicable_points):
                if pdf.get_y() > (pdf.h - 40): pdf.add_page(); pdf.chapter_title("Non-Applicable / Governmental Points (Continued)")
                pdf.not_applicable_point_details(idx + 1, point)

        # --- Save the PDF ---
        pdf.output(filename)
        print(f"PDF report saved successfully to: {filename}")

    except Exception as e:
        print(f"ERROR: Failed to create PDF report - {e}"); traceback.print_exc()


# --- Main Execution ---
if __name__ == "__main__":
    start_time = time.time()
    print(f"--- Initializing ESG Gap Analyser for {COMPANY_NAME} (PDF v6 - Full Report) ---")

    openai_api_key = load_environment_variables()
    print(f"Initializing embedding model: {EMBEDDING_MODEL_NAME}")
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL_NAME, openai_api_key=openai_api_key)
    print(f"Initializing LLM: {LLM_MODEL_NAME}")
    llm = ChatOpenAI(model_name=LLM_MODEL_NAME, temperature=0.0, openai_api_key=openai_api_key)

    national_policy_chunks = load_and_chunk_pdf(NATIONAL_POLICY_PDF_PATH, NATIONAL_POLICY_CHUNK_SIZE, NATIONAL_POLICY_CHUNK_OVERLAP, "National Policy")
    if not national_policy_chunks: sys.exit(1)
    company_report_chunks = load_and_chunk_pdf(COMPANY_ESG_REPORT_PATH, COMPANY_REPORT_CHUNK_SIZE, COMPANY_REPORT_CHUNK_OVERLAP, f"{COMPANY_NAME} Report")
    if not company_report_chunks: sys.exit(1)
    company_collection_name = f"{COMPANY_NAME.lower()}_report_esg"
    company_vector_store = create_vector_store(company_report_chunks, embeddings, persist_directory=COMPANY_VECTORSTORE_DIR, collection_name=company_collection_name)
    if not company_vector_store: print(f"Failed vector store setup for {COMPANY_NAME}. Exiting."); sys.exit(1)

    company_retriever = company_vector_store.as_retriever(search_kwargs={"k": SEARCH_RESULT_COUNT})
    print(f"{COMPANY_NAME} report retriever configured.")

    # --- Refined Gap Evaluation Prompt (Same as v5) ---
    eval_template = f"""
    You are an expert AI assistant performing a detailed ESG gap analysis comparing {COMPANY_NAME}'s ESG report against specific requirements from a national policy document.
    Your goal is to identify **substantive gaps** where {COMPANY_NAME}'s report fails to demonstrate alignment with the policy requirements applicable to **companies ('Sources')**.

    **National Policy Requirement/Statement:** (From: {{policy_source}}, Page {{policy_page}}, Chunk {{policy_chunk_index}})
    ```{{policy_requirement}}```
    **Relevant Excerpts Found in {COMPANY_NAME}'s ESG Report:**
    ```{{company_context}}```

    **Analysis Task:** Based *only* on the provided texts:
    1.  **Applicability:** Is the requirement mainly for: (a) companies/sources, or (b) definitions, principles, government actions?
    2.  **Coverage:** If (a), do {COMPANY_NAME}'s excerpts **substantively address** it (actions, data, policies, targets)? Focus on intent.
    3.  **Ignore Minor:** Do NOT flag GAP for missing definitions verbatim or government procedures unless they impose a specific, unmet requirement on {COMPANY_NAME} in the context.
    4.  **Output:** Start *strictly* with "GAP:", "COVERED:", or "NOT_APPLICABLE:".
    5.  **Explanation:** After prefix, provide **brief** justification based on applicability and substance.
    **Assessment:**
    """
    evaluation_prompt = ChatPromptTemplate.from_template(eval_template)
    output_parser = StrOutputParser()

    # --- Gap Evaluation Chain (Same as v5) ---
    def retrieve_and_format_context(national_policy_chunk: Document):
        policy_req_text = national_policy_chunk.page_content; retrieved_docs = company_retriever.invoke(policy_req_text)
        formatted_context = format_docs_for_eval(retrieved_docs, COMPANY_NAME)
        return {"policy_requirement": policy_req_text,"company_context": formatted_context,"policy_source": national_policy_chunk.metadata.get("source_doc", "N/A"), "policy_page": national_policy_chunk.metadata.get("source_page", 0), "policy_chunk_index": national_policy_chunk.metadata.get("chunk_index", "N/A")}
    gap_eval_chain = retrieve_and_format_context | evaluation_prompt | llm | output_parser

    # --- Perform Gap Analysis Loop (Categorize results) ---
    print(f"\n--- Starting Gap Analysis ({len(national_policy_chunks)} policy chunks vs {COMPANY_NAME} report) ---")
    potential_gaps = []; covered_points = []; not_applicable_points = []
    for i, policy_chunk in enumerate(national_policy_chunks):
        print(f"Analysing Policy Chunk {i+1}/{len(national_policy_chunks)}...")
        try:
            temp_policy_chunk_doc = Document(page_content=clean_llm_output(policy_chunk.page_content), metadata=policy_chunk.metadata)
            assessment_result = gap_eval_chain.invoke(temp_policy_chunk_doc)
            assessment_cleaned = clean_llm_output(assessment_result)
            policy_req_cleaned = clean_llm_output(policy_chunk.page_content)
            chunk_metadata = {"policy_chunk_index": policy_chunk.metadata.get("chunk_index", "N/A"),"policy_source_page": policy_chunk.metadata.get("source_page", 0),"policy_requirement": policy_req_cleaned,"assessment": assessment_cleaned.strip()}

            if assessment_cleaned.strip().startswith("GAP:"): potential_gaps.append(chunk_metadata); print("  -> GAP identified.")
            elif assessment_cleaned.strip().startswith("COVERED:"): covered_points.append(chunk_metadata); print("  -> COVERED.")
            elif assessment_cleaned.strip().startswith("NOT_APPLICABLE:"): not_applicable_points.append(chunk_metadata); print("  -> NOT APPLICABLE.")
            else: print(f"  -> Unexpected format: {assessment_cleaned[:100]}...")
        except Exception as e: print(f"  -> Error analysing chunk {i+1}: {e}"); traceback.print_exc(); continue

    # --- Generate Summary (Based only on Gaps) ---
    summary_text = generate_summary(potential_gaps, llm, COMPANY_NAME)

    # --- Create PDF Report (Pass all lists and updated config) ---
    end_time = time.time()
    analysis_config = {
        "national_policy_path": os.path.basename(NATIONAL_POLICY_PDF_PATH),
        "company_report_path": os.path.basename(COMPANY_ESG_REPORT_PATH),
        "company_name": COMPANY_NAME,
        "analysis_date": time.strftime('%Y-%m-%d %H:%M:%S'),
        "total_gaps": len(potential_gaps),
        "total_covered": len(covered_points), # Added count
        "total_not_applicable": len(not_applicable_points) # Added count
    }
    # Pass all three lists to the report function
    create_pdf_report(summary_text, potential_gaps, covered_points, not_applicable_points, analysis_config, GAP_ANALYSIS_PDF_OUTPUT_FILE)

    print("\n--- Analysis Complete ---")
    print(f"Total analysis time: {end_time - start_time:.2f} seconds")
    print(f"Found {len(potential_gaps)} gaps, {len(covered_points)} covered points, and {len(not_applicable_points)} non-applicable points for {COMPANY_NAME}.")