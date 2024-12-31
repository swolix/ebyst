# Copyright (c) 2024 Sijmen Woutersen
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import logging
import pyparsing as pp

logger = logging.getLogger(__name__)

class StaplFile:
    """STAPL parser"""

    @classmethod
    def parse(cls, f):
        comments = "`" + pp.SkipTo(pp.LineEnd())
        proc_instruction = pp.Forward()
        expression = pp.Forward()

        identifier = pp.Word(init_chars=pp.srange("[a-zA-Z]"), body_chars=pp.srange("[a-zA-Z0-9_]"))
        literal = pp.Combine(pp.Or((pp.pyparsing_common.integer,
                                    pp.Literal("#") + pp.Word(pp.srange("[01]")),
                                    pp.Literal("$") + pp.Word(pp.srange("[0-9a-fA-F]"))))) # TODO ACA
        variable = pp.Combine(identifier + pp.Opt(pp.Literal("[") + expression + pp.Literal("]")))
        
        expression0 = identifier | literal | pp.Group(pp.Suppress(pp.Literal("(")) + expression + pp.Suppress(pp.Literal(")")))
        expression1 = pp.Group(expression0 + pp.Opt(pp.Literal("[") + expression + pp.Opt(pp.Literal("..") + expression) + pp.Literal("]")))
        expression2 = pp.Group(pp.Optional(pp.one_of("- ! ~")) + expression1)
        expression3 = pp.Group(expression2 + pp.ZeroOrMore(pp.one_of("* / %") + expression2))
        expression4 = pp.Group(expression3 + pp.ZeroOrMore(pp.one_of("+ -") + expression3))
        expression5 = pp.Group(expression4 + pp.ZeroOrMore(pp.one_of("<< >>") + expression4))
        expression6 = pp.Group(expression5 + pp.ZeroOrMore(pp.one_of("<= >= < >") + expression5))
        expression7 = pp.Group(expression6 + pp.ZeroOrMore(pp.one_of("== !=") + expression6))
        expression8 = pp.Group(expression7 + pp.ZeroOrMore(pp.Literal("&") + expression7))
        expression9 = pp.Group(expression8 + pp.ZeroOrMore(pp.Literal("^") + expression8))
        expression10 = pp.Group(expression9 + pp.ZeroOrMore(pp.Literal("|") + expression9))
        expression11 = pp.Group(expression10 + pp.ZeroOrMore(pp.Literal("&&") + expression10))
        expression12 = pp.Group(expression11 + pp.ZeroOrMore(pp.Literal("||") + expression11))
        expression <<= expression12

        str_expression = pp.Or((pp.QuotedString("\""))) # TODO

        action = pp.Group(pp.CaselessKeyword("ACTION") - identifier - pp.Opt(pp.QuotedString("\"")) -
                          pp.Suppress(pp.Literal("=")) - identifier -
                          pp.Opt(pp.Or((pp.CaselessKeyword("OPTIONAL"), pp.CaselessKeyword("RECOMMENDED")))) -
                          pp.ZeroOrMore(pp.Literal(",") - identifier - pp.Opt(pp.Or((pp.CaselessKeyword("OPTIONAL"),
                                                                                     pp.CaselessKeyword("RECOMMENDED"))))) -
                          pp.Suppress(pp.Literal(";")))
        assignment = expression + pp.Literal("=") + expression + pp.Suppress(pp.Literal(";"))
        boolean = pp.Group(pp.CaselessKeyword("BOOLEAN") - variable -
                           pp.Opt(pp.Suppress(pp.Literal("=")) - expression) - pp.Suppress(pp.Literal(";")))
        call = pp.Group(pp.CaselessKeyword("CALL") - identifier - pp.Suppress(pp.Literal(";")))
        crc = pp.Group(pp.CaselessKeyword("CRC") - pp.Word(pp.srange("[0-9a-fA-F]")) - pp.Suppress(pp.Literal(";")))
        drscan = pp.Group(pp.CaselessKeyword("DRSCAN") - expression - pp.Suppress(pp.Literal(",")) - expression -
                          pp.Opt(pp.Suppress(pp.Literal(",")) - pp.CaselessKeyword("CAPTURE") - expression) -
                          pp.Opt(pp.Suppress(pp.Literal(",")) - pp.CaselessKeyword("COMPARE") - expression -
                                 pp.Suppress(pp.Literal(",")) - expression + pp.Suppress(pp.Literal(",")) - expression) -
                          pp.Suppress(pp.Literal(";")))
        drstop = pp.Group(pp.CaselessKeyword("DRSTOP") - identifier - pp.Suppress(pp.Literal(";")))
        exit = pp.Group(pp.CaselessKeyword("EXIT") - expression - pp.Suppress(pp.Literal(";")))
        export = pp.Group(pp.CaselessKeyword("EXPORT") - pp.QuotedString("\"") - pp.Suppress(pp.Literal(",")) -
                          expression - pp.Suppress(pp.Literal(";")))
        for_ = pp.Forward()
        goto = pp.Group(pp.CaselessKeyword("GOTO") - identifier - pp.Suppress(pp.Literal(";")))
        if_ = pp.Group(pp.CaselessKeyword("IF") - expression - pp.CaselessKeyword("THEN") - proc_instruction)
        integer = pp.Group(pp.CaselessKeyword("INTEGER") - variable -
                           pp.Opt(pp.Suppress(pp.Literal("=")) - expression - pp.Opt(pp.ZeroOrMore(pp.Literal(",") - expression))) -
                           pp.Suppress(pp.Literal(";")))
        irscan = pp.Group(pp.CaselessKeyword("IRSCAN") - expression + pp.Suppress(pp.Literal(",")) - expression -
                          pp.Opt(pp.Suppress(pp.Literal(",")) - pp.CaselessKeyword("CAPTURE") - expression) -
                          pp.Opt(pp.Suppress(pp.Literal(",")) - pp.CaselessKeyword("COMPARE") - expression -
                                 pp.Suppress(pp.Literal(",")) - expression - pp.Suppress(pp.Literal(",")) - expression) -
                          pp.Suppress(pp.Literal(";")))
        irstop = pp.Group(pp.CaselessKeyword("IRSTOP") - identifier - pp.Suppress(pp.Literal(";")))
        note = pp.Group(pp.CaselessKeyword("NOTE") - pp.QuotedString("\"") - pp.QuotedString("\"") - pp.Suppress(pp.Literal(";")))
        pop = pp.Group((pp.CaselessKeyword("POP") - variable - pp.Suppress(pp.Literal(";"))))
        # postdr = pp.Group((pp.CaselessKeyword("POSTDR") - pp.Suppress(pp.Literal(";")))) # TODO
        # postir = pp.Group(pp.CaselessKeyword("POSTIR") - pp.Suppress(pp.Literal(";"))) # TODO
        # predr = pp.Group(pp.CaselessKeyword("PREDR") - pp.Suppress(pp.Literal(";"))) # TODO
        # preir = pp.Group(pp.CaselessKeyword("PREIR") - pp.Suppress(pp.Literal(";"))) # TODO
        print = pp.Group(pp.CaselessKeyword("PRINT") - str_expression -
                         pp.ZeroOrMore(pp.Suppress(pp.Literal(",")) - str_expression) - pp.Suppress(pp.Literal(";")))
        push = pp.Group(pp.CaselessKeyword("PUSH") - expression - pp.Suppress(pp.Literal(";")))
        state = pp.Group(pp.CaselessKeyword("STATE") - pp.OneOrMore(identifier) - pp.Suppress(pp.Literal(";")))
        wait_type = pp.Or((expression - pp.CaselessKeyword("CYCLES") -
                           pp.Opt(pp.Suppress(pp.Literal(",")) - expression - pp.CaselessKeyword("USEC")),
                           expression - pp.CaselessKeyword("USEC")))
        trst = pp.Group(pp.CaselessKeyword("TRST") - wait_type - pp.Suppress(pp.Literal(";")))
        wait = pp.Group(pp.CaselessKeyword("WAIT") - pp.Opt(identifier - pp.Suppress(pp.Literal(","))) -
                        wait_type - pp.Opt(pp.Suppress(pp.Literal(",")) - identifier) -
                        pp.Opt(pp.CaselessKeyword("MAX") - wait_type) - pp.Suppress(pp.Literal(";")))

        opt_label = pp.Opt(identifier + pp.Suppress(pp.Literal(":")))
        proc_instruction <<= pp.Or((assignment, boolean, call, crc, drscan, drstop, exit, export, for_, goto, if_,
                                    integer, irscan, irstop, note, pop, print, push, state, trst, wait))
        proc_statement = opt_label + proc_instruction
        data_statement = opt_label + pp.Or((boolean, integer))

        data = (opt_label + pp.CaselessKeyword("DATA") - identifier -
                pp.Suppress(pp.Literal(";")) -
                pp.ZeroOrMore(data_statement) -
                opt_label - pp.CaselessKeyword("ENDDATA") - pp.Suppress(pp.Literal(";")))
        procedure = pp.Group(pp.Group(opt_label + pp.CaselessKeyword("PROCEDURE") - identifier -
                                      pp.Opt(pp.CaselessKeyword("USES") - identifier -
                                             pp.ZeroOrMore(pp.Literal(",") - identifier)) -
                                      pp.Suppress(pp.Literal(";"))) -
                             pp.ZeroOrMore(proc_statement) -
                             pp.Group(opt_label - pp.CaselessKeyword("ENDPROC") - pp.Suppress(pp.Literal(";"))))
        for_ <<= pp.Group(pp.Group(pp.CaselessKeyword("FOR") - identifier - pp.Literal("=") -
                                   expression - pp.CaselessKeyword("TO") - expression -
                                   pp.Opt(pp.CaselessKeyword("STEP") - expression) - pp.Suppress(pp.Literal(";"))) -
                          pp.ZeroOrMore(proc_statement) -
                          pp.Group(opt_label - pp.CaselessKeyword("NEXT") - identifier - pp.Suppress(pp.Literal(";"))))

        stapl_file = (pp.ZeroOrMore(note) +
                      pp.ZeroOrMore(opt_label + action) +
                      pp.ZeroOrMore(pp.Or((procedure, data))) +
                      opt_label + crc + pp.StringEnd())
        
        stapl_file.ignore(comments)

        parsed = stapl_file.parse_string(f.read())
        return parsed
