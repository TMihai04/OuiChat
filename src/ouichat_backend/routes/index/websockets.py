# Websocket related endpoints

from ouichat_backend.utils.logger import logger
from ouichat_backend.utils.manager import ws_manager
from ouichat_backend.utils import (
    WS_CREDENTIALS_EXCEPTION,
    GenericItemsResponse,
    GenericMessageResponse,
    GenericItemResponse,
    WebsocketUpdate,
    EndpointTags,
    EndpointPrefixes,
)
from ouichat_backend.utils.methods import (
    ws_decode_access_token,
    decode_token,
    datetime_from_timestamp,
    get_uuid4,
)

from . import _bodies

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, WebSocketException, status
from datetime import datetime, timezone, timedelta
from json.decoder import JSONDecodeError

import asyncio


router = APIRouter(
    prefix=EndpointPrefixes.WEBSOCKET.value,
    tags=[EndpointTags.WEBSOCKET]
)


async def _token_expiration_notifier(
    username: str,
    websocket: WebSocket,
    exp_time: datetime,
    grace_period: timedelta = timedelta(minutes=1)
):
    now = datetime.now(timezone.utc)
    notify_time = exp_time - grace_period
    wait_seconds = (notify_time - now).total_seconds()

    # logger.debug(f"{exp_time}, {notify_time}, {wait_seconds}")

    if wait_seconds > 0:
        logger.debug(f"Sleeping for {timedelta(seconds=wait_seconds)}")
        await asyncio.sleep(wait_seconds)

    try:
        logger.debug(f"Notifying websocket about access token expiry - username: {username}")

        await ws_manager.notify(
            websocket,
            payload=WebsocketUpdate(
                type="system",
                scope="token.access",
                data={
                    "message": f"Current access token is about to expire"
                }
            )
        )
    except Exception as e:
        logger.error(f"Error occured during websocket access token expiry time notification: {e}")
        pass
    
    await asyncio.sleep(grace_period.total_seconds())
    try:
        await ws_manager.disconnect(
            username=username,
            webscoket=websocket,
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Access token expired",
            close=True
        )
    except Exception:
        logger.error(f"Error occured when closing websocket due to access token expiring: {e}")
        pass


async def _broadcast_presence(username: str, online: bool) -> None:
    await ws_manager.notify_all(
        payload=WebsocketUpdate(
            event_id=get_uuid4(),
            type="update",
            scope="user.presence",
            data={
                "username": username,
                "online": online,
            },
        ),
        mode="binary",
    )


async def _send_presence_snapshot(websocket: WebSocket) -> None:
    await ws_manager.notify(
        websocket,
        payload=WebsocketUpdate(
            event_id=get_uuid4(),
            type="update",
            scope="user.presence",
            data={
                "usernames": ws_manager.online_usernames(),
            },
        ),
        mode="binary",
    )


def _note_disconnect(username: str) -> None:
    ws_manager.schedule_offline(username, lambda: _broadcast_presence(username, False))


@router.websocket("/global")
async def global_comm_ws(
    websocket: WebSocket,
    payload: dict = Depends(ws_decode_access_token),
):
    logger.debug(f"weboscket connected - payload: {payload}")

    username = payload.get("sub")
    ws_manager.cancel_offline(username)
    await ws_manager.connect(
        username,
        websocket
    )
    if ws_manager.connection_count(username) == 1:
        await _broadcast_presence(username, True)
    await _send_presence_snapshot(websocket)

    notifier_task = asyncio.create_task(_token_expiration_notifier(
        username=payload.get("sub"),
        websocket=websocket,
        exp_time=datetime_from_timestamp(payload.get("exp"))
    ))
    
    while True:
        # logger.debug(f"debug - webscoket: {websocket}")
        try:
            recv_js = await asyncio.wait_for(
                websocket.receive_json(mode="binary"),
                1
            )

            if recv_js.get("access_token"):
                try:
                    decoded_token = decode_token(recv_js.get("access_token"))

                    # TODO: Check if new token's owner is the same as old owner
                except Exception as e:
                    raise WS_CREDENTIALS_EXCEPTION

                try:
                    notifier_task.cancel()
                except Exception:
                    pass

                notifier_task = asyncio.create_task(_token_expiration_notifier(
                    username=payload.get("sub"),
                    websocket=websocket,
                    exp_time=datetime_from_timestamp(decoded_token.get("exp"))
                ))
        except TimeoutError:
            pass
        except JSONDecodeError:
            logger.warning("Non JSON byte frame received")
        except KeyError:
            logger.warning("Non binary frame received")
        except WebSocketDisconnect as e:
            logger.error(f"WebsocketDisconnect error: {str(e)}")

            await ws_manager.disconnect(
                username=payload.get("sub"),
                webscoket=websocket,
                close=False
            )
            _note_disconnect(payload.get("sub"))
            break
        except WebSocketException as e:
            logger.error(f"WebsocketException: {str(e)}")

            await ws_manager.disconnect(
                username=payload.get("sub"),
                webscoket=websocket,
                code=e.code,
                reason=e.reason,
                close=True
            )
            _note_disconnect(payload.get("sub"))
            break
    
    try:
        notifier_task.cancel()
    except Exception:
        pass

        
