#!/usr/bin/env python

from base64 import urlsafe_b64encode
from datetime import datetime
from hashlib import sha1
from json import load
from sys import stdin, stdout, stderr

from rdflib import BNode, Literal, Graph, URIRef
from rdflib.namespace import DC, DCTERMS, FOAF, Namespace, OWL, RDF, RDFS, VOID, XSD


YOUTUBE_HREF = "https://www.youtube.com"
GRAPH_LABEL = "YouTube Meta-Data Graph"
GRAPH_DESCRIPTION = """A knowledge graph containing video meta data (context) from
news channels on YouTube for use in the CaptureBias project"""
GRAPH_CREATOR = "Wilcke WX"
GRAPH_CREATED = datetime.now().isoformat()
GRAPH_NAMESPACE = Namespace("http://capturebias.wordpress.com/rdf/yt2014#")
GRAPH_SEEALSO = "https://capturebias.wordpress.com"
GRAPH_SOURCE_NAME = "YouTube"

CATEGORY_FILE = "./categories.json"
GEONAMES_FILE = "./geonames.json"

YTMDS = Namespace("http://capturebias.wordpress.com/rdf/schema#")
YTMDV = Namespace("http://capturebias.wordpress.com/rdf/vocab#")

BASE = GRAPH_NAMESPACE


country_map = dict()

def init_entity(name=None, pre='n'):
    if name is None:
        name = BNode()
    else:
        hasher = sha1(name.encode('utf8'))
        name = urlsafe_b64encode(hasher.digest()).decode('utf8')
        if name[0].isdigit():
            name = pre+name

    return URIRef(BASE+name.title())

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
    g.add((source, FOAF.homepage, Literal(YOUTUBE_HREF,
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
            g.add((channel_uri, YTMDS.published, video_uri))
            g.add((video_uri, YTMDS.published_by, channel_uri))

    return g

def add_channel(g, channel_data, geonames_map):
    chid = channel_data['id']
    channel_uri = URIRef(BASE+'c='+chid)
    g.add((channel_uri, RDF.type, YTMDS.Channel))
    g.add((channel_uri, DC.identifier, Literal(chid,
                                               datatype=XSD.string)))
    g.add((channel_uri, OWL.sameAs, URIRef(YOUTUBE_HREF+'/channel/'+chid)))

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
    vid = video_data['id']
    video_uri = URIRef(BASE+'v='+vid)
    g.add((video_uri, RDF.type, YTMDS.Video))
    g.add((video_uri, DC.identifier, Literal(vid,
                                             datatype=XSD.string)))
    g.add((video_uri, DC.source, Literal(YOUTUBE_HREF+'/watch?v='+vid,
                                         datatype=XSD.anyURI)))

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
            g.add((video_uri, YTMDS.duration,
                  Literal(value, datatype=YTMDS.ISO8601Duration)))
            continue
        if attr == 'dimension':
            if value.lower() == '3d':
                g.add((video_uri, YTMDS.dimension, YTMDV.ThreeDimensional))
            elif value.lower() == '2d':
                g.add((video_uri, YTMDS.dimension, YTMDV.TwoDimensional))
            continue
        if attr == 'definition':
            if value.lower() == 'sd':
                g.add((video_uri, YTMDS.definition, YTMDV.StandardDefinition))
            elif value.lower() == 'hd':
                g.add((video_uri, YTMDS.definition, YTMDV.HighDefinition))
            continue
        if attr == 'projection':
            if value.lower() == '360':
                g.add((video_uri, YTMDS.projection,
                       YTMDV.SphericalProjection))
            elif value.lower() == 'rectangular':
                g.add((video_uri, YTMDS.projection,
                       YTMDV.RectangularProjection))
            continue
        if attr == 'regionRestriction':
            if 'allowed' in value.keys():
                for cc in value['allowed']:
                    country_uri = init_country(g, cc, geonames_map)
                    g.add((video_uri, YTMDS.allowed_in, country_uri))
            if 'blocked' in value.keys():
                for cc in value['blocked']:
                    country_uri = init_country(g, cc, geonames_map)
                    g.add((video_uri, YTMDS.blocked_in, country_uri))
            continue
        if attr == 'contentRating':
            for rating_scheme, rating in value.items():
                if not rating_scheme.endswith("Rating"):
                    continue
                rating_uri = URIRef(YTMDV+rating)
                g.add((video_uri, YTMDS.rating, rating_uri))
            continue

def add_topicDetails(g, subject_uri, data):
    for attr, value in data.items():
        if attr == 'topicCategories':
            for item in value:
                g.add((subject_uri, YTMDS.topic,
                       Literal(item, datatype=XSD.anyURI)))
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
        if attr == 'thumbnails' and 'standard' in value.keys():
            add_thumbnail(g, video_uri, value['standard'])
            continue

        if attr == 'tags':
            for tag in value:
                if tag in ("Not Specified"):
                    continue
                g.add((video_uri, YTMDS.tag,
                       Literal(tag, datatype=XSD.string)))
            continue

        if attr == 'categoryId':
            if value in categories_map.keys():
                cat = categories_map[value].replace('&', "and")
                cat = cat.replace('/', ' ').replace('-', ' ')
                cat_fragment = '_'.join(cat.split())
                g.add((video_uri, YTMDS.category, URIRef(YTMDV+cat_fragment)))
            continue

def add_thumbnail(g, subject_uri, image_data):
    if 'url' not in image_data.keys():
        return

    image_uri = init_entity()
    g.add((subject_uri, YTMDS.thumbnail, image_uri))
    g.add((image_uri, RDF.type, FOAF.Image))

    g.add((image_uri, DC.source, Literal(image_data['url'],
                                         datatype=XSD.anyURI)))

    if 'width' in image_data.keys():
        g.add((image_uri, YTMDS.width, Literal(image_data['width'],
                                               datatype=XSD.nonNegativeInteger)))
    if 'height' in image_data.keys():
        g.add((image_uri, YTMDS.height, Literal(image_data['height'],
                                               datatype=XSD.nonNegativeInteger)))

def add_channel_snippet(g, channel_uri, data, geonames_map):
    add_snippet(g, channel_uri, data)

    for attr, value in data.items():
        if attr == 'thumbnails' and 'high' in value.keys():
            add_thumbnail(g, channel_uri, value['high'])
            continue

        if attr == 'country':
            country_uri = init_country(g, value, geonames_map)
            g.add((channel_uri, YTMDS.operates_from, country_uri))
            continue

def init_country(g, country_data, geonames_map):
    if country_data in country_map.keys():
        return country_map[country_data]

    country_uri = init_entity(country_data)
    g.add((country_uri, RDF.type, YTMDS.Country))
    g.add((country_uri, YTMDS.country_code, Literal(country_data,
                                                    datatype=YTMDS.ISO3166Alpha2)))

    country = geonames_map[country_data]
    if country is not None:
        g.add((country_uri, OWL.sameAs, URIRef(country)))

    country_map[country_data] = country_uri
    return country_uri

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
                g.add((channel_uri, YTMDS.keyword,
                       Literal(tag, datatype=XSD.string)))
            continue
        if attr == 'featuredChannelsUrls':
            for ch in value:
                uri = URIRef(YOUTUBE_HREF+'/channel/'+ch)
                g.add((channel_uri, DCTERMS.references, uri))
            continue
        if attr == 'moderateComments':
            if value:
                g.add((channel_uri, YTMDS.moderated,
                       Literal('true', datatype=XSD.boolean)))

def add_statistics(g, subject_uri, data):
    for attr, value in data.items():
        if attr == 'viewCount':
            g.add((subject_uri, YTMDS.num_views,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue

        if attr == 'commentCount':
            g.add((subject_uri, YTMDS.num_comments,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue

def add_video_statistics(g, video_uri, data):
    add_statistics(g, video_uri, data)

    for attr, value in data.items():
        if attr == 'likeCount':
            g.add((video_uri, YTMDS.num_likes,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue
        if attr == 'dislikeCount':
            g.add((video_uri, YTMDS.num_dislikes,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue
        if attr == 'favoriteCount':
            g.add((video_uri, YTMDS.num_favored,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue

def add_channel_statistics(g, channel_uri, data):
    add_statistics(g, channel_uri, data)

    for attr, value in data.items():
        if attr == 'subscriberCount':
            g.add((channel_uri, YTMDS.num_subscribers,
                   Literal(value, datatype=XSD.nonNegativeInteger)))
            continue

        if attr == 'videoCount':
            g.add((channel_uri, YTMDS.num_videos,
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
