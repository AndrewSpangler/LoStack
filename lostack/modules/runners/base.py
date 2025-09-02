import os
import subprocess
import threading

class RunBase:
    """Default runner, runs a shell command"""
    def __init__(self, call, result_queue, complete=False, work_dir="/docker"):
        self.call = call
        self.queue = result_queue
        self.complete_at_end = complete
        self.work_dir = work_dir

    def run(self):
        oldcwd = os.getcwd()
        self.status = None
        try:
            def queue_std(pipe, tag):
                for line in iter(pipe.readline, ''):
                    msg = tag + line.strip()
                    self.queue.put_nowait(msg)
                pipe.close()

            os.chdir(self.work_dir)
            process = subprocess.Popen(
                self.call,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            stdout_thread = threading.Thread(target=queue_std, args=(process.stdout, f"stdout: "))
            stderr_thread = threading.Thread(target=queue_std, args=(process.stderr, f"stderr: "))
            stdout_thread.start()
            stderr_thread.start()
            process.wait()
            stdout_thread.join()
            stderr_thread.join()
        except Exception as e:
            self.status = e
        os.chdir(oldcwd)
        if self.complete_at_end:
            self.queue.put_nowait("__COMPLETE__")
        if self.status:
            raise self.status
        return self.queue