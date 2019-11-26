#!/usr/bin/env python3
from io import BytesIO
from sys import argv, stderr
from pathlib import Path
from lxml import etree
import lxml
from lxml import etree
import re
import logging

log = logging.getLogger()
logging.basicConfig()
# Global variables
PAD = " " * 4


def eventually_yield(wrapped):
    def tmp(*a, **k):
        ret = wrapped(*a, **k)
        if ret:
            yield from ret

    return tmp


class RFCXMLParser(object):
    def __init__(self):
        self.section_level = 0
        self.parts = {}

    def parse_section(self, e):
        assert e.tag == "section"

        title = get_title_or_name(e)

        assert title
        self.section_level += 1
        ret = "#" * self.section_level
        ret += " %s" % title

        if e.get("anchor"):
            ret += " {#%s}" % e.get("anchor")
        yield ret + "\n"

        if e.get("numbered") == "false":
            yield '{:numbered="false"}\n'

        yield "\n"
        for c in e.getchildren():
            ret = self.parse(c)
            if isinstance(ret, str):
                yield ret
            else:
                yield from ret

        self.section_level -= 1

    def parse(self, e):
        """
        Parses a set of predefined tags.
        While parse_map could be implemented via a reflection,
        I decided to being explicit on the supported functions
        for now.
        :param e:
        :return:
        """
        parse_map = {
            "area": parse_generic_text,
            "workgroup": parse_generic_text,
            "keyword": parse_generic_text,
            "rfc": self.parse_rfc,
            "note": self.parse_note,
            "abstract": parse_abstract,
            "author": parse_author,
            "title": parse_title,
            "front": self.parse_front,
            "middle": self.parse_middle,
            "back": self.parse_back,
            "t": parse_t,
            "section": self.parse_section,
            "figure": self.parse_figure,
            "artwork": parse_artwork,
            "list": parse_list,
            "references": self.parse_references,
        }
        if e.tag not in parse_map:
            log.warning("Missing tag: %r. %r", e.tag, etree.tostring(e))
            return ""
        f = parse_map[e.tag]
        if e.tag in ("references", "front", "abstract", "note", "middle", "back"):
            log.warning("Assigning tag %r to %r", e.tag, self.parts)
            self.parts[e.tag] = list(f(e))
            return
        return f(e)

    def parse_references(self, e):
        title = get_title_or_name(e)

        if title.lower() == "references":
            # Nested references
            for r in e.getchildren():
                yield from self.parse_references(r)
            return

        if "normative" in title.lower():
            yield f"\nnormative:\n"
        elif "informative" in title.lower():
            yield f"\ninformative:\n"
        else:
            raise NotImplementedError

        for r in e.getchildren():
            if r.tag == "name":
                # we already processed "name"
                continue
            assert r.tag != "author"
            ref = parse_reference(r)
            yield from (PAD + x + "\n" for x in ref)
        yield "\n"

    def parse_front(self, e):
        assert e.tag == "front"

        has_autor = False
        for c in e.getchildren():
            # author stanza should be unique
            if c.tag == "author" and not has_autor:
                has_autor = True
                yield from parse_authors(e)
                continue

            ret = self.parse(c)
            if ret:
                yield from ret

    def parse_rfc(self, e):
        field_map = {"ipr": "ipr", "docName": "docname", "category": "category"}
        yield "---\n"
        for k, v in field_map.items():
            if e.get(k):
                yield f"\n{v}: " + e.get(k)
        for c in e.getchildren():
            ret = self.parse(c)
            if ret:
                yield from ret

    def parse_note(self, e):
        assert e.tag == "note"
        title = get_title_or_name(e)

        if title:
            title = f"_{title.replace(' ', '_')}"
        yield f"\n\n--- note{title}\n"
        for c in e.getchildren():
            yield from self.parse(c)

    def parse_figure(self, f):
        assert f.tag == "figure"
        for e in f.getchildren():
            yield from self.parse(e)

    def parse_middle(self, e: lxml.etree.Element):
        assert e.tag == "middle"
        yield "--- middle\n"
        for c in e.getchildren():
            yield from self.parse(c)

    def parse_back(self, e):
        yield "--- back\n"
        for c in e.getchildren():
            p = self.parse(c)
            if p:
                yield from p

    def dump(self):
        ret = "".join(self.parts["front"])
        ret += "".join(self.parts["references"])
        ret += "".join(self.parts["abstract"])
        ret += "".join(self.parts["note"])
        ret += "".join(self.parts["middle"])
        ret += "".join(self.parts["back"])
        return ret


def parse_front(e):
    xmlparser = RFCXMLParser()
    ret = xmlparser.parse_front(e)
    return ret


def parse_references(e):
    xmlparser = RFCXMLParser()
    ret = xmlparser.parse_references(e)
    return ret


def parse_section(e):
    xmlparser = RFCXMLParser()
    return xmlparser.parse_section(e)


def parse_list(t):
    assert t.tag == "list"
    ret = "\n"
    for e in t.getchildren():
        if e.tag != "t":
            raise NotImplementedError("List only support test children")
        ret += " * " + parse_t(e)
    return ret


def parse_artwork(a):
    assert a.tag == "artwork"
    yield """~~~\n%s\n~~~\n\n""" % a.text


def get_text_element(e, key):
    items = e.findall(f".//{key}")
    if not items:
        return []
    assert len(items) == 1
    return items[0].text


def parse_author(author):

    if not author.get("initials"):
        return None

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

    yield f"\n{PAD}-\n"
    yield from (PAD + x + "\n" for x in ret)


def ensure_string(s):
    re_xquotes = re.compile("[“”]")
    r = s.decode() if hasattr(s, "decode") else s
    r = re_xquotes.sub("", r)
    return r


def parse_xref(e):
    c_values = e.values()
    if "default" in c_values:
        c_values.remove("default")
    assert len(c_values) == 1
    c_value = c_values[0]
    if c_value.startswith("RFC"):
        return "{{?%s}}" % c_value

    return "{{%s}}" % c_value


def parse_t(t):
    assert t.tag == "t"
    text = stringify_children(t)

    map_t = {
        "xref": parse_xref,
        "list": parse_list,
        "em": parse_em,
        "spanx": parse_spanx,
        "eref": parse_eref,
    }
    for c in t.getchildren():
        c_text = ensure_string(etree.tostring(c)).strip(c.tail)

        if c.tag not in map_t:
            raise NotImplementedError

        parse_f = map_t[c.tag]
        c_value = parse_f(c)
        text = text.replace(c_text, c_value)

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


def parse_spanx(e):
    assert e.tag == "spanx"
    style = e.get("style")
    r = e.text
    if style == "emph":
        r = f"*{r}*"
    return r


def parse_em(e):
    return f"*{e.text}*"


def parse_eref(e):
    target = e.get("target")
    text = e.text
    if target == text:
        return f"<{text}>"
    return f"[{text}]({target})"


def get_title_or_name(s):

    if s.get("title"):
        return s.get("title")

    if s.tag == "name":
        return s.text

    if s.findall(".//name"):
        return s.findall(".//name")[0].text

    raise NotImplementedError


def parse_reference(e):
    anchor = e.get("anchor")
    if not anchor:
        raise NotImplementedError
    if anchor.startswith("RFC"):
        yield f"{anchor}:"
        return

    ret = [f"{e.get('anchor')}:"]
    content = []
    if e.get("target"):
        content += [f'target: {e.get("target")}']

    front = e.findall(".//front")
    assert len(front) == 1
    for x in front[0].getchildren():
        if x.text:
            content += [f"{x.tag}: {x.text}"]

    authors = parse_authors(front[0])
    content += authors
    log.debug("content: %s", content)
    yield from ret + [PAD + x for x in content]


def parse_abstract(e):
    abstract = stringify_children(e[0])
    return f"\n\n--- abstract\n{abstract.strip()}"


def parse_title(e):
    assert e.tag == "title"
    return f"\ntitle: {e.text}"


def parse_generic_text(e):
    return f"\n{e.tag}: {e.text}"


def has_author(e):
    if e.tag != "author":
        return False

    if e.get("fullname"):
        return True

    return False


def parse_authors(e):
    # FIXME consider None authors
    log.debug("authors: %r", etree.tostring(e))
    authors = e.findall(".//author")
    if not any(has_author(a) for a in authors):
        return

    if authors:
        yield "\nauthor:"

    for c in authors:
        # author stanza should be unique
        a = parse_author(c)
        if a:
            yield from a


if __name__ == "__main__":
    from sys import argv
    from urllib.request import urlopen

    fpath = argv[1]
    if fpath.startswith("http"):
        txt = urlopen(fpath).read()
    else:
        txt = Path(fpath).read_bytes()

    parser = etree.XMLParser(
        dtd_validation=False,
        load_dtd=True,
        resolve_entities=True,
        no_network=False,
        recover=True,
    )
    root = etree.parse(BytesIO(txt), parser=parser).getroot()

    rfcxml = RFCXMLParser()
    out = rfcxml.parse(root)
    out = list(out)
    print(rfcxml.dump())
    # txt = "".join(out)
    # log.warning(txt)
