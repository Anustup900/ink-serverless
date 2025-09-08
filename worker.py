import os
import json
import base64
import shutil
import uuid
import requests
import subprocess
import time
from pathlib import Path

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
WORKDIR = "/workspace/ComfyUI"
BASE_WORKFLOW = "/workspace/baseGraphTemplate.json"
COMFY_API = "http://127.0.0.1:8188"

# Node ID mappings (confirmed from baseGraphTemplate.json)
NODE_WIDTH = "27"       # Width
NODE_HEIGHT = "28"      # Height
NODE_SEED = "95"        # Seed
NODE_HUMAN = "33"       # Load Human Image
NODE_TATTOO = "96"      # Load Tattoo Image
NODE_MASK = "153"       # Load Mask Image
NODE_OUTPUT = "143"     # Save Image Output

# -------------------------------------------------------------------
# Utility functions
# -------------------------------------------------------------------

def save_base64_image(b64_str, path):
    """Decode base64 string and save to disk."""
    img_bytes = base64.b64decode(b64_str)
    with open(path, "wb") as f:
        f.write(img_bytes)
    return path


def encode_images(output_path, prefix):
    """Read generated images from output directory and encode as base64."""
    images_b64 = []
    if not os.path.exists(output_path):
        return images_b64

    for f in os.listdir(output_path):
        if f.startswith(prefix) and f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            with open(os.path.join(output_path, f), "rb") as img_file:
                images_b64.append(base64.b64encode(img_file.read()).decode("utf-8"))
    return images_b64


def start_comfyui_server():
    """Start ComfyUI API server in background (if not already running)."""
    try:
        requests.get(f"{COMFY_API}/queue")
        return  # already running
    except requests.exceptions.ConnectionError:
        pass

    subprocess.Popen(
        ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"],
        cwd=WORKDIR
    )

    # Wait for server to be ready
    for _ in range(30):
        try:
            requests.get(f"{COMFY_API}/queue")
            return
        except:
            time.sleep(2)
    raise RuntimeError("ComfyUI server did not start in time!")

# -------------------------------------------------------------------
# Worker main job function
# -------------------------------------------------------------------

def process_job(job):
    """
    Run one ComfyUI workflow job via API.
    Expects job['input']['params'] to contain:
      - width (int)
      - height (int)
      - human_image (base64 str)
      - Tattooimage (base64 str)
      - mask (base64 str)
      - tryon_seed (int)
    """
    inputs = job.get("input", {})
    params = inputs.get("params", {})

    # Start ComfyUI if needed
    start_comfyui_server()

    # Unique job folder + prefix
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(WORKDIR, "jobs", job_id)
    os.makedirs(job_dir, exist_ok=True)

    workflow_file = os.path.join(job_dir, "workflow.json")
    output_dir = os.path.join(job_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    output_prefix = f"tryon_{job_id[:8]}"

    # Load base workflow template
    with open(BASE_WORKFLOW, "r") as f:
        workflow = json.load(f)

    # --- Replace mapped values ---
    if "width" in params:
        workflow[NODE_WIDTH]["inputs"]["value"] = int(params["width"])
    if "height" in params:
        workflow[NODE_HEIGHT]["inputs"]["value"] = int(params["height"])
    if "tryon_seed" in params:
        workflow[NODE_SEED]["inputs"]["seed"] = int(params["tryon_seed"])

    if "human_image" in params:
        human_path = os.path.join(job_dir, "human.png")
        save_base64_image(params["human_image"], human_path)
        workflow[NODE_HUMAN]["inputs"]["image"] = human_path

    if "Tattooimage" in params:
        tattoo_path = os.path.join(job_dir, "tattoo.png")
        save_base64_image(params["Tattooimage"], tattoo_path)
        workflow[NODE_TATTOO]["inputs"]["image"] = tattoo_path

    if "mask" in params:
        mask_path = os.path.join(job_dir, "mask.png")
        save_base64_image(params["mask"], mask_path)
        workflow[NODE_MASK]["inputs"]["image"] = mask_path

    # Ensure output node uses unique prefix
    if NODE_OUTPUT in workflow and "inputs" in workflow[NODE_OUTPUT]:
        workflow[NODE_OUTPUT]["inputs"]["filename_prefix"] = output_prefix

    # Save updated workflow
    with open(workflow_file, "w") as f:
        json.dump(workflow, f)

    # Submit workflow to ComfyUI API
    resp = requests.post(f"{COMFY_API}/prompt", json={"prompt": workflow})
    if resp.status_code != 200:
        return {"stdout": "", "stderr": f"ComfyUI API error: {resp.text}", "tryon_images": []}

    prompt_id = resp.json().get("prompt_id")
    if not prompt_id:
        return {"stdout": "", "stderr": "No prompt_id returned from ComfyUI", "tryon_images": []}

    # Poll until finished
    finished = False
    for _ in range(60):  # wait up to 2 minutes
        q = requests.get(f"{COMFY_API}/history/{prompt_id}")
        if q.status_code == 200:
            history = q.json()
            if prompt_id in history:
                finished = True
                break
        time.sleep(2)

    if not finished:
        return {"stdout": "", "stderr": "ComfyUI job did not finish in time", "tryon_images": []}

    # Collect outputs
    images_b64 = encode_images(output_dir, prefix=output_prefix)

    # Cleanup
    shutil.rmtree(job_dir, ignore_errors=True)

    return {
        "stdout": f"Workflow {prompt_id} executed successfully.",
        "stderr": "",
        "tryon_images": images_b64
    }
