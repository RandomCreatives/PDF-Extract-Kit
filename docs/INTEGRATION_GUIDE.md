# Integration Guide: PDF-Extract-Kit for DigitalMehandis_V5.0

This guide explains how `PDF-Extract-Kit` works and how it can be integrated into the [DigitalMehandis_V5.0](https://github.com/RandomCreatives/DigitalMehandis_V5.0) project to automate data extraction from construction drawings.

## 0. Integration vs. Re-creation

A common question is whether to **re-create** the features of `PDF-Extract-Kit` directly inside `DigitalMehandis` or have the two repositories **communicate**.

**Recommendation: Integration (Communication)**
You should **integrate** `PDF-Extract-Kit` as a backend service dependency rather than re-creating it.
- **Complexity**: PDF-Extract-Kit relies on complex, heavy-weight ML models (LayoutLMv3, YOLOv10, PaddleOCR). Re-creating these within your main app would make your codebase difficult to maintain.
- **Specialization**: Keeping them separate allows your main app (EthioQS) to focus on quantity surveying logic, while PDF-Extract-Kit focuses on document analysis.
- **Resource Management**: Extraction requires high CPU/GPU power. Integration allows you to host the Extraction Service on a separate GPU-optimized server while keeping your web server lightweight.

---

## 1. How PDF-Extract-Kit Works

`PDF-Extract-Kit` is a modular, model-driven toolkit designed for high-quality content extraction. Its architecture is based on three main pillars:

### A. Task-Model Registry System
The toolkit uses a registry pattern (found in `pdf_extract_kit/registry/`) to decouple high-level extraction **Tasks** from the underlying **Models**.
- **Tasks**: (e.g., `OCRTask`, `TableParsingTask`) Define the workflow: loading data, calling models, and formatting results.
- **Models**: (e.g., `PaddleOCR`, `StructEqTable`) Perform the actual machine learning inference.
- **Decoupling**: You can swap models via configuration files (YAML) without changing any application code.

### B. PDF Processing Workflow
1. **Preprocessing**: PDFs are converted into high-resolution images (default 144 DPI) using `PyMuPDF` (`fitz`) in `pdf_extract_kit/utils/data_preprocess.py`.
2. **Analysis**:
   - **Layout Detection**: Identifies regions like Text, Tables, Formulas, and Images.
   - **OCR**: Detects and recognizes text within the identified regions.
   - **Table Parsing**: Specialized models reconstruct table structures into structured formats like HTML, Markdown, or LaTeX.
3. **Structured Output**: Results are returned as Python dictionaries or JSON files containing coordinates (polygons/bounding boxes) and extracted content.

### C. Configuration-Driven
Everything is controlled by YAML files in the `configs/` directory. For example, `configs/ocr.yaml` specifies which OCR model to use and its parameters.

---

## 2. Integration into DigitalMehandis_V5.0

`DigitalMehandis_V5.0` is a quantity surveying tool with a FastAPI backend and a Next.js frontend. The integration involves creating a service layer in the backend to wrap `PDF-Extract-Kit`.

### A. Backend Integration (FastAPI)

1. **Service Wrapper**: Create a new service in `backend/app/services/extraction.py`.
2. **Asynchronous Processing**: Extraction is resource-intensive. Use FastAPI's `BackgroundTasks` to avoid blocking the user.

#### Example Service Implementation:
```python
from pdf_extract_kit.utils.config_loader import load_config, initialize_tasks_and_models
import os

class ExtractionService:
    def __init__(self, config_path="configs/ocr.yaml"):
        # Load configuration and initialize models once
        self.config = load_config(config_path)
        self.task_instances = initialize_tasks_and_models(self.config)
        self.ocr_task = self.task_instances['ocr']

    def extract_from_pdf(self, pdf_path, output_dir):
        # Process the PDF and return results
        # ocr_task.process handles PDF to Image conversion and OCR
        results = self.ocr_task.process(pdf_path, save_dir=output_dir)
        return results
```

### B. Frontend Integration (Next.js)

1. **Upload Trigger**: When a user uploads a drawing in the "Upload Drawings" section of DigitalMehandis.
2. **Status Polling**: Since extraction is backgrounded, the frontend should poll an endpoint (e.g., `/api/v1/drawings/{id}/status`) to check if the extraction is complete.
3. **Data Review**: Present the extracted data in a side-by-side view (Drawing vs. Form) so the user can verify and "Accept" the data into their BOQ (Bill of Quantities).

---

## 3. Specific Use Cases for Construction Drawings

### 1. Title Block Extraction
Construction drawings have a "Title Block" (usually bottom-right) containing critical metadata.
- **Action**: Run OCR on the bottom 20% of the page.
- **Data Extracted**: Project Name, Drawing Title, Sheet Number, Revision, and Scale.
- **Benefit**: Auto-populates the drawing registry in DigitalMehandis.

### 2. Schedule Parsing (BBS/Doors/Windows)
Construction drawings often include schedules in table format.
- **Action**: Use the `table_parsing` task to extract these tables.
- **Data Extracted**: Rebar diameters, spacing, quantities, door/window dimensions.
- **Benefit**: Automatically populates the Bar Bending Schedule (BBS) or quantity takeoff tables, reducing manual entry errors.

### 3. General Notes & Specifications
- **Action**: Use `layout_detection` to find text blocks and `OCR` to read "General Notes".
- **Benefit**: Searchable project specifications.

---

## 4. Implementation Steps

1. **Environment**: Install `pdf-extract-kit` dependencies in the DigitalMehandis backend environment.
2. **Model Weights**: Download pretrained models (LayoutLMv3, PaddleOCR, etc.) to a shared volume.
3. **API Endpoint**: Create a FastAPI endpoint `POST /api/v1/extract` that accepts a file ID and triggers the `ExtractionService`.
4. **Data Mapping**: Write a parser to map the raw OCR JSON output to the DigitalMehandis database schema (e.g., mapping "Sheet No" text to the `drawing.sheet_number` column).

---

## 5. Proof-of-Concept (PoC)

We have provided a runnable PoC in the `project/digitalmehandis_poc/` directory to demonstrate exactly how the code should look in your backend.

### Files:
- **`service.py`**: A clean wrapper that initializes the models once and provides methods to process drawings and extract specific metadata like "Sheet Number".
- **`main.py`**: A FastAPI implementation showing how to use `BackgroundTasks` to process drawings without blocking the user interface.

### Running the PoC (Conceptual):
```bash
# From the root directory
export PYTHONPATH=$PYTHONPATH:.
uvicorn project.digitalmehandis_poc.main:app --reload
```
