import os
import sys
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
from langchain_core.documents import Document # Added for handling individual chunks

# --- Configuration ---
KNOWLEDGE_BASE_PDF_PATH = r"C:\Users\saikr\OneDrive\Documents\projects\esg\portal\Federal Decree-Law No. (11) of 2024 On the Reduction of Climate Change Effects.pdf" # <--- Keep your national policy PDF
VECTORSTORE_PERSIST_DIR = "./chroma_db_esg_policy"
EMBEDDING_MODEL_NAME = "text-embedding-3-small"
LLM_MODEL_NAME = "gpt-3.5-turbo" # Or "gpt-4", "gpt-4-turbo" etc.
CHUNK_SIZE = 1500 # Adjusted chunk size for report analysis
CHUNK_OVERLAP = 200
SEARCH_RESULT_COUNT = 3

# !!! IMPORTANT: Replace this with the path to YOUR company ESG report PDF !!!
COMPANY_ESG_REPORT_PATH = r"C:\Users\saikr\OneDrive\Documents\projects\esg\portal\Agthia_SR2024_EN.pdf" # <--- CHANGE THIS

def load_environment_variables():
    """Loads environment variables and checks for the OpenAI API key."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found.")
        print("Please create a .env file with OPENAI_API_KEY=your_key")
        sys.exit(1)
    return api_key

def setup_vector_store(pdf_path, persist_directory, embeddings):
    """Loads, chunks, embeds documents, and sets up the vector store FOR KNOWLEDGE BASE."""
    # (Code is the same as before, just adding comments for clarity)
    vectorstore = None
    if os.path.exists(persist_directory):
        print(f"--- Loading existing KB vector store from: {persist_directory} ---")
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    else:
        print(f"--- Creating new KB vector store from PDF: {pdf_path} ---")
        if not os.path.exists(pdf_path):
            print(f"ERROR: Knowledge base PDF not found at: {pdf_path}")
            sys.exit(1)
        try:
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
        except Exception as e:
            print(f"Error loading KB PDF {pdf_path}: {e}")
            sys.exit(1)
        if not documents:
            print(f"ERROR: No content could be loaded from KB PDF: {pdf_path}")
            sys.exit(1)
        print(f"Loaded {len(documents)} pages from KB PDF.")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, length_function=len
        )
        chunks = text_splitter.split_documents(documents)
        print(f"Split KB document into {len(chunks)} chunks.")
        if not chunks:
            print("ERROR: Splitting the KB document resulted in no chunks.")
            sys.exit(1)
        print(f"Embedding KB chunks and creating vector store at: {persist_directory}...")
        try:
            vectorstore = Chroma.from_documents(
                documents=chunks, embedding=embeddings, persist_directory=persist_directory
            )
            print("--- KB Vector store created successfully. ---")
        except Exception as e:
            print(f"Error creating KB vector store: {e}")
            sys.exit(1)
    return vectorstore

def format_docs(docs):
    """Helper function to format retrieved documents for the RAG prompt."""
    return "\n\n---\n\n".join([doc.page_content for doc in docs])

def analyse_esg_report(report_pdf_path, llm, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    """Loads an ESG report, chunks it, and uses LLM to analyse each chunk."""
    print(f"\n--- Starting Analysis of ESG Report: {report_pdf_path} ---")

    if not os.path.exists(report_pdf_path):
        print(f"ERROR: ESG Report PDF not found at: {report_pdf_path}")
        print("Please ensure the COMPANY_ESG_REPORT_PATH is correct.")
        return # Don't exit, just skip this part

    try:
        report_loader = PyPDFLoader(report_pdf_path)
        report_docs = report_loader.load()
    except Exception as e:
        print(f"Error loading ESG report PDF {report_pdf_path}: {e}")
        return

    if not report_docs:
        print(f"ERROR: No content could be loaded from ESG Report PDF: {report_pdf_path}")
        return

    print(f"Loaded {len(report_docs)} pages from ESG report.")

    report_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    report_chunks = report_splitter.split_documents(report_docs)
    print(f"Split ESG report into {len(report_chunks)} chunks for analysis.")

    if not report_chunks:
        print("ERROR: Splitting the ESG report resulted in no chunks.")
        return

    # Define the prompt template for analysing report chunks
    analysis_template = """
    You are an AI assistant specialised in analysing ESG reports.
    Analyse the following text chunk from a company's ESG report.
    Your goal is to identify and list ONLY specific:
    - Mentioned company policies related to Environment (E), Social (S), or Governance (G).
    - Stated commitments or targets (e.g., emission reduction goals, diversity targets, safety metrics).
    - Significant ESG initiatives, programs, or projects described.
    - Key quantitative ESG data points or metrics reported (e.g., emissions figures, water usage, employee turnover, board diversity %).

    If no specific policies, commitments, targets, initiatives, or key data points are found in this chunk, state ONLY "No specific ESG points identified in this chunk."
    Do not summarise the general text. Focus ONLY on extracting the specific points listed above.
    Do not add external information or commentary. Be concise and use bullet points for listings if applicable.

    Text Chunk (Page {page_number}):
    ```
    {chunk_text}
    ```

    Analysis of Specific ESG Points in Chunk:
    """
    analysis_prompt = ChatPromptTemplate.from_template(analysis_template)
    output_parser = StrOutputParser()

    # Create a simple chain for chunk analysis (Prompt -> LLM -> Parse)
    analysis_chain = analysis_prompt | llm | output_parser

    print("\n--- Analysing Report Chunks ---")
    for i, chunk in enumerate(report_chunks):
        print(f"\n--- Analysing Chunk {i+1}/{len(report_chunks)} (from page {chunk.metadata.get('page', 'N/A')}) ---")
        try:
            # Prepare the input for the analysis chain
            prompt_input = {
                "chunk_text": chunk.page_content,
                "page_number": chunk.metadata.get('page', 'N/A') + 1 # page numbers often 0-indexed
            }
            # Invoke the analysis chain
            chunk_analysis = analysis_chain.invoke(prompt_input)
            print(chunk_analysis)

        except Exception as e:
            print(f"Error analysing chunk {i+1}: {e}")
            # Optional: Stop analysis on error, or continue with next chunk
            # break
            continue # Continue to the next chunk

    print("\n--- ESG Report Analysis Finished ---")


# --- Main Execution ---
if __name__ == "__main__":
    print("--- Initializing ESG Policy Analyser v2 ---")

    # 1. Load API Key
    openai_api_key = load_environment_variables()

    # 2. Initialize Embeddings Model (needed for RAG part)
    print(f"Initializing embedding model: {EMBEDDING_MODEL_NAME}")
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL_NAME, openai_api_key=openai_api_key)

    # 3. Initialize the LLM (used for both RAG and report analysis)
    print(f"Initializing LLM: {LLM_MODEL_NAME}")
    llm = ChatOpenAI(
        model_name=LLM_MODEL_NAME,
        temperature=0.1, # Keep low for factual analysis/extraction
        openai_api_key=openai_api_key
    )

    # --- Part 1: Analyse Company ESG Report ---
    analyse_esg_report(COMPANY_ESG_REPORT_PATH, llm)


    # --- Part 2: Setup RAG for National Policy Q&A ---
    # (This part runs after the report analysis, allowing Q&A against the national policy)
    print("\n--- Setting up RAG for National Policy Q&A ---")
    vector_store = setup_vector_store(KNOWLEDGE_BASE_PDF_PATH, VECTORSTORE_PERSIST_DIR, embeddings)
    if not vector_store:
       print("Failed to setup vector store for Q&A. Skipping Q&A part.")
    else:
        # Create Retriever for RAG
        retriever = vector_store.as_retriever(search_kwargs={"k": SEARCH_RESULT_COUNT})
        print(f"RAG Retriever configured to fetch top {SEARCH_RESULT_COUNT} national policy results.")

        # Define the RAG Prompt Template (same as before)
        rag_template = """
        You are an AI assistant analysing a company statement against provided excerpts from national regulations.
        Your task is to compare the 'Company Statement' to the 'Regulatory Context' provided below.
        Use ONLY the information present in the 'Regulatory Context' to answer. Do not use any prior knowledge.
        Be concise and specific.

        If the context directly addresses the company statement:
        - Briefly explain how the statement aligns or potentially conflicts with the regulations shown.
        - Quote the relevant part of the regulation from the context if possible.

        If the context does NOT contain relevant information to evaluate the company statement:
        - State clearly that the provided context does not cover this specific topic.

        Regulatory Context:
        {context}

        Company Statement:
        {question}

        Analysis:
        """
        rag_prompt = ChatPromptTemplate.from_template(rag_template)
        output_parser = StrOutputParser()

        # Build the RAG Chain (same as before)
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | rag_prompt
            | llm
            | output_parser
        )
        print("--- RAG Chain Constructed for Q&A ---")

        # Run the RAG Q&A Loop (same as before)
        print("\n--- National Policy Q&A Ready ---")
        print("You can now ask questions comparing statements to the loaded national policy.")
        print("Type 'quit' or 'exit' to stop.")

        while True:
            user_query = input("\nEnter statement/question for national policy comparison: ")
            if user_query.lower() in ['quit', 'exit']:
                break
            if not user_query:
                continue

            print("\nAnalysing against national policy...")
            try:
                result = rag_chain.invoke(user_query)
                print("\n--- Comparison Result ---")
                print(result)
                print("-------------------------")
            except Exception as e:
                print(f"\nAn error occurred during RAG analysis: {e}")

    print("\n--- Analyser Finished ---")