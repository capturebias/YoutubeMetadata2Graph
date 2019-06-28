#!/usr/bin/env python

from datetime import datetime
from json import load
from sys import stdin, stdout, stderr

from rdflib import BNode, Literal, Graph, URIRef
from rdflib.namespace import DC, DCTERMS, FOAF, Namespace, RDF, RDFS, VOID, XSD


GRAPH_LABEL = "YouTube Meta-Data Graph"
GRAPH_DESCRIPTION = """A knowledge graph containing video meta data (context) from
news channels on YouTube for use in the CaptureBias project"""
GRAPH_CREATOR = "Wilcke WX"
GRAPH_CREATED = datetime.now().isoformat()
GRAPH_NAMESPACE = Namespace("http://example.org#")
GRAPH_SEEALSO = "https://capturebias.wordpress.com"
GRAPH_SOURCE_NAME = "YouTube"
GRAPH_SOURCE_HREF = "https://youtube.com"

CATEGORY_FILE = "./categories.json"
GEONAMES_FILE = "./geonames.json"

SIOC = Namespace('http://rdfs.org/sioc/ns#')
DBO = Namespace('http://dbpedia.org/ontology/')
SCHEMA_NAMESPACE = Namespace("http://example.org/ontology/")
VOCAB_NAMESPACE = Namespace("http://example.org/vocabulary/")

BASE = GRAPH_NAMESPACE
BASEONT = SCHEMA_NAMESPACE
BASEVOC = VOCAB_NAMESPACE


def init_entity():
    return URIRef(BASE+BNode().title())

def init_graph():
    g = Graph()

    g.add((URIRef(BASE), RDF.type, VOID.Dataset))
    g.add((URIRef(BASE), RDFS.label, Literal(GRAPH_LABEL, lang="en")))
    g.add((URIRef(BASE), RDFS.comment, Literal(GRAPH_DESCRIPTION, lang="en")))
    g.add((URIRef(BASE), RDFS.seeAlso, Literal(GRAPH_SEEALSO,
                                       datatype=XSD.anyURI)))
    g.add((URIRef(BASE), DCTERMS.creator, Literal(GRAPH_CREATOR,
                                          datatype=XSD.string)))
    g.add((URIRef(BASE), DCTERMS.created, Literal(GRAPH_CREATED,
                                         datatype=XSD.dateTime)))

    source = init_entity()
    g.add((URIRef(BASE), DCTERMS.source, source))
    g.add((source, RDF.type, FOAF.Organization))
    g.add((source, RDFS.label, Literal(GRAPH_SOURCE_NAME, lang="en")))
    g.add((source, FOAF.homepage, Literal(GRAPH_SOURCE_HREF,
                                          datatype=XSD.anyURI)))

    return g

def dict_to_graph(g, data_dict):
    categories_map = read_categories()
    geonames_map = read_geonames()

    channels = data_dict.keys()
    if len(channels) <= 0:
        stderr.write("No channel data found\n")

    for channel in channels:
        channel_data = data_dict[channel]
        channel_uri = add_channel(g, channel_data, geonames_map)

        videos = channel_data['videos']
        if len(videos) <= 0:
            stderr.write("No video data found for channel %s\n" % channel)
        for video_data in videos:
            video_uri = add_video(g, video_data, categories_map, geonames_map)

            # link channel to videos
            g.add((channel_uri, SIOC.creator_of, video_uri))
            g.add((video_uri, SIOC.has_creator, channel_uri))

    return g

def add_channel(g, channel_data, geonames_map):
    channel_uri = URIRef(BASE+channel_data['id'])
    g.add((channel_uri, RDF.type, SIOC.UserAccount))

    if 'snippet' in channel_data.keys():
        add_channel_snippet(g, channel_uri, channel_data['snippet'],
                            geonames_map)

    if 'contentDetails' in channel_data.keys():
        pass

    if 'topicDetails' in channel_data.keys():
        add_topicDetails(g, channel_uri, channel_data['topicDetails'])

    if 'brandingSettings' in channel_data.keys():
        add_channel_brandingSettings(g, channel_uri,
                                     channel_data['brandingSettings'])

    if 'statistics' in channel_data.keys():
        add_channel_statistics(g, channel_uri, channel_data['statistics'])

    return channel_uri

def add_video(g, video_data, categories_map, geonames_map):
    video_uri = URIRef(BASE+video_data['id'])
    g.add((video_uri, RDF.type, SIOC.Post))

    if 'snippet' in video_data.keys():
        add_video_snippet(g, video_uri, video_data['snippet'], categories_map)

    if 'contentDetails' in video_data.keys():
        add_video_contentDetails(g, video_uri, video_data['contentDetails'],
                                 geonames_map)

    if 'topicDetails' in video_data.keys():
        add_topicDetails(g, video_uri, video_data['topicDetails'])

    if 'statistics' in video_data.keys():
        add_video_statistics(g, video_uri, video_data['statistics'])

    return video_uri

def add_video_contentDetails(g, video_uri, data, geonames_map):
    for attr, value in data.items():
        if attr == 'duration':
            g.add((video_uri, BASEONT.duration,
                  Literal(value, datatype=BASEONT.ISO8601)))
            continue
        if attr == 'dimension':
            if value.lower() == '3d':
                g.add((video_uri, BASEONT.video_dimension, BASEVOC.ThreeDimensional))
            elif value.lower() == '2d':
                g.add((video_uri, BASEONT.video_dimension, BASEVOC.TwoDimensional))
            continue
        if attr == 'definition':
            if value.lower() == 'sd':
                g.add((video_uri, BASEONT.video_definition, BASEVOC.StandardDefinition))
            elif value.lower() == 'hd':
                g.add((video_uri, BASEONT.video_definition, BASEVOC.HighDefinition))
            continue
        if attr == 'projection':
            if value.lower() == '360':
                g.add((video_uri, BASEONT.video_projection,
                       BASEVOC.SphericalProjection))
            elif value.lower() == 'rectangular':
                g.add((video_uri, BASEONT.video_projection,
                       BASEVOC.RectangularProjection))
            continue
        if attr == 'regionRestriction':
            if 'allowed' in value.keys():
                for cc in value['allowed']:
                    country = URIRef(geonames_map[cc])
                    if country is None:
                        country = Literal(value, datatype=XSD.string)

                    g.add((video_uri, BASEONT.allowed_explicitly_in_country, country))
            if 'blocked' in value.keys():
                for cc in value['blocked']:
                    country = URIRef(geonames_map[cc])
                    if country is None:
                        country = Literal(value, datatype=XSD.string)

                    g.add((video_uri, BASEONT.blocked_explicitly_in_country, country))
            continue
        if attr == 'contentRating':
            for rating_scheme, rating in value.items():
                rating_uri = URIRef(BASEVOC+"{}_{}".format(rating_scheme, rating))
                g.add((video_uri, BASEONT.rating, rating_uri))
            continue

def add_topicDetails(g, subject_uri, data):
    for attr, value in data.items():
        if attr == 'topicCategories':
            for item in value:
                g.add((subject_uri, SIOC.topic,
                       URIRef(item)))
            continue

def add_snippet(g, subject_uri, data):
    for attr, value in data.items():
        if attr == 'title':
            g.add((subject_uri, DCTERMS.title,
                   Literal(value, lang='en')))
            continue

        if attr == 'description':
            g.add((subject_uri, DCTERMS.description,
                   Literal(value, lang='en')))
            continue

        if attr == 'publishedAt':
            g.add((subject_uri, DCTERMS.created,
                   Literal(value, datatype=XSD.dateTime)))
            continue

def add_video_snippet(g, video_uri, data, categories_map):
    add_snippet(g, video_uri, data)

    for attr, value in data.items():
        if attr == 'thumbnails' and 'default' in value.keys():
            if 'url' in value['default']:
                image_uri = URIRef(value['default']['url'])
                g.add((video_uri, FOAF.depiction, image_uri))
                g.add((image_uri, RDF.type, FOAF.Image))
            continue

        if attr == 'tags':
            for tag in value:
                g.add((video_uri, DC.subjects,
                       Literal(tag, datatype=XSD.string)))
            continue

        if attr == 'categoryId':
            if value in categories_map.keys():
                cat_fragment = '_'.join(categories_map[value].replace('&','And').split())
                g.add((video_uri, DBO.category, URIRef(BASEVOC+cat_fragment)))
            continue

def add_channel_snippet(g, channel_uri, data, geonames_map):
    add_snippet(g, channel_uri, data)

    for attr, value in data.items():
        if attr == 'thumbnails' and 'default' in value.keys():
            if 'url' in value['default']:
                image_uri = URIRef(value['default']['url'])
                g.add((channel_uri, SIOC.avatar, image_uri))
                g.add((image_uri, RDF.type, FOAF.Image))
            continue

        if attr == 'country':
            country = URIRef(geonames_map[value])
            if country is None:
                country = Literal(value, datatype=XSD.string)

            g.add((channel_uri, DBO.country, country))
            continue

def add_channel_brandingSettings(g, channel_uri, data):
    for attr, value in data.items():
        if attr == 'channel' and 'keywords' in value.keys():
            tags = set()
            tag = ""
            multi_tag = False
            for c in value['keywords']:
                if c == '"':
                    if len(tag) > 0:
                        multi_tag = False
                        tags.add(tag)
                        tag = ""
                    else:
                        multi_tag = True

                    continue
                elif c == " " and not multi_tag:
                    if len(tag) > 0:
                        tags.add(tag)
                        tag = ""

                    continue

                tag += c

            if len(tag) > 0:
                tags.add(tag)

            for tag in tags:
                g.add((channel_uri, DC.subjects,
                       Literal(tag, datatype=XSD.string)))
            continue
        if attr == 'featuredChannelsUrls':
            for ch in value:
                uri = URIRef(BASEVOC+ch)
                g.add((channel_uri, DCTERMS.references, uri))
            continue
        if attr == 'moderateComments':
            if value:
                g.add((channel_uri, BASEONT.moderates_comments,
                       Literal('true', datatype=XSD.boolean)))

def add_statistics(g, subject_uri, data):
    for attr, value in data.items():
        if attr == 'viewCount':
            g.add((subject_uri, SIOC.num_views,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue

        if attr == 'commentCount':
            g.add((subject_uri, SIOC.num_replies,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue

def add_video_statistics(g, video_uri, data):
    add_statistics(g, video_uri, data)

    for attr, value in data.items():
        if attr == 'likeCount':
            g.add((video_uri, BASEONT.num_likes,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue
        if attr == 'dislikeCount':
            g.add((video_uri, BASEONT.num_dislikes,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue
        if attr == 'favoriteCount':
            g.add((video_uri, BASEONT.num_endorsements,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue

def add_channel_statistics(g, channel_uri, data):
    add_statistics(g, channel_uri, data)

    for attr, value in data.items():
        if attr == 'subscriberCount':
            g.add((channel_uri, BASEONT.num_subscribers,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue

        if attr == 'videoCount':
            g.add((channel_uri, BASEONT.num_videos,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue

def read_geonames():
    data = dict()

    with open(GEONAMES_FILE, 'r') as f:
        data = load(f)

    return data

def read_categories():
    data = dict()

    with open(CATEGORY_FILE, 'r') as f:
        data = load(f)

    return {item['id']:item['snippet']['title'] for item in data['items']
            if 'items' in data.keys()
            and 'id' in item.keys()
            and 'snippet' in item.keys()
            and 'title' in item['snippet'].keys()}

def main(data_dict):
    g = init_graph()

    return dict_to_graph(g, data_dict)

if __name__ == "__main__":
    data_dict = load(stdin)

    g = main(data_dict)

    stdout.write(g.serialize(format="nt").decode('utf-8'))
