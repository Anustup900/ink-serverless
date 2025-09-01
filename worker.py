import subprocess
import os
import json
import base64
import shutil
import uuid
from pathlib import Path

# Paths
WORKDIR = "/workspace/ComfyUI"
BASE_WORKFLOW = "/workspace/baseGraphTemplate.json"   # base workflow template


def save_base64_image(b64_str, path):
    """Decode base64 string and save as an image file."""
    img_bytes = base64.b64decode(b64_str)
    with open(path, "wb") as f:
        f.write(img_bytes)
    return path


def encode_images(output_path, prefix="ComfyUI"):
    """Collect output images with given prefix and return as base64 strings."""
    images_b64 = []
    if not os.path.exists(output_path):
        return images_b64

    for f in os.listdir(output_path):
        if f.startswith(prefix) and f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            with open(os.path.join(output_path, f), "rb") as img_file:
                images_b64.append(base64.b64encode(img_file.read()).decode("utf-8"))
    return images_b64


def process_job(job):
    """
    Run one ComfyUI workflow job.
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

    # Unique job folder
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(WORKDIR, "jobs", job_id)
    os.makedirs(job_dir, exist_ok=True)

    workflow_file = os.path.join(job_dir, "workflow.json")
    output_dir = os.path.join(job_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    # Load base workflow template
    with open(BASE_WORKFLOW, "r") as f:
        workflow = json.load(f)

    # --- Replace mapped values ---
    if "width" in params:
        workflow["27"]["inputs"]["value"] = params["width"]
    if "height" in params:
        workflow["28"]["inputs"]["value"] = params["height"]
    if "tryon_seed" in params:
        workflow["95"]["inputs"]["seed"] = params["tryon_seed"]

    if "human_image" in params:
        human_path = os.path.join(job_dir, "human.png")
        save_base64_image(params["human_image"], human_path)
        workflow["33"]["inputs"]["image"] = human_path

    if "Tattooimage" in params:
        tattoo_path = os.path.join(job_dir, "tattoo.png")
        save_base64_image(params["Tattooimage"], tattoo_path)
        workflow["96"]["inputs"]["image"] = tattoo_path

    if "mask" in params:
        mask_path = os.path.join(job_dir, "mask.png")
        save_base64_image(params["mask"], mask_path)
        workflow["153"]["inputs"]["image"] = mask_path

    # Save updated workflow
    with open(workflow_file, "w") as f:
        json.dump(workflow, f)

    # Run ComfyUI headless
    cmd = [
        "python", "main.py",
        "--disable-server",
        "--output-directory", output_dir,
        "--quick-test", workflow_file
    ]
    result = subprocess.run(cmd, cwd=WORKDIR, capture_output=True)

    # Collect only final try-on images
    images_b64 = encode_images(output_dir, prefix="ComfyUI")

    # Cleanup job dir (remove temporary workflow and input images)
    shutil.rmtree(job_dir, ignore_errors=True)

    return {
        "stdout": result.stdout.decode(),
        "stderr": result.stderr.decode(),
        "tryon_images": images_b64
    }
