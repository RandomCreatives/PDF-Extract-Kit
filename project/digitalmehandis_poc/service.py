import os
import sys
import logging
from typing import Dict, Any, List

# Ensure we can import from the root pdf_extract_kit
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from pdf_extract_kit.utils.config_loader import load_config, initialize_tasks_and_models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtractionService:
    """
    A service wrapper for PDF-Extract-Kit tailored for the DigitalMehandis backend.
    """
    def __init__(self, config_path: str = "configs/ocr.yaml"):
        self.config_path = config_path
        self.tasks = None
        self._initialize()

    def _initialize(self):
        """Initializes the models. This is expensive, so it's done once."""
        try:
            logger.info(f"Initializing PDF-Extract-Kit with config: {self.config_path}")
            config = load_config(self.config_path)
            # In a real integration, you might want to initialize multiple tasks
            # e.g., 'ocr' for title blocks and 'table_parsing' for schedules
            self.tasks = initialize_tasks_and_models(config)
            logger.info("Models initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize models: {str(e)}")
            raise

    def process_drawing(self, pdf_path: str, output_dir: str) -> List[Any]:
        """
        Processes a construction drawing to extract text and tables.
        """
        if not self.tasks:
            raise RuntimeError("ExtractionService not initialized.")

        # Example using the OCR task
        # Note: In production, you would check if 'ocr' or 'table_parsing' is needed
        task_name = 'ocr'
        if task_name not in self.tasks:
             # Fallback if config only has one task
             task_name = list(self.tasks.keys())[0]

        logger.info(f"Starting extraction for: {pdf_path}")
        task = self.tasks[task_name]

        # PDF-Extract-Kit's process method handles the PDF -> Image conversion internally
        results = task.process(pdf_path, save_dir=output_dir)

        logger.info(f"Extraction complete. Results saved to: {output_dir}")
        return results

    def extract_title_block(self, results: List[Any]) -> Dict[str, str]:
        """
        Helper method to filter OCR results specifically for Title Block information.
        Usually located at the bottom-right of the drawing.
        """
        # Logic to filter by coordinates would go here
        # Construction drawings are usually standardized, so we look for
        # keywords like 'Sheet No', 'Drawing Title', etc.
        metadata = {
            "drawing_title": "UNKNOWN",
            "sheet_no": "UNKNOWN"
        }

        # results[0] is typically the first page (common for drawings)
        if results and isinstance(results[0], list):
            for item in results[0]:
                text = item.get('text', '').upper()
                if 'SHEET' in text and any(char.isdigit() for char in text):
                    metadata['sheet_no'] = text
                # Additional heuristic logic ...

        return metadata
