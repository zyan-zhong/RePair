"""Entry inside an existing authorized allocation; never submits a scheduler job."""
import argparse
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binding', required=True)
    parser.add_argument('--binding-sha256', required=True)
    parser.add_argument('--mode', choices=('single','worker','finalize'), required=True)
    parser.add_argument('--host')
    parser.add_argument('--port', type=int)
    parser.add_argument('--shard-id', type=int)
    parser.add_argument('--resumption-ordinal', type=int)
    args = parser.parse_args()
    ref = {'path': args.binding, 'sha256': args.binding_sha256}
    if args.mode == 'finalize':
        from .parallel import finalize_parallel
        result = finalize_parallel(ref)
    else:
        if args.host is None or args.port is None:
            parser.error('worker/single requires --host and --port')
        if args.mode == 'worker':
            if args.shard_id is None or args.resumption_ordinal is None:
                parser.error('worker requires --shard-id and --resumption-ordinal')
            from .parallel import execute_parallel_worker
            result = execute_parallel_worker(ref, shard_id=args.shard_id, resumption_ordinal=args.resumption_ordinal,
                                            host=args.host, port=args.port)
        else:
            from .execute import execute_binding
            result = execute_binding(ref, host=args.host, port=args.port)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
