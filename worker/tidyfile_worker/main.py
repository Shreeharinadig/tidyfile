"""Worker entry point.

Placeholder for week 2: this will poll the SQS queue and run the pipeline
(profile, map, clean, report). For now it only starts, logs its configuration,
and idles, so the container stays up in Docker Compose.
"""

from __future__ import annotations

import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("tidyfile.worker")


def main() -> None:
    log.info(
        "worker started (queue=%s, endpoint=%s)",
        os.getenv("JOBS_QUEUE_NAME", "tidyfile-jobs"),
        os.getenv("AWS_ENDPOINT_URL", "aws"),
    )
    while True:
        time.sleep(30)


if __name__ == "__main__":
    main()
