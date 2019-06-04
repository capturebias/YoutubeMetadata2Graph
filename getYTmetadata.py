#!/usr/bin/env python

from datetime import datetime
from json import dump
from requests import exceptions
from sys import stderr, stdin, stdout

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


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
        key = kf.read().split()[0]

    return key

def build_service_object(api_service_name, api_version, developer_key):
    return build(api_service_name, api_version, developerKey=developer_key)

def request_channel_data(service, channel_id):
    # https://developers.google.com/youtube/v3/docs/channels
    #
    # - The snippet object contains basic details about the channel, such as its
    #   title, description, and thumbnail images. (quota -= 2)
    # - The contentDetails object encapsulates information about the channel's
    #   content. (quota -= 2)
    # - The statistics object encapsulates statistics for the channel. (quota -= 2)
    # - The topicDetails object encapsulates information about topics associated
    #   with the channel. (quota -= 2)
    # - The brandingSettings object encapsulates information about the branding
    #   of the channel. (quota -= 2)
    #
    # quota needed per request: 10 + 1 (initial costs) = 11
    request = service.channels().list(
        part="snippet,contentDetails,statistics,topicDetails,brandingSettings",
        id=channel_id
    )

    return request_data(request)

def request_video_data(service, video_id):
    # https://developers.google.com/youtube/v3/docs/videos
    #
    # - The snippet object contains basic details about the video, such as its
    #   title, description, and category. (quota -= 2)
    # - The contentDetails object contains information about the video content,
    #   including the length of the video and an indication of whether captions
    #   are available for the video. (quota -= 2)
    # - The statistics object contains statistics about the video. (quota -= 2)
    # - The topicDetails object encapsulates information about topics
    #   associated with the video. (quota -= 2)
    #
    # quota needed per request: 8 + 1 (initial costs) = 9
    request = service.videos().list(
        part="snippet,contentDetails,statistics,topicDetails",
        id=video_id
    )

    return request_data(request)

def request_data(request):
    try:
        response = request.execute()
    except HttpError as e:
        stderr.write("API HTTP Error: %s\n" % (e))
        return (dict(), False, True)
    except exceptions.RequestException as e:
        stderr.write("Request Error: %s\n" % (e))
        return (dict(), False, False)

    return (response['items'][0], True, False) # strip request meta data

def main():
    developer_key = read_developer_key(DEVELOPER_KEY_FILE)
    service = build_service_object(API_SERVICE_NAME, API_VERSION, developer_key)

    data = dict()
    for video_id in video(stdin):
        video_data, success, api_error = request_video_data(service, video_id)
        if api_error:
            stderr.write("Failed retrieving video %s\n" % (video_id))
            break
        if not success:
            stderr.write("Failed retrieving video %s\n" % (video_id))
            continue

        video_data['retrieved_on'] = datetime.today().strftime("%Y-%m-%dT%H:%M:%S")

        # extract channel ID
        channel_id = video_data['snippet']['channelId']
        if channel_id not in data.keys():
            channel_data, success, api_error = request_channel_data(service, channel_id)
            if api_error:
                stderr.write("Failed retrieving video %s\n" % (video_id))
                stderr.write("Failed retrieving channel %s\n" % (channel_id))
                break

            if not success:
                stderr.write("Failed retrieving channel %s\n" % (channel_id))
            else:
                channel_data['retrieved_on'] = datetime.today().strftime("%Y-%m-%dT%H:%M:%S")

            channel_data['videos'] = list()

            # add new channel
            data[channel_id] = channel_data

        # add new video to channel
        data[channel_id]['videos'].append(video_data)

    return data

if __name__ == "__main__":
    data = main()

    dump(data, stdout, indent=4)
