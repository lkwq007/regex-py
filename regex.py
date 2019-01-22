# concat operation
class ConcatExp(object):
    def __init__(self, left, right):
        self.left = left
        self.right = right


# | operator
class AltExp(object):
    def __init__(self, left, right):
        self.left = left
        self.right = right


# * operator
class RepeatExp(object):
    def __init__(self, subExp):
        self.subExp = subExp


# ? operator
class OptionExp(object):
    def __init__(self, subExp):
        self.subExp = subExp


# functional used for CharExp
_isCh = lambda x: lambda y: x == y


# regex element, basic char
class CharExp(object):
    def __init__(self, isch):
        self.isch = isch


# + operator
def PlusExp(exp):
    return ConcatExp(exp, RepeatExp(exp))


# convert string to CharExp
def StrExp(_str, exp=None):
    if len(_str) > 0:
        if exp is None:
            return StrExp(_str[1:], CharExp(_isCh(_str[0])))
        else:
            return StrExp(_str[1:], ConcatExp(exp, CharExp(_isCh(_str[0]))))
    else:
        return exp


# abc -> ConcatExp(a,ConcatExp(b,c))
def ListConcatExp(lst, exp=None):
    if len(lst) > 0:
        if exp is None:
            return ListConcatExp(lst[1:], lst[0])
        else:
            return ListConcatExp(lst[1:], ConcatExp(exp, lst[0]))
    else:
        return exp


# a|b|c -> AltExp(a,AltExp(b,c))
def ListAltExp(lst, exp=None):
    if len(lst) > 0:
        if exp is None:
            return ListAltExp(lst[1:], lst[0])
        else:
            return ListAltExp(lst[1:], AltExp(exp, lst[0]))
    else:
        return exp


# conditional match
def MatchApply(exp, target, i, cont):
    if isinstance(exp, ConcatExp):
        return MatchApply(
            exp.left, target, i,
            lambda rest, ri: MatchApply(exp.right, rest, ri, cont)
        )
    elif isinstance(exp, AltExp):
        return MatchApply(exp.left, target, i, cont) \
               or MatchApply(exp.right, target, i, cont)
    elif isinstance(exp, RepeatExp):
        return MatchApply(
            exp.subExp, target, i,
            lambda rest, ri: (MatchApply(exp, rest, ri, cont) or cont(rest, ri))) \
               or cont(target, i)
    elif isinstance(exp, OptionExp):
        return MatchApply(exp.subExp, target, i, cont) \
               or cont(target, i)
    elif isinstance(exp, CharExp):
        return i < len(target) and exp.isch(target[i]) and cont(target, i + 1)
    else:
        raise Exception("Regular expression type error")


# problem: only match whole string
ReMatch = lambda regexp, target: MatchApply(regexp, target, 0, lambda rest, i: i >= len(rest))


class ReSearch(object):
    def __init__(self, regex, target):
        self.regex = regex
        self.target = target
        self.min_false = 0
        self.max_true = 0
        self.idx = 0

    def update_target(self, target):
        self.target = target

    def wrapper_(self, val, idx):
        if val:
            if idx > self.max_true:
                self.max_true = idx
        else:
            if idx < self.min_false:
                self.min_false = idx
        return val

    def apply_(self, exp, target, i, cont):
        if isinstance(exp, ConcatExp):
            return self.wrapper_(
                self.apply_(
                    exp.left, target, i,
                    lambda rest, ri: self.apply_(exp.right, rest, ri, cont))
                , i)
        elif isinstance(exp, AltExp):
            return self.wrapper_(
                self.apply_(exp.left, target, i, cont) or self.apply_(exp.right, target, i, cont)
                , i)
        elif isinstance(exp, RepeatExp):
            return self.wrapper_(
                self.apply_(
                    exp.subExp, target, i,
                    lambda rest, ri: (self.apply_(exp, rest, ri, cont) or cont(rest, ri))
                ) or cont(target, i)
                , i)
        elif isinstance(exp, OptionExp):
            return self.wrapper_(
                self.apply_(exp.subExp, target, i, cont) or cont(target, i)
                , i)
        elif isinstance(exp, CharExp):
            return self.wrapper_(i < len(target) and exp.isch(target[i]) and cont(target, i + 1), i)
        else:
            raise Exception("Regular expression type error")

    def idx_plus(self):
        self.idx += 1
        return True

    def search_(self):
        self.min_false = len(self.target)
        self.max_true = self.idx
        if self.apply_(self.regex, self.target, self.idx, lambda rest, ri: True):
            if self.max_true == self.idx:
                return self.idx < len(self.target) and self.idx_plus() and self.search_()
            else:
                return True
        else:
            return self.idx < len(self.target) and self.idx_plus() and self.search_()

    def search(self, all=False):
        self.idx = 0
        if all:
            ret = []
            while self.idx < len(self.target):
                if self.search_():
                    ret.append((self.idx, self.min_false))
                self.idx = self.min_false
            return ret
        else:
            if self.search_():
                return self.idx, self.min_false
            else:
                return -1, -1


# functionals that imitate PCRE regular expression
_d = lambda x: x.isdigit()
_D = lambda x: not _d(x)
_w = lambda x: x == "_" or x.isalnum()
_W = lambda x: not _w(x)
_l = lambda x: x.islower()
_u = lambda x: x.issuper()
_s = lambda x: x.isspace()
_S = lambda x: not _s(x)
_lst = lambda _str: lambda x: x in _str
_id = lambda x: x == "_" or x.isalpha()

# [-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?[flFL]?
# actually, this is a wrong pattern cuz it can match integer and it cannot match 1.
# the stricter pattern is shown below# however, we can test whether the token is integer at first, then apply this pattern to this pattern
_float_constant_loose = ListConcatExp([
    OptionExp(CharExp(_lst("+-"))),
    RepeatExp(CharExp(_d)),
    OptionExp(CharExp(_isCh("."))),
    PlusExp(CharExp(_d)),
    OptionExp(ListConcatExp(
        [
            CharExp(_lst("eE")),
            OptionExp(CharExp(_lst("+-"))),
            PlusExp(CharExp(_d))
        ]
    )),
    OptionExp(CharExp(_lst("flFL")))
])

# digit-sequence:
#     digit
#     digit-sequence digit
_digit = CharExp(_d)
_digit_sequence = PlusExp(_digit)
# sign: one of
#     + -
_sign = CharExp(_lst("+-"))
# floating-suffix: one of
#     f l F L
_float_suffix = CharExp(_lst("flFL"))
# exponent-part:
#     e sign_opt digit-sequence
#     E sign_opt digit-sequence
_exponent_part = ListConcatExp([
    CharExp(_lst("eE")),
    OptionExp(CharExp(_lst("+-"))),
    _digit_sequence
])
# fractional-constant:
#     digit-sequence_opt . digit-sequence
#     digit-sequence .
_fractional_constant = AltExp(
    ListConcatExp([
        OptionExp(_digit_sequence),
        StrExp("."),
        _digit_sequence
    ]),
    ConcatExp(_digit_sequence, StrExp("."))
)
# floating-point-constant:
#     fractional-constant exponent-part_opt floating-suffix_opt
#     digit-sequence exponent-part floating-suffix_opt
_float_constant = AltExp(
    ListConcatExp([
        _fractional_constant,
        OptionExp(_exponent_part),
        OptionExp(_float_suffix)
    ]),
    ListConcatExp([
        _digit_sequence,
        _exponent_part,
        OptionExp(_float_suffix)
    ])
)
# long-suffix: one of
#     l L
_long_suffix = CharExp(_lst("lL"))
# unsigned-suffix: one of
#     u U
_unsigned_suffix = CharExp(_lst("uU"))
# integer-suffix:
#     unsigned-suffix long-suffix_opt
#     long-suffix unsigned-suffix_opt
_integer_suffix = AltExp(
    ConcatExp(_unsigned_suffix, OptionExp(_long_suffix)),
    ConcatExp(_long_suffix, OptionExp(_unsigned_suffix))
)

# digit
_nonzero_digit = CharExp(lambda x: x != "0" and x.isdigit())
_oct_digit = CharExp(_lst("01234567"))
_hex_digit = CharExp(_lst("0123456789abcdefABCDEF"))
_bin_digit = CharExp(_lst("01"))
# numerical part
# decimal-constant:
#     nonzero-digit
#     decimal-constant digit
_decimal_constant = ConcatExp(_nonzero_digit, RepeatExp(_digit))
# binary-constant:
#     0b binary-digit
#     0B binary-digit
_binary_constant = ConcatExp(
    AltExp(StrExp("0b"), StrExp("0B")),
    PlusExp(_bin_digit)
)
# octal-constant:
#     0
#     octal-constant octal-digit
_octal_constant = ConcatExp(
    StrExp("0"),
    RepeatExp(_oct_digit)
)
# hexadecimal-constant:
#     0x hexadecimal-digit
#     0X hexadecimal-digit
#     hexadecimal-constant hexadecimal-digit
_hexadecimal_constant = ConcatExp(
    AltExp(StrExp("0x"), StrExp("0X")),
    PlusExp(_hex_digit)
)
# integer-constant:
#     decimal-constant integer-suffix_opt
#     binary-constant integer-suffix_opt
#     octal-constant integer-suffix_opt
#     hexadecimal-constant integer-suffix_opt
_integer_constant = ListConcatExp([
    OptionExp(_sign),
    ListAltExp([
        _decimal_constant,
        _binary_constant,
        _octal_constant,
        _hexadecimal_constant
    ]),
    OptionExp(_integer_suffix)
])
# cuz python int() needs a base, we split integer pattern as follows
_binary_integer_constant = ListConcatExp([
    OptionExp(_sign),
    _binary_constant,
    OptionExp(_integer_suffix)
])
_decimal_integer_constant = ListConcatExp([
    OptionExp(_sign),
    _decimal_constant,
    OptionExp(_integer_suffix)
])
_octal_integer_constant = ListConcatExp([
    OptionExp(_sign),
    _octal_constant,
    OptionExp(_integer_suffix)
])
_hexadecimal_integer_constant = ListConcatExp([
    OptionExp(_sign),
    _hexadecimal_constant,
    OptionExp(_integer_suffix)
])

_identifier = ConcatExp(
    CharExp(_id),
    RepeatExp(CharExp(_w))
)
