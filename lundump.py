'''
    l(un)dump.py

    A Lua5.1 cross-platform bytecode deserializer. This module pulls int and size_t sizes from the
    chunk header, meaning it should be able to deserialize lua bytecode dumps from most platforms,
    regardless of the host machine.

    For details on the Lua5.1 bytecode format, I read [this PDF](https://archive.org/download/a-no-frills-intro-to-lua-5.1-vm-instructions/a-no-frills-intro-to-lua-5.1-vm-instructions_archive.torrent)
    as well as read the lundump.c source file from the Lua5.1 source.
'''

from multiprocessing.spawn import get_executable
import struct
import array
from enum import IntEnum, Enum, auto
from typing_extensions import Self

class InstructionType(Enum):
    ABC = auto(),
    ABx = auto(),
    AsBx = auto()

class Opcodes(IntEnum):
    MOVE        = 0,
    LOADK       = 1,
    LOADBOOL    = 2,
    LOADNIL     = 3,
    GETUPVAL    = 4,
    GETGLOBAL   = 5,
    GETTABLE    = 6,
    SETGLOBAL   = 7,
    SETUPVAL    = 8,
    SETTABLE    = 9,
    NEWTABLE    = 10,
    SELF        = 11,
    ADD         = 12,
    SUB         = 13,
    MUL         = 14,
    DIV         = 15,
    MOD         = 16,
    POW         = 17,
    UNM         = 18,
    NOT         = 19,
    LEN         = 20,
    CONCAT      = 21,
    JMP         = 22,
    EQ          = 23,
    LT          = 24,
    LE          = 25,
    TEST        = 26,
    TESTSET     = 27,
    CALL        = 28,
    TAILCALL    = 29,
    RETURN      = 30,
    FORLOOP     = 31,
    FORPREP     = 32,
    TFORLOOP    = 33,
    SETLIST     = 34,
    CLOSE       = 35,
    CLOSURE     = 36,
    VARARG      = 37

class ConstType(IntEnum):
    NIL     = 0,
    BOOL    = 1,
    NUMBER  = 3,
    STRING  = 4,

_RKBCInstr = [Opcodes.SETTABLE, Opcodes.ADD, Opcodes.SUB, Opcodes.MUL, Opcodes.DIV, Opcodes.MOD, Opcodes.POW, Opcodes.EQ, Opcodes.LT]
_RKCInstr = [Opcodes.GETTABLE, Opcodes.SELF]
_KBx = [Opcodes.LOADK, Opcodes.GETGLOBAL]

class Instruction:
    def __init__(self, type: InstructionType, name: str) -> None:
        self.type = type
        self.name = name
        self.opcode: int = None
        self.A: int = None
        self.B: int = None
        self.C: int = None

    # 'RK's are special in because can be a register or a konstant. a bitflag is read to determine which
    def __readRK(self, rk: int) -> str:
        if (rk & (1 << 8)) > 0:
            return "K[" + str((rk & ~(1 << 8))) + "]"
        else:
            return "R[" + str(rk) + "]"

    def toString(self):
        instr = "%10s" % self.name
        regs = ""

        if self.type == InstructionType.ABC:
            # by default, treat them as registers
            A = "R[%d]" % self.A
            B = "R[%d]" % self.B
            C = "R[%d]" % self.C

            # these opcodes have RKs for B & C
            if self.opcode in _RKBCInstr:
                B = self.__readRK(self.B)
                C = self.__readRK(self.C)
            elif self.opcode in _RKCInstr: # just for C
                C = self.__readRK(self.C)

            regs = "%s %s %s" % (A, B, C) 
        elif self.type == InstructionType.ABx or self.type == InstructionType.AsBx:
            A = "R[%d]" % self.A
            B = "R[%d]" % self.B

            if self.opcode in _KBx:
                B = "K[%d]" % self.B

            regs = "%s %s" % (A, B)

        return "%s : %s" % (instr, regs)

class Constant:
    def __init__(self, type: ConstType, data) -> None:
        self.type = type
        self.data = data

    def toString(self):
        return "[" + self.type.name + "] " + str(self.data)

    # format the constant so that it is parsable by lua
    def toCode(self):
        if self.type == ConstType.STRING:
            return "\"" + self.data + "\""
        elif self.type == ConstType.BOOL:
            if self.data:
                return "true"
            else:
                return "false"
        elif self.type == ConstType.NUMBER:
            return str(self.data)
        else:
            return "nil"

class Local:
    def __init__(self, name: str, start: int, end: int):
        self.name = name
        self.start = start
        self.end = end

class Chunk:
    def __init__(self) -> None:
        self.constants: list[Constant] = []
        self.instructions: list[Instruction] = []
        self.protos: list[Chunk] = []

        self.name: str = "Unnamed proto"
        self.frst_line: int = 0
        self.last_line: int = 0
        self.numUpvals: int = 0
        self.numParams: int = 0
        self.isVarg: bool = False
        self.maxStack: int = 0

        self.upvalues: list[str] = []
        self.locals: list[Local] = []

    def appendInstruction(self, instr: Instruction):
        self.instructions.append(instr)

    def appendConstant(self, const: Constant):
        self.constants.append(const)

    def appendProto(self, proto):
        self.protos.append(proto)

    def appendLocal(self, local: Local):
        self.locals.append(local)

    def findLocal(self, pc: int) -> Local:
        for l in self.locals:
            if l.start <= pc and l.end >= pc:
                return l

        # there's no local information (may have been stripped)
        return None

    def print(self):
        print("\n==== [[" + str(self.name) + "'s constants]] ====\n")
        for z in range(len(self.constants)):
            i = self.constants[z]
            print(str(z) + ": " + i.toString())

        print("\n==== [[" + str(self.name) + "'s dissassembly]] ====\n")
        for i in range(len(self.instructions)):
            print("[%3d] %s" % (i, self.instructions[i].toString()))

        if len(self.protos) > 0:
            print("\n==== [[" + str(self.name) + "'s protos]] ====\n")
            for z in self.protos:
                z.print()

instr_lookup_tbl = [
    Instruction(InstructionType.ABC, "MOVE"),  Instruction(InstructionType.ABx, "LOADK"), Instruction(InstructionType.ABC, "LOADBOOL"),
    Instruction(InstructionType.ABC, "LOADNIL"), Instruction(InstructionType.ABC, "GETUPVAL"), Instruction(InstructionType.ABx, "GETGLOBAL"),
    Instruction(InstructionType.ABC, "GETTABLE"), Instruction(InstructionType.ABx, "SETGLOBAL"), Instruction(InstructionType.ABC, "SETUPVAL"),
    Instruction(InstructionType.ABC, "SETTABLE"), Instruction(InstructionType.ABC, "NEWTABLE"), Instruction(InstructionType.ABC, "SELF"),
    Instruction(InstructionType.ABC, "ADD"), Instruction(InstructionType.ABC, "SUB"), Instruction(InstructionType.ABC, "MUL"),
    Instruction(InstructionType.ABC, "DIV"), Instruction(InstructionType.ABC, "MOD"), Instruction(InstructionType.ABC, "POW"),
    Instruction(InstructionType.ABC, "UNM"), Instruction(InstructionType.ABC, "NOT"), Instruction(InstructionType.ABC, "LEN"),
    Instruction(InstructionType.ABC, "CONCAT"), Instruction(InstructionType.AsBx, "JMP"), Instruction(InstructionType.ABC, "EQ"),
    Instruction(InstructionType.ABC, "LT"), Instruction(InstructionType.ABC, "LE"), Instruction(InstructionType.ABC, "TEST"),
    Instruction(InstructionType.ABC, "TESTSET"), Instruction(InstructionType.ABC, "CALL"), Instruction(InstructionType.ABC, "TAILCALL"),
    Instruction(InstructionType.ABC, "RETURN"), Instruction(InstructionType.AsBx, "FORLOOP"), Instruction(InstructionType.AsBx, "FORPREP"),
    Instruction(InstructionType.ABC, "TFORLOOP"), Instruction(InstructionType.ABC, "SETLIST"), Instruction(InstructionType.ABC, "CLOSE"),
    Instruction(InstructionType.ABx, "CLOSURE"), Instruction(InstructionType.ABC, "VARARG")
]

# at [p]osition, with [s]ize of bits
def get_bits(num: int, p: int, s: int):
    return (num>>p) & (~((~0)<<s))

# set bits from data to num at [p]osition, with [s]ize of bits
def set_bits(num, data, p, s) -> int:
    return (num & (~((~((~0)<<s))<<p))) | ((data << p) & ((~((~0)<<s))<<p))

def _decode_instr(data: int) -> Instruction:
    opcode = get_bits(data, 0, 6)
    template = instr_lookup_tbl[opcode]
    instr = Instruction(template.type, template.name)

    # i read the lopcodes.h file to get these bit position and sizes.
    instr.opcode = opcode
    instr.A = get_bits(data, 6, 8) # starts after POS_OP + SIZE_OP (6), with a size of 8

    if instr.type == InstructionType.ABC:
        instr.B = get_bits(data, 23, 9) # starts after POS_C + SIZE_C (23), with a size of 9
        instr.C = get_bits(data, 14, 9) # starts after POS_A + SIZE_A (14), with a size of 9
    elif instr.type == InstructionType.ABx:
        instr.B = get_bits(data, 14, 18) # starts after POS_A + SIZE_A (14), with a size of 18
    elif instr.type == InstructionType.AsBx:
        instr.B = get_bits(data, 14, 18) - 131071 # Bx is now signed, so just sub half of the MAX_UINT for 18 bits

    return instr

# returns a u32 instruction
def _encode_instr(instr: Instruction) -> int:
    data = 0

    # encode instruction (basically, do the inverse of _decode_instr)
    data = set_bits(data, instr.opcode, 0, 6)
    data = set_bits(data, instr.A, 6, 8)

    if instr.type == InstructionType.ABC:
        data = set_bits(data, instr.B, 23, 9)
        data = set_bits(data, instr.C, 14, 9)
    elif instr.type == InstructionType.ABx:
        data = set_bits(data, instr.B, 14, 18)
    elif instr.type == InstructionType.AsBx:
        data = set_bits(data, instr.B + 131071, 14, 18)

    return data

class LuaUndump:
    def __init__(self):
        self.rootChunk: Chunk = None
        self.index = 0

    @staticmethod
    def dis_chunk(chunk: Chunk):
        chunk.print()
    
    def loadBlock(self, sz) -> bytearray:
        if self.index + sz > len(self.bytecode):
            raise Exception("Malformed bytecode!")

        temp = bytearray(self.bytecode[self.index:self.index+sz])
        self.index = self.index + sz
        return temp

    def get_byte(self) -> int:
        return self.loadBlock(1)[0]

    def get_int32(self) -> int:
        if (self.big_endian):
            return int.from_bytes(self.loadBlock(4), byteorder='big', signed=False)
        else:
            return int.from_bytes(self.loadBlock(4), byteorder='little', signed=False)

    def get_int(self) -> int:
        if (self.big_endian):
            return int.from_bytes(self.loadBlock(self.int_size), byteorder='big', signed=False)
        else:
            return int.from_bytes(self.loadBlock(self.int_size), byteorder='little', signed=False)

    def get_size_t(self) -> int:
        if (self.big_endian):
            return int.from_bytes(self.loadBlock(self.size_t), byteorder='big', signed=False)
        else:
            return int.from_bytes(self.loadBlock(self.size_t), byteorder='little', signed=False)

    def get_double(self) -> int:
        if self.big_endian:
            return struct.unpack('>d', self.loadBlock(8))[0]
        else:
            return struct.unpack('<d', self.loadBlock(8))[0]

    def get_string(self, size) -> str:
        if (size == None):
            size = self.get_size_t()
            if (size == 0):
                return ""

        return "".join(chr(x) for x in self.loadBlock(size))

    def decode_chunk(self) -> Chunk:
        chunk = Chunk()

        chunk.name = self.get_string(None)
        chunk.frst_line = self.get_int()
        chunk.last_line = self.get_int()

        chunk.numUpvals = self.get_byte()
        chunk.numParams = self.get_byte()
        chunk.isVarg = (self.get_byte() != 0)
        chunk.maxStack = self.get_byte()

        if (not chunk.name == ""):
            chunk.name = chunk.name[1:-1]

        # parse instructions
        num = self.get_int()
        for i in range(num):
            chunk.appendInstruction(_decode_instr(self.get_int32()))

        # get constants
        num = self.get_int()
        for i in range(num):
            constant: Constant = None
            type = self.get_byte()

            if type == 0: #nil
                constant = Constant(ConstType.NIL, None)
            elif type == 1: # bool
                constant = Constant(ConstType.BOOL, (self.get_byte() != 0))
            elif type == 3: # number
                constant = Constant(ConstType.NUMBER, self.get_double())
            elif type == 4: # string
                constant = Constant(ConstType.STRING, self.get_string(None)[:-1])
            else:
                raise Exception("Unknown Datatype! [%d]" % type)

            chunk.appendConstant(constant)

        # parse protos
        num = self.get_int()
        for i in range(num):
            chunk.appendProto(self.decode_chunk())

        # debug stuff, maybe i'll add this to chunks to have better disassembly annotation in the future?
        # eh, for now just consume the bytes.

        # line numbers
        num = self.get_int()
        for i in range(num):
            self.get_int()

        # locals
        num = self.get_int()
        for i in range(num):
            name = self.get_string(None) # local name
            start = self.get_int() # local start PC
            end = self.get_int() # local end PC
            chunk.appendLocal(Local(name, start, end))

        # upvalues
        num = self.get_int()
        for i in range(num):
            self.get_string(None) # upvalue name

        return chunk

    def decode_rawbytecode(self, rawbytecode):
        # bytecode sanity checks
        if not rawbytecode[0:4] == b'\x1bLua':
            raise Exception("Lua Bytecode expected!")

        bytecode = array.array('b', rawbytecode)
        return self.decode_bytecode(bytecode)

    def decode_bytecode(self, bytecode):
        self.bytecode   = bytecode

        # aligns index, skips header
        self.index = 4
        
        self.vm_version = self.get_byte()
        self.bytecode_format = self.get_byte()
        self.big_endian = (self.get_byte() == 0)
        self.int_size   = self.get_byte()
        self.size_t     = self.get_byte()
        self.instr_size = self.get_byte() # gets size of instructions
        self.l_number_size = self.get_byte() # size of lua_Number
        self.integral_flag = self.get_byte()

        self.rootChunk = self.decode_chunk()
        return self.rootChunk
        
    def loadFile(self, luaCFile):
        with open(luaCFile, 'rb') as luac_file:
            bytecode = luac_file.read()
            return self.decode_rawbytecode(bytecode)

    def print_dissassembly(self):
        LuaUndump.dis_chunk(self.rootChunk)

