def new_index_map(n, i, j):
    L = list(range(n))
    elem = L.pop(i)
    L.insert(j, "x")

    mapping = {}
    for old in range(n):
        if old == i:
            mapping[old] = None
        else:
            mapping[old] = L.index(old)
    return mapping


# Test -------------------------------------------------------

n = 10
i = 3
j = 7

mapping = new_index_map(n, i, j)

print(f"remove {i}, insert at {j}")
for old, new in mapping.items():
    print(f"{old} -> {new}")

# sanity check
L = list(range(n))
x = L.pop(i)
L.insert(j, "x")
print("final list:", L)
