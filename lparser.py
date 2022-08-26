'''
    lparser.py

    Depends on lundump.py for lua dump deserialization.

    An experimental bytecode decompiler.
'''

from lundump import Chunk, Constant, Instruction, Opcodes, whichRK, readRKasK

class _Scope:
    def __init__(self, startPC: int, endPC: int):
        self.startPC = startPC
        self.endPC = endPC

class _Traceback:
    def __init__(self):
        self.sets = []
        self.uses = []
        self.isConst = False

class _Line:
    def __init__(self, startPC: int, endPC: int, src: str, scope: int):
        self.startPC = startPC
        self.endPC = endPC
        self.src = src
        self.scope = scope

def isValidLocal(ident: str) -> bool:
    # has to start with an alpha or _
    if ident[0] not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_":
        return False

    # then it can be alphanum or _
    for c in ident[1:]:
        if c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_":
            return False

    return True

class LuaDecomp:
    def __init__(self, chunk: Chunk, headChunk: bool = True, scopeOffset: int = 0):
        self.chunk = chunk
        self.pc = 0
        self.scope: list[_Scope] = []
        self.lines: list[_Line] = []
        self.top = {}
        self.locals = {}
        self.traceback = {}
        self.unknownLocalCount = 0
        self.headChunk = headChunk
        self.scopeOffset = scopeOffset # number of scopes this chunk/proto is in
        self.src: str = ""

        # configurations!
        self.aggressiveLocals = False # should *EVERY* set register be considered a local? 
        self.annotateLines = False
        self.indexWidth = 4 # how many spaces for indentions?

        self.__loadLocals()

        if not self.headChunk:
            functionProto = "function("

            # define params
            for i in range(self.chunk.numParams):
                # add param to function prototype (also make a local in the register if it doesn't exist)
                functionProto += ("%s, " if i+1 < self.chunk.numParams else "%s") % self.__makeLocalIdentifier(i)

                # mark local as defined
                self.__addSetTraceback(i)
            functionProto += ")"

            self.__startScope(functionProto, 0, len(self.chunk.instructions))

        # parse instructions
        while self.pc < len(self.chunk.instructions):
            self.parseInstr()
            self.pc += 1

            # end the scope (if we're supposed too)
            self.__checkScope()

        if not self.headChunk:
            self.__endScope()

    def getPseudoCode(self) -> str:
        fullSrc = ""

        for line in self.lines:
            if self.annotateLines:
                fullSrc += "-- PC: %d to PC: %d\n" % (line.startPC, line.endPC)
            fullSrc += ((' ' * self.indexWidth) * (line.scope + self.scopeOffset)) + line.src + "\n"

        return fullSrc

    # =======================================[[ Helpers ]]=========================================

    def __getInstrAtPC(self, pc: int) -> Instruction:
        if pc < len(self.chunk.instructions):
            return self.chunk.instructions[pc]

        raise Exception("Decompilation failed!")

    def __getNextInstr(self) -> Instruction:
        return self.__getInstrAtPC(self.pc + 1)

    def __getCurrInstr(self) -> Instruction:
        return self.__getInstrAtPC(self.pc)

    def __makeTracIfNotExist(self) -> None:
        if not self.pc in self.traceback:
            self.traceback[self.pc] = _Traceback()

    # when we read from a register, call this
    def __addUseTraceback(self, reg: int) -> None:
        self.__makeTracIfNotExist()
        self.traceback[self.pc].uses.append(reg)

    # when we write from a register, call this
    def __addSetTraceback(self, reg: int) -> None:
        self.__makeTracIfNotExist()
        self.traceback[self.pc].sets.append(reg)

    def __addExpr(self, code: str) -> None:
        self.src += code

    def __endStatement(self):
        startPC = self.lines[len(self.lines) - 1].endPC + 1 if len(self.lines) > 0 else 0
        endPC = self.pc

        # make sure we don't write an empty line
        if not self.src == "":
            self.lines.append(_Line(startPC, endPC, self.src, len(self.scope)))
        self.src = ""

    def __insertStatement(self, pc: int) -> None:
        # insert current statement into lines at pc location
        for i in range(len(self.lines)):
            if self.lines[i].startPC <= pc and self.lines[i].endPC >= pc:
                self.lines.insert(i, _Line(pc, pc, self.src, self.lines[i-1].scope if i > 0 else 0))
                self.src = ""
                return i

        self.src = ""

    # walks traceback, if local wasn't set before, the local needs to be defined
    def __needsDefined(self, reg) -> bool:
        for _, trace in self.traceback.items():
            if reg in trace.sets:
                return False

        # wasn't set in traceback! needs defined!
        return True

    def __loadLocals(self):
        for i in range(len(self.chunk.locals)):
            name = self.chunk.locals[i].name
            if isValidLocal(name):
                self.locals[i] = name
            elif "(for " not in name: # if it's a for loop register, ignore
                self.__makeLocalIdentifier(i)

    # when you *know* the register *has* to be a local (for loops, etc.)
    def __getLocal(self, indx: int) -> str:
        return self.locals[indx] if indx in self.locals else self.__makeLocalIdentifier(indx)

    def __getReg(self, indx: int) -> str:
        self.__addUseTraceback(indx)

        # if the top indx is a local, get it
        return self.locals[indx] if indx in self.locals else self.top[indx]

    def __setReg(self, indx: int, code: str, forceLocal: bool = False) -> None:
        # if the top indx is a local, set it
        if indx in self.locals:
            if self.__needsDefined(indx):
                self.__newLocal(indx, code)
            else:
                self.__addExpr(self.locals[indx] + " = " + code)
                self.__endStatement()
        elif self.aggressiveLocals or forceLocal: # 'every register is a local!!'
            self.__newLocal(indx, code)

        self.__addSetTraceback(indx)
        self.top[indx] = code

    # ========================================[[ Locals ]]=========================================

    def __makeLocalIdentifier(self, indx: int) -> str:
        # first, check if we have a local name already determined
        if indx in self.locals:
            return self.locals[indx]

        # otherwise, generate a local
        self.locals[indx] = "__unknLocal%d" % self.unknownLocalCount
        self.unknownLocalCount += 1

        return self.locals[indx]

    def __newLocal(self, indx: int, expr: str) -> None:
        self.__makeLocalIdentifier(indx)

        self.__addExpr("local " + self.locals[indx] + " = " + expr)
        self.__endStatement()

    # ========================================[[ Scopes ]]=========================================

    def __startScope(self, scopeType: str, start: int, size: int) -> None:
        self.__addExpr(scopeType)
        self.__endStatement()
        self.scope.append(_Scope(start, start + size))

    # checks if we need to end a scope
    def __checkScope(self) -> None:
        if len(self.scope) == 0:
            return

        if self.pc > self.scope[len(self.scope) - 1].endPC:
            self.__endScope()

    def __endScope(self) -> None:
        self.__endStatement()
        self.__addExpr("end")
        self.scope.pop()

        self.__endStatement()

    # =====================================[[ Instructions ]]======================================

    def __emitOperand(self, a: int, b: str, c: str, op: str) -> None:
        self.__setReg(a, "(" + b + op + c + ")")

    # handles conditional jumps
    def __condJmp(self, op: str, rkBC: bool = True):
        instr = self.__getCurrInstr()
        jmpType = "if"
        scopeStart = "then"

        # we need to check if the jmp location has a jump back (if so, it's a while loop)
        jmp = self.__getNextInstr().B + 1
        jmpToInstr = self.__getInstrAtPC(self.pc + jmp)

        if jmpToInstr.opcode == Opcodes.JMP:
            # if this jump jumps back to this compJmp, it's a loop!
            if self.pc + jmp + jmpToInstr.B <= self.pc + 1:
                jmpType = "while"
                scopeStart = "do"
        elif jmp < 0:
            # 'repeat until' loop (probably)
            jmpType = "until"
            scopeStart = None

        if instr.A > 0:
            self.__addExpr("%s not " % jmpType)
        else:
            self.__addExpr("%s " % jmpType)

        # write actual comparison
        if rkBC:
            self.__addExpr(self.__readRK(instr.B) + op + self.__readRK(instr.C) + " ")
        else: # just testing rkB
            self.__addExpr(op + self.__readRK(instr.B))

        self.pc += 1 # skip next instr
        if scopeStart:
            self.__startScope("%s " % scopeStart, self.pc - 1, jmp)

            # we end the statement *after* scopeStart
            self.__endStatement()
        else:
            # end the statement prior to repeat
            self.__endStatement()

            # it's a repeat until loop, insert 'repeat' at the jumpTo location
            self.__addExpr("repeat")
            insertedLine = self.__insertStatement(self.pc + jmp)

            # add scope to every line in-between
            for i in range(insertedLine+1, len(self.lines)-1):
                self.lines[i].scope += 1

    # 'RK's are special in because can be a register or a konstant. a bitflag is read to determine which
    def __readRK(self, rk: int) -> str:
        if (whichRK(rk)) > 0:
            return self.chunk.getConstant(readRKasK(rk)).toCode()
        else:
            return self.__getReg(rk)

    # walk & peak ahead NEWTABLE
    def __parseNewTable(self, indx: int):
        # TODO: parse SETTABLE too?
        tblOps = [Opcodes.LOADK, Opcodes.SETLIST]

        instr = self.__getNextInstr()
        cachedRegs = {}
        tbl = "{"
        while instr.opcode in tblOps:
            if instr.opcode == Opcodes.LOADK: # operate on registers
                cachedRegs[instr.A] = self.chunk.getConstant(instr.B).toCode()
            elif instr.opcode == Opcodes.SETLIST:
                numElems = instr.B

                for i in range(numElems):
                    tbl += "%s, " % cachedRegs[instr.A + i + 1]
                    del cachedRegs[instr.A + i + 1]

            self.pc += 1
            instr = self.__getNextInstr()
        tbl += "}"

        # i use forceLocal here even though i don't know *for sure* that the register is a local.
        # this does help later though if the table is reused (which is 99% of the time). the other 1%
        # only affects syntax and may look a little weird but is fine and equivalent non-the-less
        self.__setReg(indx, tbl, forceLocal=True)
        self.__endStatement()

        # if we have leftovers... oops, set those
        for i, v in cachedRegs.items():
            self.__setReg(i, v)

    def parseInstr(self):
        instr = self.__getCurrInstr()

        # python, add switch statements *please*
        if instr.opcode == Opcodes.MOVE: # move is a fake ABC instr, C is ignored
            # move registers
            self.__setReg(instr.A, self.__getReg(instr.B))
        elif instr.opcode == Opcodes.LOADK:
            self.__setReg(instr.A, self.chunk.getConstant(instr.B).toCode())
        elif instr.opcode == Opcodes.LOADBOOL:
            if instr.B == 0:
                self.__setReg(instr.A, "false")
            else:
                self.__setReg(instr.A, "true")
        elif instr.opcode == Opcodes.GETGLOBAL:
            self.__setReg(instr.A, self.chunk.getConstant(instr.B).data)
        elif instr.opcode == Opcodes.GETTABLE:
            self.__setReg(instr.A, self.__getReg(instr.B) + "[" + self.__readRK(instr.C) + "]")
        elif instr.opcode == Opcodes.SETGLOBAL:
            self.__addExpr(self.chunk.getConstant(instr.B).data + " = " + self.__getReg(instr.A))
            self.__endStatement()
        elif instr.opcode == Opcodes.SETTABLE:
            self.__addExpr(self.__getReg(instr.A) + "[" + self.__readRK(instr.B) + "] = " + self.__readRK(instr.C))
            self.__endStatement()
        elif instr.opcode == Opcodes.NEWTABLE:
            self.__parseNewTable(instr.A)
        elif instr.opcode == Opcodes.ADD:
            self.__emitOperand(instr.A, self.__readRK(instr.B), self.__readRK(instr.C), " + ")
        elif instr.opcode == Opcodes.SUB:
            self.__emitOperand(instr.A, self.__readRK(instr.B), self.__readRK(instr.C), " - ")
        elif instr.opcode == Opcodes.MUL:
            self.__emitOperand(instr.A, self.__readRK(instr.B), self.__readRK(instr.C), " * ")
        elif instr.opcode == Opcodes.DIV:
            self.__emitOperand(instr.A, self.__readRK(instr.B), self.__readRK(instr.C), " / ")
        elif instr.opcode == Opcodes.MOD:
            self.__emitOperand(instr.A, self.__readRK(instr.B), self.__readRK(instr.C), " % ")
        elif instr.opcode == Opcodes.POW:
            self.__emitOperand(instr.A, self.__readRK(instr.B), self.__readRK(instr.C), " ^ ")
        elif instr.opcode == Opcodes.UNM:
            self.__setReg(instr.A, "-" + self.__getReg(instr.B))
        elif instr.opcode == Opcodes.NOT:
            self.__setReg(instr.A, "not " + self.__getReg(instr.B))
        elif instr.opcode == Opcodes.LEN:
            self.__setReg(instr.A, "#" + self.__getReg(instr.B))
        elif instr.opcode == Opcodes.CONCAT:
            count = instr.C-instr.B+1
            concatStr = ""

            # concat all items on stack from RC to RB
            for i in range(count):
                concatStr += self.__getReg(instr.B + i) + (" .. " if not i == count - 1 else "")

            self.__setReg(instr.A, concatStr)
        elif instr.opcode == Opcodes.JMP:
            pass
        elif instr.opcode == Opcodes.EQ:
            self.__condJmp(" == ")
        elif instr.opcode == Opcodes.LT:
            self.__condJmp(" < ")
        elif instr.opcode == Opcodes.LE:
            self.__condJmp(" <= ")
        elif instr.opcode == Opcodes.TEST:
            if instr.C == 0:
                self.__condJmp("", False)
            else:
                self.__condJmp("not ", False)
        elif instr.opcode == Opcodes.CALL:
            preStr = ""
            callStr = ""
            ident = ""

            # parse arguments
            callStr += self.__getReg(instr.A) + "("
            for i in range(instr.A + 1, instr.A + instr.B):
                callStr += self.__getReg(i) + (", " if not i + 1 == instr.A + instr.B else "")
            callStr += ")"

            # parse return values
            if instr.C > 1:
                preStr = "local "
                for indx  in range(instr.A, instr.A + instr.C - 1):
                    if indx in self.locals:
                        ident = self.locals[indx]
                    else:
                        ident = self.__makeLocalIdentifier(indx)
                    preStr += ident

                    # normally setReg() does this
                    self.top[indx] = ident

                    # just so we don't have a trailing ', '
                    preStr += ", " if not indx == instr.A + instr.C - 2 else ""
                preStr += " = "

            self.__addExpr(preStr + callStr)
            self.__endStatement()
        elif instr.opcode == Opcodes.RETURN:
            self.__endStatement()
            pass # no-op for now
        elif instr.opcode == Opcodes.FORLOOP:
            pass # no-op for now
        elif instr.opcode == Opcodes.FORPREP:
            self.__addExpr("for %s = %s, %s, %s " % (self.__getLocal(instr.A+3), self.__getReg(instr.A), self.__getReg(instr.A + 1), self.__getReg(instr.A + 2)))
            self.__startScope("do", self.pc, instr.B)
        elif instr.opcode == Opcodes.SETLIST:
            # LFIELDS_PER_FLUSH (50) is the number of elements that *should* have been set in the list in the *last* SETLIST
            # eg.
            # [ 49]      LOADK :  R[49]   K[1]               ; load 0.0 into R[49]
            # [ 50]      LOADK :  R[50]   K[1]               ; load 0.0 into R[50]
            # [ 51]    SETLIST :      0     50      1        ; sets list[1..50]
            # [ 52]      LOADK :   R[1]   K[1]               ; load 0.0 into R[1]
            # [ 53]    SETLIST :      0      1      2        ; sets list[51..51]
            numElems = instr.B
            startAt = ((instr.C - 1) * 50)
            ident = self.__getLocal(instr.A)

            # set each index (TODO: make tables less verbose)
            for i in range(numElems):
                self.__addExpr("%s[%d] = %s" % (ident, (startAt + i + 1), self.__getReg(instr.A + i + 1)))
                self.__endStatement()
        elif instr.opcode == Opcodes.CLOSURE:
            proto = LuaDecomp(self.chunk.protos[instr.B], headChunk=False, scopeOffset=len(self.scope))
            self.__setReg(instr.A, proto.getPseudoCode())
        else:
            raise Exception("unsupported instruction: %s" % instr.toString())