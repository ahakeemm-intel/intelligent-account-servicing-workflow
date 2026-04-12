"""
Mock FileNet service — simulates archival to an enterprise document management system.

Documents are stored on the local filesystem under FILENET_STORE_PATH.
A generated reference ID would be the DMS object ID in production.
"""
import os
import uuid
import shutil
from datetime import datetime
from loguru import logger
from app.core.config import settings


def _store_root() -> str:
    path = settings.FILENET_STORE_PATH
    if not os.path.isabs(path):
        path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "../../../../", path)
        )
    os.makedirs(path, exist_ok=True)
    return path


def archive_document(
    source_path: str,
    request_id: str,
    document_type: str,
    original_filename: str,
) -> tuple[str, str]:
    """
    Archive a document to the FileNet mock store.

    Returns:
        (stored_path, filenet_reference_id)
    """
    root = _store_root()
    request_dir = os.path.join(root, request_id)
    os.makedirs(request_dir, exist_ok=True)

    ext = os.path.splitext(original_filename)[1]
    stored_filename = f"{document_type}_{uuid.uuid4().hex[:8]}{ext}"
    dest_path = os.path.join(request_dir, stored_filename)

    shutil.copy2(source_path, dest_path)

    # Generate a FileNet-style reference ID
    filenet_ref = f"FN-{request_id[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"

    logger.info(
        "FileNet archive | request={} | type={} | ref={} | path={}",
        request_id, document_type, filenet_ref, dest_path,
    )
    return dest_path, filenet_ref
