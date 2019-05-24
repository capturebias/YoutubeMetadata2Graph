#!/usr/bin/env python

from datetime import datetime
from sys import stdin, stdout

from rdflib import BNode, Literal, Graph, URIRef
from rdflib.namespace import DCTERMS, FOAF, Namespace, RDF, RDFS, VOID, XSD


GRAPH_LABEL = "YouTube Meta-Data Graph"
GRAPH_DESCRIPTION = "..."
GRAPH_CREATOR = "Wilcke WX"
GRAPH_CREATED = datetime.now().isoformat()
GRAPH_NAMESPACE = "http://example.org#"
GRAPH_SOURCE_NAME = "YouTube"
GRAPH_SOURCE_HREF = "https://youtube.com"

def video_id(video_identifiers):
    for video_ids in video_identifiers:
        for video_id in video_ids.split():
            yield video_id

def init_entity(base_ns):
    return URIRef(base_ns+BNode().title())

def init_graph(base_ns):
    base_ns = Namespace(base_ns)
    g = Graph()

    g.add((URIRef(base_ns), RDF.type, VOID.Dataset))
    g.add((URIRef(base_ns), RDFS.label, Literal(GRAPH_LABEL, lang="en")))
    g.add((URIRef(base_ns), RDFS.comment, Literal(GRAPH_DESCRIPTION, lang="en")))
    g.add((URIRef(base_ns), DCTERMS.creator, Literal(GRAPH_CREATOR,
                                                     datatype=XSD.string)))
    g.add((URIRef(base_ns), DCTERMS.created, Literal(GRAPH_CREATED,
                                                     datatype=XSD.dateTime)))

    source = init_entity(base_ns)
    g.add((URIRef(base_ns), DCTERMS.source, source))
    g.add((source, RDF.type, FOAF.Organization))
    g.add((source, RDFS.label, Literal(GRAPH_SOURCE_NAME, lang="en")))
    g.add((source, FOAF.homepage, Literal(GRAPH_SOURCE_HREF,
                                          datatype=XSD.anyURI)))

    return g

def main():
    for videoid in video_id(stdin):
        stdout.write(videoid)

if __name__ == "__main__":
    main()
