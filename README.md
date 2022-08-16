# LuaDecompy

An experimental Lua 5.1 dump decompiler (typically dumped using `luac -o <out.luac> <script.lua>`).

You will quickly find that only **extremely** simple scripts are decompiled successfully right now. This is an experimental project and not all opcodes are properly handled for now. If you need a real decompiler I would recommend any of the handful of ones that exist already.

## Why?

Lua has a relatively small instruction set (only 38 different opcodes!). This makes it pretty feasible for a weekend decompiler project. (real) Decompilers are extremely complex pieces of software, so being able to write a simpler one helps show the theory without *much* of the headache.

## Example usage

```sh
> cat example.lua && luac5.1 -o example.luac example.lua
local tbl = {"Hello", "World"}

print(tbl[1] .. " " .. tbl[2] .. ": " .. 2.5)
> python main.py example.luac
example.luac

==== [[example.lua's constants]] ====

0: [STRING] Hello
1: [STRING] World
2: [STRING] print
3: [NUMBER] 1.0
4: [STRING]  
5: [NUMBER] 2.0
6: [STRING] : 
7: [NUMBER] 2.5

==== [[example.lua's locals]] ====

R[0]: tbl

==== [[example.lua's dissassembly]] ====

[  0]   NEWTABLE :      0      2      0        ; 
[  1]      LOADK :   R[1]   K[0]               ; load "Hello" into R[1]
[  2]      LOADK :   R[2]   K[1]               ; load "World" into R[2]
[  3]    SETLIST :      0      2      1        ; 
[  4]  GETGLOBAL :   R[1]   K[2]               ; move _G["print"] into R[1]
[  5]   GETTABLE :   R[2]      0   K[3]        ; 
[  6]      LOADK :   R[3]   K[4]               ; load " " into R[3]
[  7]   GETTABLE :   R[4]      0   K[5]        ; 
[  8]      LOADK :   R[5]   K[6]               ; load ": " into R[5]
[  9]      LOADK :   R[6]   K[7]               ; load 2.5 into R[6]
[ 10]     CONCAT :      2      2      6        ; concat 5 values from R[2] to R[6], store into R[2]
[ 11]       CALL :      1      2      1        ; 
[ 12]     RETURN :      0      1      0        ; 

==== [[example.lua's pseudo-code]] ====

local tbl = {}
tbl[1] = "Hello"
tbl[2] = "World"
print(tbl[1] .. " " .. tbl[2] .. ": " .. 2.5)

```