#!/usr/bin/env python3
from sys import argv
from collections import OrderedDict
from pathlib import Path
from lxml import etree

try:
    fpath = argv[10]
except IndexError:
    fpath = "draft-polli-service-description-well-known-uri.xml"
    fpath = "draft-cedik-http-warning-01.xml"

import lxml
from lxml import etree

txt = open(fpath).read()
root = etree.fromstring(txt.encode())

HEAD = """---
title: {{ front["@title"] }}
docname: {{ rfc["@docName"] }}
category: {{ rfc["@category"] }}

ipr: {{ rfc["@ipr"] }}

area: {{ front["@area"] }}
workgroup: {{ front["@workgroup"]}}
keyword: {{ front["@keyword"]}}

--- abstract

{{ front['abstract']['t'] }}

--- note_{{  front["note"]['@title'].replace(' ','_') }}

{{ front["note"]['t'] }}

"""


import types


def parse_list(t):
    assert t.tag == "list"
    ret = "\n"
    for e in t.getchildren():
        if e.tag != "t":
            raise NotImplementedError("List only support test children")
        ret += " * " + parse_t(e)
    return ret


def test_parse_list():
    t = b'<list>      <t>Warn Code: 246</t>      <t>Short Description: Embedded Warning</t>      <t>Reference: <xref target="warning-header"/> of [[ this document ]]</t>   </list>'
    xml_t = etree.fromstring(t)
    txt = parse_list(xml_t)
    assert " * Short Description: " in txt


def test_parse_t():
    t = b'<t><xref target="RFC8631"/> introduced the ability\nto provide documentation, descriptions, metadata, or status\ninformation for Web Services via Link Relations.</t>\n\n'
    xml_t = etree.fromstring(t)
    txt = parse_t(xml_t)
    assert "xref" not in txt


def test_parse_t_2():
    t = (
        b"<t><list>"
        b"<t>Warn Code: 246</t><t>Short Description: Embedded Warning</t>"
        b'<t>Reference: <xref target="warning-header"/> of [[ this document ]]</t>'
        b"</list>"
        b"</t>"
    )
    xml_t = etree.fromstring(t)
    txt = parse_t(xml_t)
    assert "Short Description" in txt


def test_parse_middle():
    txt = parse_middle(root[1])
    out = list(txt)
    Path("_middle.md").write_text("".join(out))


def test_parse_author():
    t = """
    <author initials="E." surname="Wilde" fullname="Erik Wilde">
         <organization>Axway</organization>
         <address>
            <email>erik.wilde@dret.net</email>
            <uri>http://dret.net/netdret/</uri>
         </address>
    </author>
    """
    xml_t = etree.fromstring(t)
    txt = parse_author(xml_t)
    assert "name:" in txt


def test_root():
    for c in root:
        txt = parse(c)
        out = list(txt)
        Path(f"_{c.tag}.md").write_text("".join(out))


def test_parse_section():
    t = b'<section title="Introduction" anchor="introduction">\n         <t>Many current APIs are based on HTTP\n            <xref target="RFC7230"/> as their application protocol. Their\n            response handling model is based on the assumption that requests either are\n            successful or they fail. In both cases (success and fail) an HTTP status code\n            <xref target="RFC7231"/> is returned to convey either fact.\n         </t>\n         <t>But response status is not always strictly either success or failure. For example, there are cases where an underlying\n            system returns a response with data that cannot be defined as a clear error. API\n            providers who are integrating such a service might want to\n            return a correct response nonetheless, but returning a HTTP status code of e.g. 200 OK\n            without any additional information is not the only possible approach in this case.\n         </t>\n         <t>As defined in the principles of Web architecture\n            <xref target="W3C.REC-webarch-20041215"/>, agents that "recover from errors by\n            making a choice without the user\'s consent are not acting on the user\'s behalf".\n            Therefore APIs should be able to communicate what has happened to their consumers, which then allows clients or users to make more informed decisions.\n         </t>\n         <t>This document defines a warning code and a standard response structure for communicating and representing warning\n            information in HTTP APIs. The goal is to allow HTTP providers to have a standardized way of communicating to their consumers that while the response can be considered to be a non-failure, there is some warning information available that they might want to take into account.\n         </t>\n         <t>As a general guideline, warning information should be considered to be any information that can be safely ignored (treating the response as if it did not contain any warning information), but that might help clients and users to make better decisions.</t>\n      </section>\n      '
    xml_t = etree.fromstring(t)
    txt = parse_section(xml_t)

    out = "".join(txt)
    assert "{{?RFC7230}}" in out
    assert "# Introduction {#introduction}\n" in out


def test_parse_figure():
    t = b'<figure><artwork>\nPOST /example HTTP/1.1\nHost: example.com\nAccept: application/json\n\nHTTP/1.1 200 OK\nContent-Type: application/json\nWarning: 246 - "Embedded Warning" "Fri, 04 Oct 2019 09:59:45 GMT"\n\n{\n  "request_id": "2326b087-d64e-43bd-a557-42171155084f",\n  "warnings": [\n    {\n      "detail": "Street name was too long. It has been shortened...",\n      "instance": "https://example.com/shipments/3a186c51/msgs/c94d",\n      "status": "200",\n      "title": "Street name too long. It has been shortened.",\n      "type": "https://example.com/errors/shortened_entry"\n    },\n    {\n      "detail": "City for this zipcode unknown. Code for shipment..",\n      "instance": "https://example.com/shipments/3a186c51/msgs/5927",\n      "status": "200",\n      "title": "City for zipcode unknown.",\n      "type": "https://example.com/errors/city_unknown"\n    }\n  ],\n  "id": "3a186c51d4281acb",\n  "carrier_tracking_no": "84168117830018",\n  "tracking_url": "http://example.com/3a186c51d",\n  "label_url": "http://example.com/shipping_label_3a186c51d.pdf",\n  "price": 3.4\n}\n</artwork></figure>\n         '
    xml_t = etree.fromstring(t)
    txt = parse_figure(xml_t)

    out = "".join(txt)
    assert "```\n\nPOST" in out


def parse_figure(f):
    assert f.tag == "figure"
    for e in f.getchildren():
        yield from parse(e)


def parse_artwork(a):
    assert a.tag == "artwork"
    yield """```\n%s\n```\n\n""" % a.text


section_level = 0


def get_text_element(e, key):
    items = e.findall(f".//{key}")
    if not items:
        return []
    assert len(items) == 1
    return items[0].text


def parse_author(author):

    ret = [
        f"""ins: { author.get('initials') } { author.get('surname') }""",
        f"""name: { author.get('fullname') }""",
    ]

    organization = get_text_element(author, "organization")
    if organization:
        ret.append(f"org: {organization}")

    email = get_text_element(author, "email")
    if email:
        ret += [f"email: {email}"]

    uri = get_text_element(author, "uri")
    if uri:
        ret += [f"uri: {uri}"]

    pad = " " * 2
    return f"\n-{pad}\n" + "\n".join((pad + x.strip() for x in ret))


def ensure_string(s):
    return s.decode() if hasattr(s, "decode") else s


def parse_t(t):
    assert t.tag == "t"
    text = stringify_children(t)

    for c in t.getchildren():
        if c.tag == "xref":
            c_text = ensure_string(etree.tostring(c)).strip(c.tail)
            c_values = c.values()
            assert len(c_values) == 1
            c_value = c_values[0]
            if c_value.startswith("RFC"):
                text = text.replace(c_text, "{{?%s}}" % c_value)
            else:
                text = text.replace(c_text, "{{%s}}" % c_value)
        elif c.tag == "list":
            text = parse_list(c)

    return text.strip() + "\n\n"


def stringify_children(node):
    from lxml.etree import tostring
    from itertools import chain

    c1 = list(
        chain(
            *(
                (tostring(child, with_tail=False), child.tail)
                for child in node.getchildren()
            )
        )
    )

    chunks = list(chain((node.text,), c1, (node.tail,)))
    return "".join([ensure_string(c) for c in chunks if c])


def parse(c):
    parse_map = {
        "note": parse_note,
        "abstract": parse_abstract,
        "author": parse_author,
        "title": parse_title,
        "front": parse_front,
        "middle": parse_middle,
        "back": parse_back,
        "t": parse_t,
        "section": parse_section,
        "figure": parse_figure,
        "artwork": parse_artwork,
        "list": parse_list,
    }
    if c.tag not in parse_map:
        print("Missing tag: ", c.tag)
        return ""
    f = parse_map[c.tag]
    return f(c)


def parse_section(s):
    global section_level
    assert s.tag == "section"
    assert s.get("title"), "Missing title"
    section_level += 1
    ret = "#" * section_level
    ret += " %s" % s.get("title")

    if s.get("anchor"):
        ret += " {#%s}" % s.get("anchor")
    yield ret + "\n\n"

    for e in s.getchildren():
        ret = parse(e)
        if isinstance(ret, str):
            yield ret
        else:
            yield from ret

    section_level -= 1


def parse_abstract(e):
    abstract = stringify_children(e[0])
    return f"\n\n--- abstract\n{abstract.strip()}"


def parse_title(e):
    assert e.tag == "title"
    return f"title: {e.text}"


def parse_note(e):
    assert e.tag == "note"
    title = e.get("title") or ""
    if title:
        title = f"_{title.replace(' ', '_')}"
    yield f"\n\n--- note{title}\n"
    for c in e.getchildren():
        yield from parse(c)


def parse_front(e):
    assert e.tag == "front"

    has_autor = False
    for c in e.getchildren():
        # author stanza should be unique
        if c.tag == "author" and not has_autor:
            has_autor = True
            yield "\nauthor:"
        yield from parse(c)


def parse_middle(m: lxml.etree.Element):
    assert m.tag == "middle"
    for e in m.getchildren():
        yield from parse(e)


def parse_back(b):
    yield ""
