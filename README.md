# LuaDecompy

An experimental Lua 5.1 dump decompiler (typically dumped using `luac -o <out.luac> <script.lua>`).

You will quickly find that only **extremely** simple scripts are decompiled successfully right now. This is an experimental project and not all opcodes are properly handled for now. If you need a real decompiler I would recommend any of the handful of ones that exist already.

## Why?

Lua has a relatively small instruction set (only 38 different opcodes!). This makes it pretty feasible for a weekend decompiler project. (real) Decompilers are extremely complex pieces of software, so being able to write a simpler one helps show the theory without *much* of the headache.

## Example usage

```sh
> cat example.lua && luac5.1 -o example.luac example.lua
local i, x = 0, 2

while i < 10 do
    print(i + x)
    i = i + 1
end
> python main.py example.luac
example.luac

==== [[example.lua's constants]] ====

0: [NUMBER] 0.0
1: [NUMBER] 2.0
2: [NUMBER] 10.0
3: [STRING] print
4: [NUMBER] 1.0

==== [[example.lua's dissassembly]] ====

[  0]      LOADK :   R[0]   K[0]               ; load 0.0 into R[0]
[  1]      LOADK :   R[1]   K[1]               ; load 2.0 into R[1]
[  2]         LT :   R[0]   R[0]   K[2]        ; 
[  3]        JMP :   R[0]      5               ; 
[  4]  GETGLOBAL :   R[2]   K[3]               ; 
[  5]        ADD :   R[3]   R[0]   R[1]        ; 
[  6]       CALL :   R[2]      2      1        ; 
[  7]        ADD :   R[0]   R[0]   K[4]        ; 
[  8]        JMP :   R[0]     -7               ; 
[  9]     RETURN :   R[0]      1      0        ; 

==== [[example.lua's decompiled source]] ====


local i = 0.0
local x = 2.0
while i < 10.0 do 
    print((i + x))
    i = (i + 1.0)
end

```