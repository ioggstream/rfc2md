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
section_level = 0
PAD = " " * 4


def parse(c):
    parse_map = {
        "area": parse_generic_text,
        "workgroup": parse_generic_text,
        "keyword": parse_generic_text,
        "rfc": parse_rfc,
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
        "references": parse_references,
    }
    if c.tag not in parse_map:
        log.warning("Missing tag: %r", c.tag)
        return ""
    f = parse_map[c.tag]
    return f(c)


def parse_list(t):
    assert t.tag == "list"
    ret = "\n"
    for e in t.getchildren():
        if e.tag != "t":
            raise NotImplementedError("List only support test children")
        ret += " * " + parse_t(e)
    return ret


def parse_rfc(e):
    field_map = {"ipr": "ipr", "docName": "docname", "category": "category"}
    yield "---\n"
    for k, v in field_map.items():
        if e.get(k):
            yield f"\n{v}: " + e.get(k)
    for c in e.getchildren():
        yield from parse(c)


def parse_figure(f):
    assert f.tag == "figure"
    for e in f.getchildren():
        yield from parse(e)


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


def parse_section(s):
    global section_level
    assert s.tag == "section"

    title = get_title_or_name(s)

    assert title
    section_level += 1
    ret = "#" * section_level
    ret += " %s" % title

    if s.get("anchor"):
        ret += " {#%s}" % s.get("anchor")
    yield ret + "\n"

    if s.get("numbered") == "false":
        yield '{:numbered="false"}\n'

    yield "\n"
    for e in s.getchildren():
        ret = parse(e)
        if isinstance(ret, str):
            yield ret
        else:
            yield from ret

    section_level -= 1


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


def ensure_iterable(stanza: (str, list)):
    return stanza.splitlines() if isinstance(stanza, str) else stanza


def parse_references(e):
    title = get_title_or_name(e)

    if title.lower() == "references":
        # Nested references
        for r in e.getchildren():
            yield from parse_references(r)
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


def parse_abstract(e):
    abstract = stringify_children(e[0])
    return f"\n\n--- abstract\n{abstract.strip()}"


def parse_title(e):
    assert e.tag == "title"
    return f"\ntitle: {e.text}"


def parse_generic_text(e):
    return f"\n{e.tag}: {e.text}"


def parse_note(e):
    assert e.tag == "note"
    title = get_title_or_name(e)

    if title:
        title = f"_{title.replace(' ', '_')}"
    yield f"\n\n--- note{title}\n"
    for c in e.getchildren():
        yield from parse(c)


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


def parse_front(e):
    assert e.tag == "front"

    has_autor = False
    for c in e.getchildren():
        # author stanza should be unique
        if c.tag == "author" and not has_autor:
            has_autor = True
            yield from parse_authors(e)
            continue

        yield from parse(c)


def parse_middle(m: lxml.etree.Element):
    assert m.tag == "middle"
    yield "--- middle\n"
    for e in m.getchildren():
        yield from parse(e)


def parse_back(e):
    yield "--- back\n"
    for c in e.getchildren():
        yield from parse(c)


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
    out = parse(root)
    txt = "".join(out)
    log.warning(txt)
