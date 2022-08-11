# LuaDecompy

An experimental Lua 5.1 dump decompiler (typically dumped using `luac -o <out.luac> <script.lua>`).

## Example usage

```sh
> cat example.lua && luac5.1 -o example.luac example.lua
pp = "pri" .. "nt"

if 2 + 2 == 4 then
    _G[pp]("Hello world")
end

> python main.py example.luac
example.luac

==== [[example.lua's constants]] ====

0: [STRING] pp
1: [STRING] pri
2: [STRING] nt
3: [NUMBER] 4.0
4: [STRING] _G
5: [STRING] Hello world

==== [[example.lua's dissassembly]] ====

[  0]      LOADK :   R[0]   K[1]               ; load "pri" into R[0]
[  1]      LOADK :   R[1]   K[2]               ; load "nt" into R[1]
[  2]     CONCAT :   R[0]   R[0]   R[1]        ; concat 2 values from R[0] to R[1], store into R[0]
[  3]  SETGLOBAL :   R[0]   K[0]               ; 
[  4]         EQ :   R[0]   K[3]   K[3]        ; 
[  5]        JMP :   R[0]   R[5]               ; 
[  6]  GETGLOBAL :   R[0]   K[4]               ; 
[  7]  GETGLOBAL :   R[1]   K[0]               ; 
[  8]   GETTABLE :   R[0]   R[0]   R[1]        ; 
[  9]      LOADK :   R[1]   K[5]               ; load "Hello world" into R[1]
[ 10]       CALL :   R[0]   R[2]   R[1]        ; 
[ 11]     RETURN :   R[0]   R[1]   R[0]        ; 

==== [[example.lua's decompiled source]] ====


pp = "pri" .. "nt"
if 4.0 == 4.0 then 
    _G[pp]("Hello world")
end
```