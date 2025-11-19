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





                # Apply constraint from higher anchor (working backwards)
                if higher_anchor_pos is not None:
                    # This value must fit in the remaining_copies positions before higher_anchor_pos
                    # So it cannot appear before position (higher_anchor_pos - remaining_copies)
                    min_pos = higher_anchor_pos - remaining_copies
                    for pos in range(0, min_pos):
                        if pos < W:
                            before_size = len(self.beliefs[player_id][pos])
                            self.beliefs[player_id][pos].discard(value)
                            if len(self.beliefs[player_id][pos]) < before_size:
                                changed = True
                
                # Apply constraint from lower anchor (working forwards)
                if lower_anchor_pos is not None:
                    # This value must fit in the remaining_copies positions after lower_anchor_pos
                    # So it cannot appear after position (lower_anchor_pos + remaining_copies)
                    max_pos = lower_anchor_pos + remaining_copies
                    for pos in range(max_pos, W):
                        before_size = len(self.beliefs[player_id][pos])
                        self.beliefs[player_id][pos].discard(value)
                        if len(self.beliefs[player_id][pos]) < before_size:
                            changed = True
        