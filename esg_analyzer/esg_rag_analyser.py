import os
import sys
import time # Added for timing
from dotenv import load_dotenv

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
# !!! IMPORTANT: Update these paths !!!
NATIONAL_POLICY_PDF_PATH = "Federal Decree-Law No. (11) of 2024 On the Reduction of Climate Change Effects.pdf" # <--- National Policy PDF
COMPANY_ESG_REPORT_PATH = r"C:\Users\saikr\OneDrive\Documents\projects\esg\portal\Agthia_SR2024_EN.pdf" # <--- Company ESG Report PDF

# Vector Store for Company Report (will be created in memory for this run)
# If you run this often with the same report, you could persist it like the national policy one.
COMPANY_VECTORSTORE_DIR = "./chroma_db_company_report" # Optional: persist company report DB

EMBEDDING_MODEL_NAME = "text-embedding-3-small"
LLM_MODEL_NAME = "gpt-3.5-turbo" # Use "gpt-4-turbo" or "gpt-4" for potentially better evaluation
NATIONAL_POLICY_CHUNK_SIZE = 750 # Smaller chunks for national policy to isolate requirements
NATIONAL_POLICY_CHUNK_OVERLAP = 100
COMPANY_REPORT_CHUNK_SIZE = 1000 # Standard chunk size for searching company report
COMPANY_REPORT_CHUNK_OVERLAP = 150
SEARCH_RESULT_COUNT = 3 # How many company chunks to retrieve for comparison
GAP_ANALYSIS_OUTPUT_FILE = "esg_gap_analysis_report.txt" # File to save the results

def load_environment_variables():
    """Loads environment variables and checks for the OpenAI API key."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found.")
        sys.exit(1)
    return api_key

def load_and_chunk_pdf(pdf_path, chunk_size, chunk_overlap, doc_type="Document"):
    """Loads a PDF and splits it into chunks."""
    if not os.path.exists(pdf_path):
        print(f"ERROR: {doc_type} PDF not found at: {pdf_path}")
        return None

    print(f"--- Loading {doc_type} PDF: {pdf_path} ---")
    try:
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
    except Exception as e:
        print(f"Error loading {doc_type} PDF {pdf_path}: {e}")
        return None

    if not documents:
        print(f"ERROR: No content loaded from {doc_type} PDF: {pdf_path}")
        return None
    print(f"Loaded {len(documents)} pages from {doc_type} PDF.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split {doc_type} into {len(chunks)} chunks.")

    if not chunks:
        print(f"ERROR: Splitting the {doc_type} resulted in no chunks.")
        return None

    # Add original filename and chunk ID to metadata for easier tracking
    for i, chunk in enumerate(chunks):
        chunk.metadata["source_doc"] = os.path.basename(pdf_path)
        chunk.metadata["chunk_index"] = i

    return chunks

def create_vector_store(docs, embeddings, persist_directory=None, collection_name="default_collection"):
    """Creates a Chroma vector store from documents."""
    print(f"Creating vector store for {docs[0].metadata['source_doc']}...")
    if persist_directory and os.path.exists(persist_directory):
         print(f"Loading existing vector store from {persist_directory}")
         vectorstore = Chroma(
              persist_directory=persist_directory,
              embedding_function=embeddings,
              collection_name=collection_name
            )
    else:
        print(f"Creating new vector store {'at ' + persist_directory if persist_directory else 'in memory'}...")
        vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=persist_directory, # None means in-memory
            collection_name=collection_name # Added collection name
        )
        if persist_directory:
             print(f"Vector store persisted to {persist_directory}")
        else:
             print("Vector store created in memory.")
    return vectorstore

def format_docs_for_eval(docs):
    """Formats retrieved company docs for the evaluation prompt."""
    if not docs:
        return "No relevant excerpts found in the company report."
    # Include source page and basic content
    return "\n\n---\n\n".join(
        f"Excerpt from Company Report (Page {doc.metadata.get('page', 'N/A') + 1}):\n{doc.page_content}"
        for doc in docs
    )

# --- Main Execution ---
if __name__ == "__main__":
    start_time = time.time()
    print("--- Initializing ESG Gap Analyser ---")

    # 1. Load API Key
    openai_api_key = load_environment_variables()

    # 2. Initialize Embeddings Model
    print(f"Initializing embedding model: {EMBEDDING_MODEL_NAME}")
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL_NAME, openai_api_key=openai_api_key)

    # 3. Initialize LLM
    print(f"Initializing LLM: {LLM_MODEL_NAME}")
    llm = ChatOpenAI(
        model_name=LLM_MODEL_NAME,
        temperature=0.0, # Set temperature to 0 for deterministic evaluation
        openai_api_key=openai_api_key
    )

    # 4. Load and Chunk National Policy
    national_policy_chunks = load_and_chunk_pdf(
        NATIONAL_POLICY_PDF_PATH,
        NATIONAL_POLICY_CHUNK_SIZE,
        NATIONAL_POLICY_CHUNK_OVERLAP,
        "National Policy"
    )
    if not national_policy_chunks:
        sys.exit(1)

    # 5. Load, Chunk, and Create Vector Store for Company Report
    company_report_chunks = load_and_chunk_pdf(
        COMPANY_ESG_REPORT_PATH,
        COMPANY_REPORT_CHUNK_SIZE,
        COMPANY_REPORT_CHUNK_OVERLAP,
        "Company Report"
    )
    if not company_report_chunks:
        sys.exit(1)

    # Use a unique collection name if persisting
    company_vector_store = create_vector_store(
        company_report_chunks,
        embeddings,
        persist_directory=None, # Set to COMPANY_VECTORSTORE_DIR to save/load
        collection_name="company_report_esg"
        )
    if not company_vector_store:
        print("Failed to create vector store for Company Report. Exiting.")
        sys.exit(1)

    # 6. Create Retriever for Company Report Vector Store
    company_retriever = company_vector_store.as_retriever(
        search_kwargs={"k": SEARCH_RESULT_COUNT}
    )
    print(f"Company report retriever configured to fetch top {SEARCH_RESULT_COUNT} results.")

    # 7. Define the Gap Evaluation Prompt Template
    eval_template = """
    You are an AI assistant performing an ESG gap analysis. Your task is to determine if a company's ESG report adequately addresses a specific point derived from a national policy document.

    **National Policy Requirement/Statement:**
    (From: {policy_source}, Page {policy_page}, Chunk {policy_chunk_index})
    ```
    {policy_requirement}
    ```

    **Relevant Excerpts Found in Company ESG Report:**
    ```
    {company_context}
    ```

    **Analysis Task:**
    Based *only* on the provided texts:
    1.  Carefully read the 'National Policy Requirement/Statement'.
    2.  Examine the 'Relevant Excerpts Found in Company ESG Report'.
    3.  Determine if the company report excerpts **directly and substantively address** the core requirement or statement from the national policy. Consider if the company report mentions relevant actions, data, specific policies, commitments, or governance related to the national policy point. Passing mentions or vague statements may not be sufficient.
    4.  Provide your assessment in the following format:
        - Start your response *strictly* with "GAP:" if the company report excerpts DO NOT adequately address the national policy requirement OR if no relevant excerpts were found.
        - Start your response *strictly* with "COVERED:" if the company report excerpts DO adequately address the national policy requirement.
    5.  After "GAP:" or "COVERED:", provide a **brief** (1-2 sentence) explanation for your assessment, focusing on *why* the company text is or isn't sufficient in relation to the specific national policy point.

    **Assessment:**
    """
    evaluation_prompt = ChatPromptTemplate.from_template(eval_template)
    output_parser = StrOutputParser()

    # 8. Build the Gap Evaluation Chain
    # This chain will take a national policy chunk, retrieve company context, and evaluate
    # We define a function to handle the retrieval and formatting within the chain
    def retrieve_and_format_context(national_policy_chunk: Document):
        policy_req_text = national_policy_chunk.page_content
        # Use the retriever to find relevant company chunks
        retrieved_docs = company_retriever.invoke(policy_req_text)
        # Format the retrieved docs
        formatted_context = format_docs_for_eval(retrieved_docs)
        # Return a dictionary suitable for the prompt template
        return {
            "policy_requirement": policy_req_text,
            "company_context": formatted_context,
            "policy_source": national_policy_chunk.metadata.get("source_doc", "N/A"),
            "policy_page": national_policy_chunk.metadata.get("page", "N/A") + 1,
            "policy_chunk_index": national_policy_chunk.metadata.get("chunk_index", "N/A")
        }

    # Chain: Input (National Policy Chunk) -> Retrieve/Format -> Prompt -> LLM -> Parse Output
    gap_eval_chain = retrieve_and_format_context | evaluation_prompt | llm | output_parser

    # 9. Perform Gap Analysis Loop
    print(f"\n--- Starting Gap Analysis (Comparing {len(national_policy_chunks)} policy chunks against company report) ---")
    potential_gaps = []
    covered_points = [] # Optional: track covered points too

    for i, policy_chunk in enumerate(national_policy_chunks):
        print(f"Analysing National Policy Chunk {i+1}/{len(national_policy_chunks)}...")
        try:
            # Invoke the chain with the current national policy chunk
            assessment_result = gap_eval_chain.invoke(policy_chunk)

            # Check the output prefix
            if assessment_result.strip().startswith("GAP:"):
                gap_info = {
                    "policy_chunk_index": policy_chunk.metadata.get("chunk_index", "N/A"),
                    "policy_source_page": policy_chunk.metadata.get("page", "N/A") + 1,
                    "policy_requirement": policy_chunk.page_content,
                    "assessment": assessment_result.strip() # Store the full assessment text
                }
                potential_gaps.append(gap_info)
                print("  -> Potential GAP identified.")
            elif assessment_result.strip().startswith("COVERED:"):
                 covered_points.append({ # Optional tracking
                      "policy_chunk_index": policy_chunk.metadata.get("chunk_index", "N/A"),
                      "assessment": assessment_result.strip()
                 })
                 print("  -> Requirement appears COVERED.")
            else:
                 print(f"  -> Unexpected assessment format: {assessment_result[:100]}...") # Log unexpected outputs

        except Exception as e:
            print(f"  -> Error during analysis of chunk {i+1}: {e}")
            # Optionally add error info to a separate list
            continue # Continue to the next chunk

    # 10. Report Results
    print("\n--- Gap Analysis Finished ---")
    end_time = time.time()
    print(f"Total analysis time: {end_time - start_time:.2f} seconds")

    print(f"\nFound {len(potential_gaps)} potential gaps.")
    print(f"Found {len(covered_points)} potentially covered points.") # Optional

    # Write results to file
    try:
        with open(GAP_ANALYSIS_OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("=======================================\n")
            f.write("    ESG Gap Analysis Report\n")
            f.write("=======================================\n\n")
            f.write(f"National Policy Document: {NATIONAL_POLICY_PDF_PATH}\n")
            f.write(f"Company ESG Report Document: {COMPANY_ESG_REPORT_PATH}\n")
            f.write(f"Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Potential Gaps Found: {len(potential_gaps)}\n")
            f.write("---------------------------------------\n\n")

            if not potential_gaps:
                f.write("No significant gaps identified based on the analysis.\n")
            else:
                f.write("Potential Gaps Identified:\n\n")
                for idx, gap in enumerate(potential_gaps):
                    f.write(f"Gap #{idx + 1}\n")
                    f.write(f"Source: National Policy Page {gap['policy_source_page']} (Chunk approx. {gap['policy_chunk_index']})\n")
                    f.write("National Policy Requirement/Statement:\n")
                    f.write(f"```\n{gap['policy_requirement']}\n```\n")
                    f.write("Assessment:\n")
                    f.write(f"```\n{gap['assessment']}\n```\n")
                    f.write("---------------------------------------\n\n")

        print(f"Gap analysis report saved to: {GAP_ANALYSIS_OUTPUT_FILE}")

    except Exception as e:
        print(f"Error writing report file: {e}")

    # Optionally print summary to console too
    # print("\n--- Summary of Potential Gaps ---")
    # if potential_gaps:
    #     for gap in potential_gaps:
    #         print(f"\nPolicy Page {gap['policy_source_page']} (Chunk {gap['policy_chunk_index']}):")
    #         print(f"  Requirement: {gap['policy_requirement'][:150]}...") # Print snippet
    #         print(f"  Assessment: {gap['assessment']}")
    # else:
    #     print("No significant gaps identified.")