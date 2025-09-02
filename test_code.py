# test_local.py
from worker import process_job
import base64

# load a test image
with open("test_human.jpg", "rb") as f:
    human_b64 = base64.b64encode(f.read()).decode("utf-8")

with open("test_tattoo.png", "rb") as f:
    tattoo_b64 = base64.b64encode(f.read()).decode("utf-8")

with open("test_mask.png", "rb") as f:
    mask_b64 = base64.b64encode(f.read()).decode("utf-8")

job = {
    "input": {
        "params": {
            "width": 1024,
            "height": 1536,
            "tryon_seed": 12345,
            "human_image": human_b64,
            "Tattooimage": tattoo_b64,
            "mask": mask_b64
        }
    }
}

result = process_job(job)
print(result)
