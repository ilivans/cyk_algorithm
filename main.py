from cfg import CNF
import re

with open("gram.in", "r") as ifs:
    n = int(ifs.readline())
    lines = []
    for _ in range(n):
        lines.append(ifs.readline())

try:
    cnf = CNF(lines)
except (ValueError, TypeError) as e:
    print(e)
    exit(-1)

# print(cnf)

re_string = re.compile("[a-z]*")
m = int(input())
for _ in range(m):
    w = input()
    if re.fullmatch(re_string, w) is None:
        print(w + " - illegal word")
        continue
    if cnf.parse(w):
        print("YES")
    else:
        print("NO")
