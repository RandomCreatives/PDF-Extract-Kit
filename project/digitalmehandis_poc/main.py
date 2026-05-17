from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import os
import uuid
from .service import ExtractionService

app = FastAPI(title="DigitalMehandis Extraction PoC")

# Mock database to store extraction results
db = {}

# Initialize the service (in production, use a singleton or dependency injection)
# We assume the config exists at the root
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../configs/ocr.yaml")
service = ExtractionService(config_path=CONFIG_PATH)

class ExtractionRequest(BaseModel):
    file_path: str

class ExtractionStatus(BaseModel):
    id: str
    status: str
    result: dict = None

def run_extraction(task_id: str, file_path: str):
    """The background task that performs the heavy lifting."""
    try:
        output_dir = f"outputs/poc_{task_id}"
        os.makedirs(output_dir, exist_ok=True)

        # 1. Run the Kit
        raw_results = service.process_drawing(file_path, output_dir)

        # 2. Extract specific construction data
        metadata = service.extract_title_block(raw_results)

        # 3. Save to mock DB
        db[task_id] = {
            "status": "completed",
            "result": {
                "metadata": metadata,
                "raw_json_path": os.path.join(output_dir, "page_1.json")
            }
        }
    except Exception as e:
        db[task_id] = {"status": "failed", "error": str(e)}

@app.post("/extract", response_model=ExtractionStatus)
async def trigger_extraction(request: ExtractionRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to trigger the extraction of a drawing.
    In DigitalMehandis, this would be called after a file upload.
    """
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    task_id = str(uuid.uuid4())
    db[task_id] = {"status": "processing"}

    background_tasks.add_task(run_extraction, task_id, request.file_path)

    return {"id": task_id, "status": "processing"}

@app.get("/status/{task_id}", response_model=ExtractionStatus)
async def get_status(task_id: str):
    """The frontend polls this to check if the AI is done."""
    if task_id not in db:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"id": task_id, **db[task_id]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
