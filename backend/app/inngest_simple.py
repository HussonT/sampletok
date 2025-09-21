"""
Simplified Inngest function for testing
"""
import inngest
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Initialize Inngest client
inngest_client = inngest.Inngest(
    app_id="sampletok-test",
    is_production=False
)


@inngest_client.create_function(
    fn_id="simple-tiktok-processor",
    trigger=inngest.TriggerEvent(event="tiktok/video.submitted")
)
def simple_process_video(ctx, step) -> Dict[str, Any]:
    """Simple test function that just logs and returns"""
    try:
        event_data = ctx.event.data
        sample_id = event_data.get("sample_id")
        url = event_data.get("url")

        logger.info(f"Processing video: {url} for sample: {sample_id}")
        print(f"Processing video: {url} for sample: {sample_id}")

        # Simple step that just logs
        def log_step():
            print(f"Step executed for sample: {sample_id}")
            return {"status": "logged"}

        result = step.run("log-step", log_step)

        return {
            "sample_id": sample_id,
            "status": "success",
            "message": f"Processed {url}",
            "step_result": result
        }
    except Exception as e:
        logger.error(f"Error in simple_process_video: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }


def get_simple_functions():
    """Return the simple test function"""
    return [simple_process_video]