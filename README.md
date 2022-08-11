# LuaDecompy

An experimental Lua 5.1 bytecode decompiler.

## Example usage

```sh
❯ python main.py example.luac
example.luac

==== [[example.lua's constants]] ====

0: [STRING] pp
1: [STRING] pri
2: [STRING] nt
3: [NUMBER] 4.0
4: [STRING] _G
5: [STRING] Hello world

==== [[example.lua's dissassembly]] ====

[  0]      LOADK : R[0] K[1]
[  1]      LOADK : R[1] K[2]
[  2]     CONCAT : R[0] R[0] R[1]
[  3]  SETGLOBAL : R[0] R[0]
[  4]         EQ : R[0] K[3] K[3]
[  5]        JMP : R[0] R[12]
[  6]  GETGLOBAL : R[0] K[4]
[  7]  GETGLOBAL : R[1] K[0]
[  8]   GETTABLE : R[0] R[0] R[1]
[  9]      LOADK : R[1] K[5]
[ 10]       CALL : R[0] R[2] R[4]
[ 11]  GETGLOBAL : R[3] K[4]
[ 12]  GETGLOBAL : R[4] K[0]
[ 13]   GETTABLE : R[3] R[3] R[4]
[ 14]       MOVE : R[4] R[2] R[0]
[ 15]       MOVE : R[5] R[1] R[0]
[ 16]       MOVE : R[6] R[0] R[0]
[ 17]       CALL : R[3] R[4] R[1]
[ 18]     RETURN : R[0] R[1] R[0]

==== [[example.lua's decompiled source]] ====


pp = "pri" .. "nt"
if 4.0 == 4.0 then 
    local __unknLocal0, __unknLocal1, __unknLocal2 = _G[pp]("Hello world")
    _G[pp](__unknLocal2, __unknLocal1, __unknLocal0)
end


```