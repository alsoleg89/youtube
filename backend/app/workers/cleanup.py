import logging
import os
import shutil

from app.core.config import settings

logger = logging.getLogger(__name__)


def cleanup_source_tmp(source_id: str) -> None:
    tmp_path = os.path.join(settings.tmp_dir, source_id)
    if os.path.exists(tmp_path):
        shutil.rmtree(tmp_path, ignore_errors=True)
        logger.info("Cleaned up tmp files for source %s", source_id)
