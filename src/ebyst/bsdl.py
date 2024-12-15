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

class BSDLFile:
    """BSDL parser"""

    class Declaration:
        def __init__(self, name, type_, value=None, direction=None, range_start=None, range_end=None, owner=None):
            self.name = name
            self.type_ = type_
            self.value = value
            self.direction = direction
            self.range_start = range_start
            self.range_end = range_end
            self.owner = owner

    def __init__(self, name):
        self.name = name
        self.generics = {}
        self.ports = {}
        self.constants = {}
        self.attributes = {}

    @classmethod
    def parse(cls, f):
        comments = "--" + pp.SkipTo(pp.LineEnd())
        identifier = pp.Word(init_chars=pp.srange("[a-zA-Z]"), body_chars=pp.srange("[a-zA-Z0-9_]"))
        string_literal = pp.Combine(pp.QuotedString("\"") +
                                    pp.ZeroOrMore(pp.Suppress(pp.Literal("&")) + pp.QuotedString("\"")), adjacent=False)
        numeric_literal = pp.Or((pp.pyparsing_common.sci_real, pp.pyparsing_common.integer))
        primary = pp.Forward()
        enumeration_literal = (pp.Suppress(pp.Literal("(")) + primary +
                               pp.ZeroOrMore(pp.Suppress(pp.Literal(",")) + primary) + pp.Suppress(pp.Literal(")")))
        literal = pp.Or((numeric_literal, enumeration_literal, string_literal))
        primary <<= pp.Or((identifier, literal))
        expression = primary
        mode = pp.Or((pp.CaselessKeyword("in"), pp.CaselessKeyword("out"), pp.CaselessKeyword("inout"),
                     pp.CaselessKeyword("buffer"), pp.CaselessKeyword("linkage")))
        range = (pp.Suppress(pp.Literal("(")) + pp.pyparsing_common.integer +
                 pp.Or((pp.CaselessKeyword("to"), pp.CaselessKeyword("downto"))) +
                 pp.pyparsing_common.integer + pp.Suppress(pp.Literal(")")))
        subtype_indication = identifier + pp.Optional(range)
        declaration = pp.Group(identifier + pp.Suppress(pp.Literal(":")) +
                            pp.Optional(mode) + subtype_indication +
                            pp.Optional(pp.Suppress(pp.Literal(":=")) + expression))
        interface_list = declaration + pp.ZeroOrMore(pp.Suppress(pp.Literal(";")) + declaration)
        generic_clause = pp.Group(pp.CaselessKeyword("generic") + pp.Suppress(pp.Literal("(")) + interface_list +
                                  pp.Suppress(pp.Literal(")")) + pp.Suppress(pp.Literal(";")))
        port_clause = pp.Group(pp.CaselessKeyword("port") + pp.Suppress(pp.Literal("(")) + interface_list +
                               pp.Suppress(pp.Literal(")")) + pp.Suppress(pp.Literal(";")))
        use_clause = pp.Group(pp.CaselessKeyword("use") + identifier + pp.Literal(".") + identifier +
                              pp.ZeroOrMore(pp.Literal(",") + identifier) +
                              pp.Suppress(pp.Literal(";")))
        class_ = pp.Or((pp.CaselessKeyword("entity"), pp.CaselessKeyword("signal")))
        attribute_specification = pp.Group(pp.CaselessKeyword("attribute") + identifier +
                                           pp.Suppress(pp.CaselessKeyword("of")) + identifier +
                                           pp.Suppress(pp.Literal(":")) + class_ +
                                           pp.Suppress(pp.CaselessKeyword("is")) + expression +
                                           pp.Suppress(pp.Literal(";")))
        constant_declaration = pp.Group(pp.CaselessKeyword("constant") + declaration + pp.Suppress(pp.Literal(";")))
        entity_header = pp.Optional(generic_clause) + pp.Optional(port_clause)
        entity_declarative_item = pp.Or((use_clause, attribute_specification, constant_declaration))
        entity_declaration = (pp.Suppress(pp.CaselessKeyword("entity")) + identifier + pp.Suppress(pp.CaselessKeyword("is")) +
                              entity_header + pp.ZeroOrMore(entity_declarative_item) +
                              pp.Suppress(pp.CaselessKeyword("end") + pp.Optional(pp.CaselessKeyword("entity")) +
                                          pp.Optional(identifier)) +
                              pp.Suppress(pp.Literal(";")))
        bsdl_file = entity_declaration + pp.StringEnd()

        bsdl_file.ignore(comments)

        parsed = bsdl_file.parse_string(f.read())
        # parsed.pprint()
        r = cls(parsed[0])
        for item in parsed[1:]:
            if item[0] == "generic":
                for generic in item[1:]:
                    assert len(generic) == 3
                    generic = BSDLFile.Declaration(generic[0], generic[1], value=generic[2])
                    r.generics[generic.name] = generic
            elif item[0] == "port":
                for port in item[1:]:
                    if len(port) == 3:
                        port = BSDLFile.Declaration(port[0], port[2], direction=port[1])
                    elif len(port) == 6:
                        port = BSDLFile.Declaration(port[0], port[2], direction=port[1],
                                                    range_start=port[3], range_end=port[5])
                    r.ports[port.name] = port
            elif item[0] == "use":
                pass
            elif item[0] == "constant":
                assert len(item) == 2
                assert len(item[1]) == 3
                constant = BSDLFile.Declaration(name=item[1][0], type_=item[1][1], value=item[1][2])
                r.constants[constant.name] = constant
            elif item[0] == "attribute":
                assert len(item) >= 5
                # TODO fix tuples
                attribute = BSDLFile.Declaration(name=item[1], type_ = item[3], owner=item[2], value=item[4])
                r.attributes[attribute.name] = attribute
            else:
                assert False

        return r
