import asyncio
import heapq
import itertools

from fastapi import HTTPException
from bsutils.apimodels.pick_message import BSTelegramMessage


def _to_bs_message(msg, user_id: str) -> BSTelegramMessage:
    """Convert a raw Telethon Message to a BSTelegramMessage."""
    return BSTelegramMessage(
        telegram_message_id=str(msg.id),
        from_user_id=user_id,
        from_telegram_chat_id=str(msg.chat.id),
        from_telegram_chat_name=msg.chat.title,
        content=msg.message or "",
        timestamp=msg.date.isoformat() if msg.date else None,
    )


async def get_n_messages_kway_merge(
    client,
    channel_names: list[str],
    n: int,
    user_id: str,
) -> list[BSTelegramMessage]:
    """
    Returns the n most-recent messages across ``channel_names`` using a k-way merge.

    Algorithm
    ---------
    1. Open one async generator per channel via ``iter_messages_from_dialog``
       (lazy — no network call yet).
    2. **Prime** every generator concurrently with ``asyncio.gather``: each one
       performs its first Telegram API call in parallel, fetching ``page_size``
       messages.  The head message of each non-empty stream is pushed onto a
       max-heap keyed by timestamp.
    3. Repeatedly pop the freshest message from the heap, append it to the
       result, and advance *only that channel's* generator by one position.
       If the generator yields a next message it is pushed back onto the heap.
    4. Stop as soon as ``n`` messages have been collected or all streams are
       exhausted.  Any unconsumed generators are closed so Telethon releases
       its resources.

    Complexity
    ----------
    * Network: ~⌈n/k⌉ messages fetched per channel on average (k = # channels),
      vs. n per channel in the naïve approach.
    * CPU:     O(n · log k) heap operations.
    """
    generators = [
        client.iter_messages_from_dialog(ch)
        for ch in channel_names
    ]

    # Heap entries: (-timestamp_float, tiebreak_int, channel_idx, raw_message)
    # The tiebreak counter prevents Python from comparing Telethon Message
    # objects when two messages share the exact same timestamp.
    heap: list[tuple] = []
    _tiebreak = itertools.count()

    async def _prime(idx_: int, gen_) -> None:
        """Fetch the first message of generator[idx] and push it onto the heap."""
        try:
            msg = await gen_.__anext__()
        except StopAsyncIteration:
            return  # Channel has no messages — skip silently
        except LookupError as exc_:
            raise HTTPException(status_code=404, detail=str(exc_))
        except ValueError as exc_:
            raise HTTPException(status_code=400, detail=str(exc_))
        except Exception as exc_:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read from channel '{channel_names[idx_]}': {exc_}",
            )
        ts = msg.date.timestamp() if msg.date else 0.0
        heapq.heappush(heap, (-ts, next(_tiebreak), idx_, msg))

    # ── Step 2: prime all generators concurrently ──────────────────────────
    await asyncio.gather(*[_prime(i, g) for i, g in enumerate(generators)])

    result: list[BSTelegramMessage] = []

    # ── Steps 3-4: k-way merge ─────────────────────────────────────────────
    while heap and len(result) < n:
        _, _, idx, msg = heapq.heappop(heap)
        result.append(_to_bs_message(msg, user_id))

        # Advance this channel's stream and push its next message onto the heap.
        try:
            next_msg = await generators[idx].__anext__()
            ts = next_msg.date.timestamp() if next_msg.date else 0.0
            heapq.heappush(heap, (-ts, next(_tiebreak), idx, next_msg))
        except StopAsyncIteration:
            pass  # This channel is exhausted — it simply leaves the heap
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error reading messages from channel '{channel_names[idx]}': {exc}",
            )

    # ── Step 5: release unconsumed generators ──────────────────────────────
    for gen in generators:
        await gen.aclose()

    return result

