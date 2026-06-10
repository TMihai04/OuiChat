# Attachments related endpoints

from ouichat_backend.utils.logger import logger
from ouichat_backend.utils import (
    AttachmentDocument,
    GenericItemResponse,
    ATTACHMENTS_DIR,
    ICONS_DIR,
    EndpointTags,
    EndpointPrefixes,
)
from ouichat_backend.utils.methods import (
    decode_sub_access_token,
    timestamp_now,
    get_uuid4,
    db,
)

from . import _valids

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from fastapi.responses import FileResponse
from typing import Literal
from pathlib import Path

import aiofiles
import os


router = APIRouter(
    prefix=EndpointPrefixes.ATTACHMENTS.value, # pyright: ignore
    tags=[EndpointTags.ATTACHMENTS]
)


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/octet-stream": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    }
                }
            },
            "required": True,
        }
    }
)
async def upload_new_file(
    request: Request,
    file_type: Literal["attachment", "icon"],
    x_original_filename: str = Header("unknown_file"),
    username: str = Depends(decode_sub_access_token)
) -> GenericItemResponse:
    """Use this endpoint to upload a file. File upload limits are imposed by the reverse proxy guarding the server and are thus not checked by the API while processing the byte stream (TODO?).

    This endpoint expects certain header parameters:
    - `X-Original-Filename` should be set to full name of the file (eg. X-Original-Filename: 'my_picture.jpg'). If this header is not provided the filename defaults to 'unknown_file'
    - `Content-Type` must be set to 'application/octet-stream' to ensure client does not send multi-part/form data
    
    Args:
    * `file_type`: The purpose the uploaded file is supposed to serve, either message attchment or display icon
    * `body`: An binary stream with the file's contents
    
    Returns:
    * `GenericItemResponse`: A dictionary containing the id of the newly uploaded file
    
    Throws:
    * `415`: 'application/octet-stream' not proivded as the content type header value"""

    logger.debug(f"Uploading file - username: {username} - type: {file_type} - filename: {x_original_filename}")

    # Enforce content-type
    if request.headers.get("content-type") != "application/octet-stream":
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Must send `application/octet-stream`"
        )
    
    file_id = get_uuid4()
    disk_filename = f"{file_id}_{x_original_filename}"

    file_path = os.path.join(
        ATTACHMENTS_DIR if file_type == "attachment" else ICONS_DIR, disk_filename
    )

    try:
        # Firstly write the whole file to disk
        async with aiofiles.open(file_path, "wb") as f:
            async for chunk in request.stream():
                await f.write(chunk)
        
        # Add entry to db
        await db.add_attachment(
            AttachmentDocument(
                attachment_id=file_id,
                path=file_path,
                uploader=username,
                created_at=timestamp_now()
            )
        )
    except Exception as e:
        logger.error(f"Upload failed - filename: {x_original_filename} - error: {str(e)}")

        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Upload failed"
        )
    
    logger.info(f"Uploaded file - username: {username} - type: {file_type} - filename: {x_original_filename}")
    
    return GenericItemResponse(
        item={"file_id": file_id}
    )


@router.get(
    "/download",
    status_code=status.HTTP_200_OK
)
async def download_file(
    file: AttachmentDocument = Depends(_valids.validate_file),
    username: str = Depends(decode_sub_access_token)
) -> FileResponse:
    """Use this endpoint to download a file.
    
    Args:
    * `file_id`: Target file id
    
    Returns:
    * `FileResponse`: A byte stream containing the file's contents and metadata
    
    Throws:
    * `404`: File not found in storage"""

    logger.debug(f"Downloading file - username: {username} - file_id: {file.attachment_id}")

    file_path = Path(file.path)
    if not os.path.exists(file_path):
        logger.error(f"File not found on disk. Removing db entry if existent - file_id: {file.attachment_id}")

        await db.delete_attachment(file.attachment_id)

        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "File not found"
        )
    
    filename_with_id = file_path.parts[-1]
    filename = "_".join(filename_with_id.split("_")[1:])

    logger.info(f"Downloaded file - username: {username} - file_id: {file.attachment_id}")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )
    