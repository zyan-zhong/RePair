"""One coordinator, fork-isolated sources, deterministic merge, drain on stop."""
import multiprocessing as mp
from multiprocessing.connection import wait
import os,time,traceback

_channel=None
_stop=None

class AdmissionClosed(RuntimeError):pass

def admission_closed():return _stop is not None and _stop.is_set()
def close_admission():
    if _stop is not None:_stop.set()

def check_admission():
    if _stop is not None and _stop.is_set():
        raise AdmissionClosed('PARALLEL_ADMISSION_CLOSED')

def emit(fields):
    if _channel is not None:_channel.send(('progress',fields))

def _worker(fn,item,channel,stop,unused):
    global _channel,_stop
    for fd in unused:fd.close()
    _channel=channel;_stop=stop
    try:channel.send(('result',fn(item)))
    except BaseException as exc:
        stop.set()
        channel.send(('error',type(exc).__name__+':'+str(exc),traceback.format_exc()))
    finally:channel.close()

def map_sources(items,fn,*,key,workers,observe=None,halt=None):
    if type(workers) is not int or workers<1:raise ValueError('REGISTERED_CONCURRENCY_REQUIRED')
    items=list(items);keys=[str(key(x)) for x in items]
    if len(keys)!=len(set(keys)):raise ValueError('INDEPENDENT_SOURCE_KEYS_REQUIRED')
    if not items:return []
    if os.name!='posix':raise RuntimeError('REGISTERED_LINUX_FORK_REQUIRED')
    import threading
    if threading.active_count()!=1:raise RuntimeError('FORK_REQUIRES_SINGLE_COORDINATOR_THREAD')
    ctx=mp.get_context('fork');stop=ctx.Event();active={};values={};errors={};next_index=0
    def snapshot():
        if observe:observe({'coordinator_pid':os.getpid(),'max_concurrent_sources':workers,
            'admission_closed':stop.is_set(),'total_sources':len(items),'closed_sources':len(values),
            'active_calls':[{'source_key':keys[i],'pid':p.pid,'started_unix':start,**fields}
                for i,(p,c,start,fields,done) in sorted(active.items())]})
    try:
        while active or (next_index<len(items) and not stop.is_set()):
            # Drain messages and observe stop BEFORE admitting more sources.
            while next_index<len(items) and len(active)<workers and not stop.is_set():
                i=next_index;next_index+=1;read,write=ctx.Pipe(duplex=False)
                process=ctx.Process(target=_worker,args=(fn,items[i],write,stop,[read,*[v[1] for v in active.values()]]))
                process.start();write.close()
                active[i]=[process,read,time.time(),{'state':'SOURCE_STARTING'},False]
            snapshot()
            ready=wait([v[1] for v in active.values()],timeout=.1) if active else []
            for i,row in list(active.items()):
                process,channel,start,fields,done=row
                if channel in ready:
                    try:message=channel.recv()
                    except EOFError:message=None
                    if message:
                        if message[0]=='progress':row[3]={**message[1],'event_unix':time.time()}
                        elif message[0]=='result':
                            values[i]=message[1];row[4]=True
                            if halt and halt(message[1]):stop.set()
                        elif message[0]=='error':
                            errors[i]=message[1];stop.set();row[4]=True
                if not process.is_alive():
                    # A result may precede exit but follow the last progress message.
                    while channel.poll():
                        try:message=channel.recv()
                        except EOFError:break
                        if message[0]=='result':
                            values[i]=message[1];row[4]=True
                            if halt and halt(message[1]):stop.set()
                        elif message[0]=='error':errors[i]=message[1];stop.set();row[4]=True
                    process.join()
                    if not row[4]:errors[i]='PARALLEL_WORKER_EXIT:'+str(process.exitcode);stop.set()
                    channel.close();del active[i]
        snapshot()
    finally:
        # Never terminate an in-flight provider request to accelerate shutdown.
        stop.set()
        for process,channel,*_ in active.values():
            while process.is_alive():
                if channel.poll(.1):
                    try:channel.recv()
                    except EOFError:break
            process.join();channel.close()
    if errors:
        primary=next((errors[i] for i in sorted(errors) if 'PARALLEL_ADMISSION_CLOSED' not in errors[i]),errors[min(errors)])
        raise RuntimeError(primary)
    return [values[i] for i in sorted(values)]
