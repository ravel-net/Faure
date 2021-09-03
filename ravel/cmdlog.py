import os
class CmdLog(object):
    def __init__(self):
        self.log = None
        try:
            self.log = open(os.path.expanduser('~/cmdlog.txt'), 'a+')
        except Exception, e:
            print('Failed to open log file: ' + str(e).strip())
    def logline(self, line):
        if self.log is None:
            print 'Failed to open log file.'
            return
        self.log.write(line+'\n')
    def __del__(self):
        if self.log is not None:
            self.log.close()
cmdLogger = CmdLog()
