import runpod
from worker import process_job

# RunPod serverless handler
def run(job):
    return process_job(job)

# Start the handler
runpod.serverless.start({"handler": run})
