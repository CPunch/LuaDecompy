# LuaDecompy

An experimental Lua 5.1 dump decompiler (typically dumped using `luac -o <out.luac> <script.lua>`).

You will quickly find that only **extremely** simple scripts are decompiled successfully right now. This is an experimental project and not all opcodes are properly handled for now. If you need a real decompiler I would recommend any of the handful of ones that exist already.

## Why?

Lua has a relatively small instruction set (only 38 different opcodes!). This makes it pretty feasible for a weekend decompiler project. (real) Decompilers are extremely complex pieces of software, so being able to write a simpler one helps show the theory without *much* of the headache.

## Example usage

```sh
> cat example.lua && luac5.1 -o example.luac example.lua
local tbl = {"He", "llo", " ", "Wo", "rld", "!"}
local str = ""

for i = 1, #tbl do
    str = str .. tbl[i]
end

print(str)
> python main.py example.luac
example.luac

==== [[example.lua's constants]] ====

0: [STRING] He
1: [STRING] llo
2: [STRING]  
3: [STRING] Wo
4: [STRING] rld
5: [STRING] !
6: [STRING] 
7: [NUMBER] 1.0
8: [STRING] print

==== [[example.lua's locals]] ====

R[0]: tbl
R[1]: str
R[2]: (for index)
R[3]: (for limit)
R[4]: (for step)
R[5]: i

==== [[example.lua's dissassembly]] ====

[  0]   NEWTABLE :      0      6      0        ; 
[  1]      LOADK :   R[1]   K[0]               ; load "He" into R[1]
[  2]      LOADK :   R[2]   K[1]               ; load "llo" into R[2]
[  3]      LOADK :   R[3]   K[2]               ; load " " into R[3]
[  4]      LOADK :   R[4]   K[3]               ; load "Wo" into R[4]
[  5]      LOADK :   R[5]   K[4]               ; load "rld" into R[5]
[  6]      LOADK :   R[6]   K[5]               ; load "!" into R[6]
[  7]    SETLIST :      0      6      1        ; 
[  8]      LOADK :   R[1]   K[6]               ; load "" into R[1]
[  9]      LOADK :   R[2]   K[7]               ; load 1 into R[2]
[ 10]        LEN :      3      0      0        ; 
[ 11]      LOADK :   R[4]   K[7]               ; load 1 into R[4]
[ 12]    FORPREP :   R[2]      3               ; 
[ 13]       MOVE :      6      1      0        ; move R[1] into R[6]
[ 14]   GETTABLE :   R[7]      0   R[5]        ; 
[ 15]     CONCAT :      1      6      7        ; concat 2 values from R[6] to R[7], store into R[1]
[ 16]    FORLOOP :   R[2]     -4               ; 
[ 17]  GETGLOBAL :   R[2]   K[8]               ; move _G["print"] into R[2]
[ 18]       MOVE :      3      1      0        ; move R[1] into R[3]
[ 19]       CALL :      2      2      1        ; 
[ 20]     RETURN :      0      1      0        ; 

==== [[example.lua's pseudo-code]] ====

local tbl = {"He", "llo", " ", "Wo", "rld", "!", }
for i = 1, #tbl, 1 do
    local str = str .. tbl[i]
end
print(str)


```