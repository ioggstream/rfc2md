# rfc2md
Generate markdown code from xml rfc documents.

## Testing

Just run

        tox -e py37

To reformat code after development use

        tox -e reformat


## Running

Convert an RFC written in XML into a .md file

        ./rfc2md.py draft-spec.xml > draft-spec.md

## Caveats

This tool is under development and may not support
all the possible xml quirks.

Anyway it provides a good starting point for converting
docs from xml to markdown.
