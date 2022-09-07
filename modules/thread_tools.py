'''
Created on Oct 19, 2018

@author: wennekt
'''

'''
this is used to run things on parallel
'''

from queue import Queue, Empty
from multiprocessing.dummy import Process, Lock # lock is accessed by others
from itertools import product
import itertools, time

def thread(f, l, thread_count=None):
    if thread_count is None:
        thread_count = len(l)
    iq = Queue()
    oq = Queue()
    [iq.put((n, x)) for n, x in enumerate(l)]
    ps = [Process(target=worker, args=(f, iq, oq)) for _ in range(thread_count)]
    [p.start() for p in ps]
    [p.join() for p in ps]
    vals = []
    [vals.insert(n, val) for n, val in list(oq.queue)]
    return vals
    
def worker(f, iq, oq):
    while True:
        try:
            n, x = iq.get_nowait()
        except Empty:
            break
        oq.put((n, f(*x)))
        
def zipper(*ls):
    return list(product(*ls))

class Worker:
    
    def __init__(self, num_workers):
        self.queue_lock = Lock()
        self.queue_ids = itertools.count(start=0, step=1)
        self.browser_iq = {}
        self.browser_oq = {}
        self.num_workers = num_workers
        self.ps = []
        self.queue_count = 0
        self.kill = False
        self.running = set()
    
    def start(self):
        def f():
            while True:
                self.queue_lock.acquire()
                keys = list(self.browser_iq.keys())
                if len(keys) > 0:
                    i = keys[0]
                    f, args = self.browser_iq[i]
                    self.browser_iq.pop(i)
                    self.queue_count -= 1
                    print(i, 'started.', self.running, 'still running', self.queue_count, 'still queued')
                    self.running.add(i)
                    self.queue_lock.release()
                    if args is None:
                        val = f()
                    else:
                        val = f(*args)
                    self.queue_lock.acquire()
                    self.running.remove(i)
                    print(i, 'ran.', self.running, 'still running', self.queue_count, 'still running')
                    self.browser_oq[i] = val
                    self.queue_lock.release()
                else:
                    self.queue_lock.release()
                    if self.kill:
                        break
        self.ps = [Process(target=f) for _ in range(self.num_workers)]
        [p.start() for p in self.ps]
        
    def join(self):
        self.kill = True
        [p.join() for p in self.ps]
                
    def add_to_queue(self, f, args=None):
        self.queue_lock.acquire()
        i = next(self.queue_ids)
        print(i, 'queueing')
        self.browser_iq[i] = (f, args)
        self.queue_count += 1
        self.queue_lock.release()
        return i
    
    def get_from_queue(self, i):
        while True:
            self.queue_lock.acquire()
            try:
                val = self.browser_oq[i]
                self.queue_lock.release()
                break
            except:
                self.queue_lock.release()
        return val
    
    def func(self, f, args=None):
        return self.get_from_queue(self.add_to_queue(f, args))
    
class Browsers():
    
    def __init__(self, browser_fs):
        self.browser_fs = browser_fs
        self.browsers = []
        self.ps = [Process(target=self.run_f, args=(browser_n,)) for browser_n, _ in enumerate(self.browser_fs)]
        self.f_q = Queue()
        self.results_q = Queue()
        self.results = {}
        self.i = 0
        self.i_lock = Lock()
        self.results_lock = Lock()
        self.running_q = Queue()
        self.kill = True
        
    def add_to_queue(self, f, non_browser_args=None):
        self.i_lock.acquire()
        i = self.i
        self.i += 1
        self.i_lock.release()
        self.f_q.put((i, f, non_browser_args))
        return i
    
    def get_from_queue(self, i):
        while True:
            self.results_lock.acquire()
            results = self.results
            self.results_lock.release()
            if i in results:
                return results[i]
            else:
                time.sleep(3)
        
    def run_f(self, browser_n):
        browser = self.browsers[browser_n]
        while True:
            run = True
            try:
                self.running_q.put(None)
                i, f, non_browser_args = self.f_q.get_nowait()
            except Empty:
                self.running_q.get_nowait()
                if self.kill:
                    break
                time.sleep(3)
                run = False
            if run:
                if non_browser_args is None:
                    args = (browser,)
                else:
                    args = tuple([browser] + list(non_browser_args))
                result = f(*args)
                self.results_q.put(result)
                self.results_lock.acquire()
                self.results[i] = result
                self.results_lock.release()
                self.running_q.get_nowait()
        browser.quit()
        
    def start(self):
        self.kill = False
        self.browsers = [browser_f() for browser_f in self.browser_fs]
        [p.start() for p in self.ps]
                
    def join(self):
        time.sleep(2)
        self.kill = True
        [p.join() for p in self.ps]
        
    def get_next_result(self):
        try:
            return self.results_q.get_nowait()
        except Empty:
            raise ValueError('queue is empty')
        
    def run_all_browsers(self, f, l_args=None):
        if l_args is not None:
            l = []
            pool = itertools.cycle(l_args)
            for browser in self.browsers:
                l.append((browser, *next(pool)))
        else:
            l = [(browser,) for browser in self.browsers]
        return thread(f=f, l=l)
    
    def get_results(self):
        while self.is_active():
            pass
        return [self.results[k] for k in sorted(list(self.results.keys()))]
    
    def flush_results(self):
        results = self.get_results()
        self.i = 0
        self.results_q = Queue()
        self.results = {}
        return results
        
    def is_active(self):
        return not (self.running_q.empty() and self.f_q.empty())
    
class BrowserWorker(Worker):
      
    def __init__(self, num_workers, browser_f):
        super(BrowserWorker, self).__init__(num_workers)
        self.browser_f = browser_f
          
    def start(self):
        print('starting')
        def f():
            browser = self.browser_f()
            while True:
                self.queue_lock.acquire()
                keys = list(self.browser_iq.keys())
                if len(keys) > 0:
                    i = keys[0]
                    f, args = self.browser_iq[i]
                    self.browser_iq.pop(i)
                    self.queue_count -= 1
                    print(i, 'started.', self.running, 'still running')
                    self.running.add(i)
                    self.queue_lock.release()
                    if args is None:
                        val = f(browser)
                    else:
                        args = tuple([browser] + list(args))
                        val = f(*args)
                    self.queue_lock.acquire()
                    self.running.remove(i)
                    print(i, 'ran.', self.running, 'still running')
                    self.browser_oq[i] = val
                    self.queue_lock.release()
                else:
                    self.queue_lock.release()
                    if self.kill:
                        browser.quit()
                        break
        self.ps = [Process(target=f) for _ in range(self.num_workers)]
        [p.start() for p in self.ps]