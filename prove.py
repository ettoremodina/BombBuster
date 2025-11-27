import multiprocessing as mp
import math

def burn():
    x = 0.0
    while True:
        x = math.sin(x) * math.cos(x) * math.tan(x)  # keeps the CPU busy

if __name__ == "__main__":
    n = mp.cpu_count()
    procs = []
    for _ in range(n):
        p = mp.Process(target=burn)
        p.start()
        procs.append(p)
    for p in procs:
        p.join()
