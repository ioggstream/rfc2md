from rfcxml import *


fpath = "draft-cedik-http-warning-01.xml"
fpath = "draft-polli-service-description-well-known-uri.xml"


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


def harn_get_root(fpath):
    xml = Path(fpath).read_bytes()
    return etree.fromstring(xml)


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
    out = "".join(txt)
    assert "name:" in out


def test_root():
    root = harn_get_root(fpath)
    for c in root:
        txt = parse(c)
        out = list(txt)
        Path(f"_{c.tag}.md").write_text("".join(out))


def test_parse_section():
    t = b'<section title="Introduction" anchor="introduction"><t>Many current APIs are based on HTTP   <xref target="RFC7230"/> as their application protocol. Their   response handling model is based on the assumption that requests either are   successful or they fail. In both cases (success and fail) an HTTP status code   <xref target="RFC7231"/> is returned to convey either fact.</t><t>But response status is not always strictly either success or failure. For example, there are cases where an underlying   system returns a response with data that cannot be defined as a clear error. API   providers who are integrating such a service might want to   return a correct response nonetheless, but returning a HTTP status code of e.g. 200 OK   without any additional information is not the only possible approach in this case.</t><t>As defined in the principles of Web architecture   <xref target="W3C.REC-webarch-20041215"/>, agents that "recover from errors by   making a choice without the user\'s consent are not acting on the user\'s behalf".   Therefore APIs should be able to communicate what has happened to their consumers, which then allows clients or users to make more informed decisions.</t><t>This document defines a warning code and a standard response structure for communicating and representing warning   information in HTTP APIs. The goal is to allow HTTP providers to have a standardized way of communicating to their consumers that while the response can be considered to be a non-failure, there is some warning information available that they might want to take into account.</t><t>As a general guideline, warning information should be considered to be any information that can be safely ignored (treating the response as if it did not contain any warning information), but that might help clients and users to make better decisions.</t>\n      </section>\n      '
    xml_t = etree.fromstring(t)
    txt = parse_section(xml_t)

    out = "".join(txt)
    assert "{{?RFC7230}}" in out
    assert "# Introduction {#introduction}\n" in out


def test_parse_section_unnumbered():
    t = b'<section title="Introduction" numbered="false" anchor="introduction"><t>Many current APIs are based on HTTP   <xref target="RFC7230"/> as their application protocol. Their   response handling model is based on the assumption that requests either are   successful or they fail. In both cases (success and fail) an HTTP status code   <xref target="RFC7231"/> is returned to convey either fact.</t><t>But response status is not always strictly either success or failure. For example, there are cases where an underlying   system returns a response with data that cannot be defined as a clear error. API   providers who are integrating such a service might want to   return a correct response nonetheless, but returning a HTTP status code of e.g. 200 OK   without any additional information is not the only possible approach in this case.</t><t>As defined in the principles of Web architecture   <xref target="W3C.REC-webarch-20041215"/>, agents that "recover from errors by   making a choice without the user\'s consent are not acting on the user\'s behalf".   Therefore APIs should be able to communicate what has happened to their consumers, which then allows clients or users to make more informed decisions.</t><t>This document defines a warning code and a standard response structure for communicating and representing warning   information in HTTP APIs. The goal is to allow HTTP providers to have a standardized way of communicating to their consumers that while the response can be considered to be a non-failure, there is some warning information available that they might want to take into account.</t><t>As a general guideline, warning information should be considered to be any information that can be safely ignored (treating the response as if it did not contain any warning information), but that might help clients and users to make better decisions.</t>\n      </section>\n      '
    xml_t = etree.fromstring(t)
    txt = parse_section(xml_t)

    out = "".join(txt)
    assert 'numbered="false"' in out

def test_parse_figure():
    t = b'<figure><artwork>\nPOST /example HTTP/1.1\nHost: example.com\nAccept: application/json\n\nHTTP/1.1 200 OK\nContent-Type: application/json\nWarning: 246 - "Embedded Warning" "Fri, 04 Oct 2019 09:59:45 GMT"\n\n{\n  "request_id": "2326b087-d64e-43bd-a557-42171155084f",\n  "warnings": [\n    {\n      "detail": "Street name was too long. It has been shortened...",\n      "instance": "https://example.com/shipments/3a186c51/msgs/c94d",\n      "status": "200",\n      "title": "Street name too long. It has been shortened.",\n      "type": "https://example.com/errors/shortened_entry"\n    },\n    {\n      "detail": "City for this zipcode unknown. Code for shipment..",\n      "instance": "https://example.com/shipments/3a186c51/msgs/5927",\n      "status": "200",\n      "title": "City for zipcode unknown.",\n      "type": "https://example.com/errors/city_unknown"\n    }\n  ],\n  "id": "3a186c51d4281acb",\n  "carrier_tracking_no": "84168117830018",\n  "tracking_url": "http://example.com/3a186c51d",\n  "label_url": "http://example.com/shipping_label_3a186c51d.pdf",\n  "price": 3.4\n}\n</artwork></figure>'
    xml_t = etree.fromstring(t)
    txt = parse_figure(xml_t)

    out = "".join(txt)
    assert "~~~\n\nPOST" in out


def test_parse_rfc():
    t = b"""<rfc
    ipr = "trust200902"
    docName = "draft-polli-service-description-well-known-uri-latest"
    category = "std" ></rfc>
    """
    xml_t = etree.fromstring(t)
    txt = parse_rfc(xml_t)
    out = "".join(txt)
    assert "docname: "


def test_parse_front():
    front = harn_get_root("front.xml")
    txt = parse_front(front)
    out = "".join(txt)
    assert "workgroup" in out


def test_parse_note():
    note = harn_get_root("note.xml")
    txt = parse(note)
    out = "".join(txt)
    assert "<https://lists.w3.org/Archives/Public/ietf-http-wg/>." in out


def test_parse_middle():
    root = harn_get_root("middle.xml")
    md = parse_middle(root)
    out = list(md)
    Path("_middle.md").write_text("".join(out))


def test_parse_back():
    root = harn_get_root("back.xml")
    md = parse(root)
    out = list(md)
    Path("_back.md").write_text("".join(out))


def test_parse_references():
    root = harn_get_root("reference.xml")
    md = parse_references(root)
    out = list(md)
    Path("_references.md").write_text("".join(out))


def test_parse_reference_2():
    t = (
        b'<reference xmlns:xi="http://www.w3.org/2001/XInclude" anchor="OpenAPI" targe'
        b't="https://github.com/OAI/OpenAPI-Specification"><front>\n    '
        b"        <title>OpenAPI Specifications</title>  <author>\n     "
        b'         <organization/>  </author>  <date year="n'
        b'.d."/></front>\n        </reference>\n        '
    )
    xml_t = etree.fromstring(t)
    txt = parse_reference(xml_t)
    out = "".join(txt)
    assert "title: OpenAPI Specifications" in out


"""
  HTML:
    target: https://html.spec.whatwg.org/
    title: HTML
    author:
    -
      ins: I. Hickson
      name: Ian Hickson
      organization: Google, Inc.
    -
      ins: S. Pieters
      name: Simon Pieters
      organization: Opera
    -
      ins: A. van Kesteren
      name: Anne van Kesteren
      organization: Mozilla
    -
      ins: P. Jägenstedt
      name: Philip Jägenstedt
      organization: Opera
    -
      ins: D. Denicola
      name: Domenic Denicola
      organization: Google, Inc.

"""


def test_parse_spanx():
    t = b'<t><spanx style="emph">RFC EDITOR: please remove this section before publication</spanx></t>'
    xml_t = etree.fromstring(t)
    txt = parse_t(xml_t)
    out = "".join(txt)
    assert "*RFC: "


def test_eref():
    t = b'<eref xmlns:xi="http://www.w3.org/2001/XInclude" target="https://lists.w3.org/Archives/Public/ietf-http-wg/">https://lists.w3.org/Archives/Public/ietf-http-wg/</eref>'
    xml_t = etree.fromstring(t)
    txt = parse_eref(xml_t)
    out = "".join(txt)
