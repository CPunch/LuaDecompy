import sys
import lundump
import lparser

lc = lundump.LuaUndump()
print(sys.argv[1])
chunk = lc.loadFile(sys.argv[1])

lc.print_dissassembly()
lp = lparser.LuaDecomp(chunk)