"""
Library for profiling operations in Ravel.

Ravel's profiling library uses message queues since a execution of a command
may span across multiple processes.   For example, operations for adding or
removing a flow execute in two processes: the database trigger and the OpenFlow
manager.  Results then are reported to a third process: the CLI.
"""

import pickle
import sysv_ipc
import threading
import time
from collections import OrderedDict

import ravel.messaging
from ravel.log import logger

ProfileQueueId = 99999
ProfileOff = "1"
ProfileOn = "2"

def enable_profiling():
    "Enable profiling"
    shm = sysv_ipc.SharedMemory(ProfileQueueId,
                                flags=sysv_ipc.IPC_CREAT,
                                mode=0o777,
                                size=sysv_ipc.PAGE_SIZE,
                                init_character=" ")
    shm.write(str(ProfileOn))
    shm.detach()

def disable_profiling():
    "Disable profiling"
    shm = sysv_ipc.SharedMemory(ProfileQueueId,
                                flags=sysv_ipc.IPC_CREAT,
                                mode=0o7777,
                                size=sysv_ipc.PAGE_SIZE,
                                init_character=" ")
    shm.write(str(ProfileOff))
    shm.detach()

def is_profiled():
    "Check if profiling is enabled"
    try:
        shm = sysv_ipc.SharedMemory(ProfileQueueId)
        return shm.read().strip("\0") == ProfileOn
    except sysv_ipc.ExistentialError as e:
        logger.warning("profile queue doesn't exist: %", e)
        return False

class PerfCounter(object):
    "Store timing information for a single operation"

    def __init__(self, name, time_ms=None):
        """name: the name of the operation
           time_ms: the execution time of the operation, if already
           recorded"""
        self.name = name
        self.start_time = None
        self.time_ms = time_ms
        if self.time_ms is not None:
            self.time_ms = round(float(time_ms), 3)

    def start(self):
        "Start recording execution time of an operation"
        if is_profiled():
            self.start_time = time.time()

    def stop(self):
        "Stop recording execution time of an operation"
        if self.start_time is not None:
            self.time_ms = round((time.time() - self.start_time) * 1000, 3)
            self.report()

    def consume(self, consumer):
        """Consume the performance counter
           consumer: a ProfiledExecution instance to consume the counter"""
        consumer.handler(self)

    def report(self):
        "Report the performance counter by adding it to the message queue"
        try:
            if is_profiled():
                mq = sysv_ipc.MessageQueue(ProfileQueueId, mode=0o777)
                mq.send(pickle.dumps(self))
        except Exception as e:
            print(e)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{0}:{1}".format(self.name, self.time_ms)

class ProfiledExecution(object):
    "Start a new profiled execution and collect performance counters"

    def __init__(self):
        self.counters = []
        self.receiver = ravel.messaging.MsgQueueReceiver(ProfileQueueId, self)

    def print_summary(self):
        "Print results of collected performance counters"
        if len(self.counters) == 0:
            print("No performance counters found")
            return

        agg = OrderedDict()
        summ = 0
        print("-" * 40)
        for counter in self.counters:
            summ += counter.time_ms

            if counter.name not in list(agg.keys()):
                agg[counter.name] = (1, counter.time_ms)
            else:
                count,ms =  agg[counter.name]
                agg[counter.name] = (count + 1, ms + counter.time_ms)

        for counter, tup in agg.items():
            print("{0}({1}): {2}ms".format(counter, tup[0], tup[1]))

        print("-" * 40)
        print("Total: {0}ms".format(summ))

    def start(self):
        "Enable profiling and start receiving performance counters"
        enable_profiling()
        self.receiver.start()

    def stop(self):
        "Disable profiling and stop receiving performance counters"
        self.receiver.stop()
        disable_profiling()

    def handler(self, obj):
        """Callback for consuming performance counters
           obj: a PerfCounter object"""
        if obj is not None:
            self.counters.append(obj)
