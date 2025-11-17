import numpy as np

K = 6            # Number of distinct wire values
r_k = 4          # Copies of each value
W = 6 # wires per player
# for loop descending from K to 1
for value in range(K, 0, -1):
    threshold = W - r_k
    if threshold > 0:
        for pos in range(threshold, W):
            print(f"Eliminating value {value} from position {pos}")
        threshold -= r_k
    else:
        break

for value in range(1, K + 1):
    threshold = r_k - 1
    if threshold < W:
        for pos in range(0, threshold + 1):
            print(f"Eliminating value {value} from position {pos}")
        threshold += r_k
    else:
        break
