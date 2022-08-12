'''
    lparser.py

    Depends on lundump.py for lua dump deserialization.

    An experimental bytecode decompiler.
'''

from operator import concat
from subprocess import call
from xmlrpc.client import Boolean
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

class LuaDecomp:
    def __init__(self, chunk: Chunk):
        self.chunk = chunk
        self.pc = 0
        self.scope = []
        self.top = {}
        self.locals = {}
        self.traceback = {}
        self.unknownLocalCount = 0
        self.src: str = ""

        # configurations!
        self.aggressiveLocals = False # should *EVERY* set register be considered a local? 
        self.indexWidth = 4 # how many spaces for indentions?

        self.__loadLocals()

        # parse instructions
        while self.pc < len(self.chunk.instructions):
            self.parseInstr()
            self.pc += 1

            # end the scope (if we're supposed too)
            self.__checkScope()

        print("\n==== [[" + str(self.chunk.name) + "'s decompiled source]] ====\n")
        print(self.src)

    # =======================================[[ Helpers ]]=========================================

    def __getInstrAtPC(self, pc: int) -> Instruction:
        if pc < len(self.chunk.instructions):
            return self.chunk.instructions[pc]

        raise Exception("Decompilation failed!")

    def __getNextInstr(self) -> Instruction:
        return self.__getInstrAtPC(self.pc + 1)

    def __getCurrInstr(self) -> Instruction:
        return self.__getInstrAtPC(self.pc)

    # when we read from a register, call this
    def __addUseTraceback(self, reg: int) -> None:
        if not self.pc in self.traceback:
            self.traceback[self.pc] = _Traceback()

        self.traceback[self.pc].uses.append(reg)

    # when we write from a register, call this
    def __addSetTraceback(self, reg: int) -> None:
        if not self.pc in self.traceback:
            self.traceback[self.pc] = _Traceback()

        self.traceback[self.pc].sets.append(reg)

    # walks traceback, if local wasn't set before, the local needs to be defined
    def __needsDefined(self, reg) -> Boolean:
        for _, trace in self.traceback.items():
            if reg in trace.sets:
                return False

        # wasn't set in traceback! needs defined!
        return True

    def __loadLocals(self):
        for i in range(len(self.chunk.locals)):
            if not self.chunk.locals[i].name == "":
                self.locals[i] = self.chunk.locals[i].name 
            else:
                self.__makeLocalIdentifier(i)

    def __addExpr(self, code: str) -> None:
        self.src += code

    def __startStatement(self):
        self.src += '\n' + (' ' * self.indexWidth * len(self.scope))

    def __getReg(self, indx: int) -> str:
        self.__addUseTraceback(indx)

        # if the top indx is a local, get it
        return self.locals[indx] if indx in self.locals else self.top[indx]

    def __setReg(self, indx: int, code: str) -> None:
        # if the top indx is a local, set it
        if indx in self.locals:
            if self.__needsDefined(indx):
                self.__newLocal(indx, code)
            else:
                self.__startStatement()
                self.__addExpr(self.locals[indx] + " = " + code)
        elif self.aggressiveLocals: # 'every register is a local!!'
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
        # TODO: grab identifier from chunk(?)
        self.__makeLocalIdentifier(indx)

        self.__startStatement()
        self.__addExpr("local " + self.locals[indx] + " = " + expr)

    # ========================================[[ Scopes ]]=========================================

    def __startScope(self, scopeType: str, size: int) -> None:
        self.__addExpr(scopeType)
        self.scope.append(_Scope(self.pc, self.pc + size))

    # checks if we need to end a scope
    def __checkScope(self) -> None:
        if len(self.scope) == 0:
            return

        if self.pc > self.scope[len(self.scope) - 1].endPC:
            self.__endScope()

    def __endScope(self) -> None:
        self.scope.pop()
        self.__startStatement()
        self.__addExpr("end")

    # =====================================[[ Instructions ]]======================================

    def __emitOperand(self, a: int, b: str, c: str, op: str) -> None:
        self.__setReg(a, "(" + b + op + c + ")")

    def __compJmp(self, op: str):
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

        self.__startStatement()
        if instr.A > 0:
            self.__addExpr("%s not " % jmpType)
        else:
            self.__addExpr("%s " % jmpType)
        self.__addExpr(self.__readRK(instr.B) + op + self.__readRK(instr.C) + " ")
        self.__startScope("%s " % scopeStart, jmp)
        self.pc += 1 # skip next instr

    # 'RK's are special in because can be a register or a konstant. a bitflag is read to determine which
    def __readRK(self, rk: int) -> str:
        if (whichRK(rk)) > 0:
            return self.chunk.getConstant(readRKasK(rk)).toCode()
        else:
            return self.__getReg(rk)

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
            self.__startStatement()
            self.__addExpr(self.chunk.getConstant(instr.B).data + " = " + self.__getReg(instr.A))
        elif instr.opcode == Opcodes.SETTABLE:
            self.__startStatement()
            self.__addExpr(self.__getReg(instr.A) + "[" + self.__readRK(instr.B) + "] = " + self.__readRK(instr.C))
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
            self.__setReg(instr.A, "!" + self.__getReg(instr.B))
        elif instr.opcode == Opcodes.LEN:
            self.__setReg(instr.A, "#" + self.__getCurrInstr(instr.B))
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
            self.__compJmp(" == ")
        elif instr.opcode == Opcodes.LT:
            self.__compJmp(" < ")
        elif instr.opcode == Opcodes.LE:
            self.__compJmp(" <= ")
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

            self.__startStatement()
            self.__addExpr(preStr + callStr)
        elif instr.opcode == Opcodes.RETURN:
            self.__startStatement()
            pass # no-op for now
        else:
            raise Exception("unsupported instruction: %s" % instr.toString())