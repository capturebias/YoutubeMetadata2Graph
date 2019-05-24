#!/usr/bin/env python

from sys import stdin

from googleapiclient.discovery import build


API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
DEVELOPER_KEY_FILE = "./developer_key"

def video(video_identifiers):
    for video_ids in video_identifiers:
        for video_id in video_ids.split():
            yield video_id

def read_developer_key(keyfile):
    key = None
    with open(keyfile, "r") as kf:
        key = kf.read.split()

    return key

def build_service_object(api_service_name, api_version, developer_key):
    return build(api_service_name, api_version, developerKey=developer_key)

def request_channel_data(service, channel_id):
    request = service.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_id
    )
    response = request.execute()

def request_video_data(service, video_id):
    request = service.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_id
    )
    response = request.execute()

def main():
    developer_key = read_developer_key(DEVELOPER_KEY_FILE)
    service = build_service_object(API_SERVICE_NAME, API_VERSION, developer_key)

    channels_visited = set()
    for video_id in video(stdin):
        channel_id, video_data = request_video_data(service, video_id)

        # add video_data to tsv
        if channel_id not in channels_visited:
            channel_data = request_channel_data(service, channel_id)

            # add channel_data to tsv
            channels_visited.add(channel_id)

        # add other types of linked information?

        # deal with errors
        # add retrieval dateTime

    # tsv close
    # print stats

if __name__ == "__main__":
    main()
