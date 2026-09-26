with open(r"c:\Users\sitak\SATARK\backend\simulation\engine.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

method_starts = []
for i, line in enumerate(lines):
    if line.startswith("    def ") or line.startswith("    @property"):
        method_starts.append((i + 1, line.strip()))

for idx in range(len(method_starts)):
    line_no, sig = method_starts[idx]
    next_line = method_starts[idx + 1][0] if idx + 1 < len(method_starts) else len(lines)
    length = next_line - line_no
    if length > 30:
        print(f"L{line_no:4d} (len {length:4d}): {sig}")
