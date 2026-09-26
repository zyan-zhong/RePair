from __future__ import annotations

import socket
from typing import Iterable

from .contract import Stage4DFullError

PARALLEL_SHARD_COUNT = 4


def shard_for_ordinal(ordinal: int, *, shard_count: int = PARALLEL_SHARD_COUNT) -> int:
    if type(ordinal) is not int or ordinal < 0:
        raise Stage4DFullError("PARALLEL_ORDINAL_INVALID")
    if type(shard_count) is not int or shard_count <= 0:
        raise Stage4DFullError("PARALLEL_SHARD_COUNT_INVALID")
    return ordinal % shard_count


def remaining_ordinals(*, completed_prefix_count: int, total_pairs: int) -> tuple[int, ...]:
    if type(completed_prefix_count) is not int or type(total_pairs) is not int:
        raise Stage4DFullError("PARALLEL_PAIR_COUNT_INVALID")
    if completed_prefix_count < 0 or total_pairs < 0 or completed_prefix_count > total_pairs:
        raise Stage4DFullError("PARALLEL_COMPLETED_PREFIX_INVALID")
    return tuple(range(completed_prefix_count, total_pairs))


def partition_ordinals(
    ordinals: Iterable[int],
    *,
    shard_count: int = PARALLEL_SHARD_COUNT,
) -> tuple[tuple[int, ...], ...]:
    if type(shard_count) is not int or shard_count <= 0:
        raise Stage4DFullError("PARALLEL_SHARD_COUNT_INVALID")
    buckets: list[list[int]] = [[] for _ in range(shard_count)]
    observed: set[int] = set()
    for ordinal in ordinals:
        if type(ordinal) is not int or ordinal < 0:
            raise Stage4DFullError("PARALLEL_ORDINAL_INVALID")
        if ordinal in observed:
            raise Stage4DFullError("PARALLEL_ORDINAL_DUPLICATED")
        observed.add(ordinal)
        buckets[shard_for_ordinal(ordinal, shard_count=shard_count)].append(ordinal)
    return tuple(tuple(bucket) for bucket in buckets)


def split_visible_devices(value: str) -> tuple[str, ...]:
    devices = tuple(part.strip() for part in value.split(",") if part.strip())
    if len(devices) != PARALLEL_SHARD_COUNT or len(set(devices)) != PARALLEL_SHARD_COUNT:
        raise Stage4DFullError(
            "PARALLEL_VISIBLE_GPU_SET_INVALID:expected=4:observed=" + repr(devices)
        )
    return devices



def require_single_visible_device(value: str) -> str:
    devices = tuple(part.strip() for part in value.split(",") if part.strip())
    if len(devices) != 1:
        raise Stage4DFullError(
            "PARALLEL_WORKER_VISIBLE_GPU_INVALID:expected=1:observed=" + repr(devices)
        )
    return devices[0]

def allocate_free_ports(count: int) -> tuple[int, ...]:
    if type(count) is not int or count <= 0:
        raise Stage4DFullError("PARALLEL_PORT_COUNT_INVALID")
    sockets: list[socket.socket] = []
    try:
        ports: list[int] = []
        for _ in range(count):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            sockets.append(sock)
            ports.append(sock.getsockname()[1])
        if len(set(ports)) != count:
            raise Stage4DFullError("PARALLEL_PORT_DUPLICATED")
        return tuple(ports)
    finally:
        for sock in sockets:
            sock.close()
