# LuaDecompy

An experimental Lua 5.1 dump decompiler (typically dumped using `luac -o <out.luac> <script.lua>`).

You will quickly find that only **extremely** simple scripts are decompiled successfully right now. This is an experimental project and not all opcodes are properly handled for now. If you need a real decompiler I would recommend any of the handful of ones that exist already.

## Why?

Lua has a relatively small instruction set (only 38 different opcodes!). This makes it pretty feasible for a weekend decompiler project. (real) Decompilers are extremely complex pieces of software, so being able to write a simpler one helps show the theory without *much* of the headache.

## Example usage

```sh
> cat example.lua && luac5.1 -o example.luac example.lua
local total = 0

for i = 0, 9, 1 do
    total = total + i
    print(total)
end
> python main.py example.luac
example.luac

==== [[example.lua's constants]] ====

0: [NUMBER] 0.0
1: [NUMBER] 9.0
2: [NUMBER] 1.0
3: [STRING] print

==== [[example.lua's locals]] ====

R[0]: total
R[1]: (for index)
R[2]: (for limit)
R[3]: (for step)
R[4]: i

==== [[example.lua's dissassembly]] ====

[  0]      LOADK :   R[0]   K[0]               ; load 0.0 into R[0]
[  1]      LOADK :   R[1]   K[0]               ; load 0.0 into R[1]
[  2]      LOADK :   R[2]   K[1]               ; load 9.0 into R[2]
[  3]      LOADK :   R[3]   K[2]               ; load 1.0 into R[3]
[  4]    FORPREP :   R[1]      4               ; 
[  5]        ADD :   R[0]   R[0]   R[4]        ; add R[4] to R[0], place into R[0]
[  6]  GETGLOBAL :   R[5]   K[3]               ; move _G["print"] into R[5]
[  7]       MOVE :      6      0      0        ; move R[0] into R[6]
[  8]       CALL :      5      2      1        ; 
[  9]    FORLOOP :   R[1]     -5               ; 
[ 10]     RETURN :      0      1      0        ; 

==== [[example.lua's decompiled source]] ====

local total = 0.0
for i = 0.0, 9.0, 1.0 do
    total = (total + i)
    print(total)
end


```