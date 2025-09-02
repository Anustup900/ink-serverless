import runpod
from worker import process_job


def run(job):
    """
    RunPod entrypoint.
    Receives a job dict from RunPod, forwards it to process_job,
    and returns the result.
    """
    try:
        return process_job(job)
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Handler error: {repr(e)}",
            "tryon_images": []
        }


# Start RunPod serverless handler
runpod.serverless.start({"handler": run})
