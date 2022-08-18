# LuaDecompy

An experimental Lua 5.1 dump decompiler (typically dumped using `luac -o <out.luac> <script.lua>`).

You will quickly find that only **extremely** simple scripts are decompiled successfully right now. This is an experimental project and not all opcodes are properly handled for now. If you need a real decompiler I would recommend any of the handful of ones that exist already.

## Why?

Lua has a relatively small instruction set (only 38 different opcodes!). This makes it pretty feasible for a weekend decompiler project. (real) Decompilers are extremely complex pieces of software, so being able to write a simpler one helps show the theory without *much* of the headache.

## Example usage

```sh
> cat example.lua && luac5.1 -o example.luac example.lua
local printMsg = function(append)
    local tbl = {"He", "llo", " ", "Wo"}
    local str = ""

    for i = 1, #tbl do
        str = str .. tbl[i]
    end

    print(str .. append)
end

printMsg("rld!")
> python main.py example.luac
example.luac

==== [[example.lua's constants]] ====

0: [STRING] rld!

==== [[example.lua's locals]] ====

R[0]: printMsg

==== [[example.lua's dissassembly]] ====

[  0]    CLOSURE :   R[0]      0               ; 
[  1]       MOVE :      1      0      0        ; move R[0] into R[1]
[  2]      LOADK :   R[2]   K[0]               ; load "rld!" into R[2]
[  3]       CALL :      1      2      1        ; 
[  4]     RETURN :      0      1      0        ; 

==== [[example.lua's protos]] ====


==== [['s constants]] ====

0: [STRING] He
1: [STRING] llo
2: [STRING]  
3: [STRING] Wo
4: [STRING] 
5: [NUMBER] 1.0
6: [STRING] print

==== [['s locals]] ====

R[0]: append
R[1]: tbl
R[2]: str
R[3]: (for index)
R[4]: (for limit)
R[5]: (for step)
R[6]: i

==== [['s dissassembly]] ====

[  0]   NEWTABLE :      1      4      0        ; 
[  1]      LOADK :   R[2]   K[0]               ; load "He" into R[2]
[  2]      LOADK :   R[3]   K[1]               ; load "llo" into R[3]
[  3]      LOADK :   R[4]   K[2]               ; load " " into R[4]
[  4]      LOADK :   R[5]   K[3]               ; load "Wo" into R[5]
[  5]    SETLIST :      1      4      1        ; 
[  6]      LOADK :   R[2]   K[4]               ; load "" into R[2]
[  7]      LOADK :   R[3]   K[5]               ; load 1 into R[3]
[  8]        LEN :      4      1      0        ; 
[  9]      LOADK :   R[5]   K[5]               ; load 1 into R[5]
[ 10]    FORPREP :   R[3]      3               ; 
[ 11]       MOVE :      7      2      0        ; move R[2] into R[7]
[ 12]   GETTABLE :   R[8]      1   R[6]        ; 
[ 13]     CONCAT :      2      7      8        ; concat 2 values from R[7] to R[8], store into R[2]
[ 14]    FORLOOP :   R[3]     -4               ; 
[ 15]  GETGLOBAL :   R[3]   K[6]               ; move _G["print"] into R[3]
[ 16]       MOVE :      4      2      0        ; move R[2] into R[4]
[ 17]       MOVE :      5      0      0        ; move R[0] into R[5]
[ 18]     CONCAT :      4      4      5        ; concat 2 values from R[4] to R[5], store into R[4]
[ 19]       CALL :      3      2      1        ; 
[ 20]     RETURN :      0      1      0        ; 

==== [[example.lua's pseudo-code]] ====

local printMsg = function(append)
    local tbl = {"He", "llo", " ", "Wo", }
    local str = ""
    for i = 1, #tbl, 1 do
        str = str .. tbl[i]
    end
    print(str .. append)
end

printMsg("rld!")

```