from __future__ import annotations
import math

def shard_positions(total_cells:int, shard_count:int, shard_id:int)->tuple[int,...]:
    if type(total_cells) is not int or total_cells<=0: raise ValueError("TOTAL_CELLS")
    if type(shard_count) is not int or shard_count<=0: raise ValueError("SHARD_COUNT")
    if type(shard_id) is not int or not (0<=shard_id<shard_count): raise ValueError("SHARD_ID")
    return tuple(i for i in range(total_cells) if i % shard_count == shard_id)

def derive_shard_walltime_minutes(
    *, total_cells:int, shard_count:int, seconds_per_episode:float,
    safety_multiplier:float, fixed_overhead_seconds:float,
    minimum_minutes:int,
)->int:
    if seconds_per_episode<=0 or safety_multiplier<1 or fixed_overhead_seconds<0:
        raise ValueError("TIMING_AUTHORITY")
    max_cells=math.ceil(total_cells/shard_count)
    seconds=(
        fixed_overhead_seconds
        + max_cells*seconds_per_episode*safety_multiplier
    )
    return max(int(minimum_minutes), math.ceil(seconds/60.0))
