#!/usr/bin/env python

from base64 import urlsafe_b64encode
from io import BytesIO
from requests import session
from shutil import copyfileobj
from sys import stdin, stdout, stderr
from time import sleep

from rdflib import BNode, Literal, Graph
from rdflib.namespace import DC, FOAF, Namespace, RDF, XSD


YTMDS = Namespace("http://capturebias.wordpress.com/rdf/schema#")
REQUEST_TIMEOUT = 0.2


def ntriple(t):
    triple = ""
    for term in t:
        if type(term) is Literal:
            triple += "\"{}\"".format(str(term))

            if term.datatype is not None:
                triple += "^^<{}>".format(str(term.datatype))
            elif term.language is not None:
                triple += "@{}".format(str(term.language))

            triple += ' '
        elif type(term) is BNode:
            triple += "_:{} ".format(str(term))
        else:  # URIRef
            triple += "<{}> ".format(str(term))

    return triple + '.'

def retrieve_raw_image(session, href):
    req = session.get(href, stream=True)

    t = 2
    while req.status_code == 429 and t <= 64:
        sleep(t) # Give it time to recuperate
        req = session.get(href, stream=True)

        t *= 2

    if not req.status_code == 200:
        return None

    return req.raw

def mkbinary(raw_img):
    raw_img.decode_content = True
    bytesIO = BytesIO()
    copyfileobj(raw_img, bytesIO)

    return urlsafe_b64encode(bytesIO.getvalue()).decode()

def main(g):
    ses = session()
    for image_uri, _, _ in g.triples((None, RDF.type, FOAF.Image)):
        href = g.value(image_uri, DC.source)
        if href is None:
            stderr.write("No href found for image %s\n" % image_uri)

            continue

        raw_img = retrieve_raw_image(ses, href)
        if raw_img is None:
            stderr.write("Failed request on image %s\n" % image_uri)
            sleep(REQUEST_TIMEOUT)

            continue

        b64string = mkbinary(raw_img)
        t = ntriple((image_uri, YTMDS.b64image, Literal(b64string,
                                                        datatype=XSD.b64string)))
        stdout.write(t+'\n')

        # Don't flood the server
        sleep(REQUEST_TIMEOUT)

if __name__ == "__main__":
    g = Graph()
    g.parse(data=stdin.read(), format='nt')

    main(g)
