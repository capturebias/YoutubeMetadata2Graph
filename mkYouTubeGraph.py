#!/usr/bin/env python

from datetime import datetime
from json import load
from sys import stdin, stdout, stderr

from rdflib import BNode, Literal, Graph, URIRef
from rdflib.namespace import DCTERMS, FOAF, Namespace, OWL, RDF, RDFS, VOID, XSD


GRAPH_LABEL = "YouTube Meta-Data Graph"
GRAPH_DESCRIPTION = """A knowledge graph containing video meta data (context) from
news channels on YouTube for use in the CaptureBias project"""
GRAPH_CREATOR = "Wilcke WX"
GRAPH_CREATED = datetime.now().isoformat()
GRAPH_NAMESPACE = "http://example.org#"
GRAPH_SEEALSO = "https://capturebias.wordpress.com"
GRAPH_SOURCE_NAME = "YouTube"
GRAPH_SOURCE_HREF = "https://youtube.com"

SIOC = Namespace('http://rdfs.org/sioc/ns#')


def init_entity(base_ns):
    return URIRef(base_ns+BNode().title())

def init_graph(base_ns):
    g = Graph()

    g.add((URIRef(base_ns), RDF.type, VOID.Dataset))
    g.add((URIRef(base_ns), RDFS.label, Literal(GRAPH_LABEL, lang="en")))
    g.add((URIRef(base_ns), RDFS.comment, Literal(GRAPH_DESCRIPTION, lang="en")))
    g.add((URIRef(base_ns), RDFS.seeAlso, Literal(GRAPH_SEEALSO,
                                                  datatype=XSD.anyURI)))
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

def dict_to_graph(base_ns, g, data_dict):
    channels = data_dict.keys()
    if len(channels) <= 0:
        stderr.write("No channel data found\n")

    for channel in channels:
        channel_data = data_dict[channel]
        channel_uri = add_channel(base_ns, g, channel_data)

        videos = channel_data['videos']
        if len(videos) <= 0:
            stderr.write("No video data found for channel %s\n" % channel)
        for video_data in videos:
            video_uri = add_video(base_ns, g, video_data)

            # link channel to videos
            g.add(channel_uri, SIOC.creator_of, video_uri)
            g.add(video_uri, SIOC.has_creator, channel_uri)

    return g

def add_channel(base_ns, g, channel_data):
    channel_uri = URIRef(base_ns+channel_data['id'])
    g.add((channel_uri, RDF.type, SIOC.OnlineAccount))

    if 'snippet' in channel_data.keys():
        pass

    if 'contentDetails' in channel_data.keys():
        pass

    if 'topicDetails' in channel_data.keys():
        pass

    if 'brandingSettings' in channel_data.keys():
        pass

    if 'statistics' in channel_data.keys():
        pass

    return channel_uri

def add_channel_snippet(base_ns, g, channel_uri, snippet_data):
    for attr, value in snippet_data.items():
        if attr == 'title':
            g.add((channel_uri, DCTERMS.title,
                   Literal(value, lang='en')))

        if attr == 'description':
            g.add((channel_uri, DCTERMS.description,
                   Literal(value, lang='en')))

        if attr == 'thumbnails' and 'default' in value.keys():
            if 'url' in value['default']:
                g.add((channel_uri, SIOC.avatar,
                       Literal(value, datatype=XSD.anyURI)))

        if attr == 'country':
            pass

def add_video(base_ns, g, video_data):
    video_uri = URIRef(base_ns+video_data['id'])
    g.add((video_uri, RDF.type, base_ns.Post))


    return video_uri

def main(data_dict):
    base_ns = Namespace(GRAPH_NAMESPACE)
    g = init_graph(base_ns)

    return dict_to_graph(base_ns, g, data_dict)

if __name__ == "__main__":
    data_dict = load(stdin)

    g = main(data_dict)

    stdout.write(g.serialize(format="nt").decode('utf-8'))
