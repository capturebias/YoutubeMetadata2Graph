#!/usr/bin/env python

from datetime import datetime
from json import dump
from requests import exceptions
from sys import stderr, stdin, stdout
from time import sleep

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
DEVELOPER_KEY_FILE = "./developer_key"

QUOTA_DEFAULT = 10000
QUOTA_RESET_TIME = 24*60*60 + 600  # in seconds, plus some more time to be sure
QUOTA_MIN = 12  # costs of highest request

TEMPFILE = "./.TEMPFILE.json"


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
    cost = 12 # minimum+1 to be sure

    request = service.channels().list(
        part="snippet,contentDetails,statistics,topicDetails,brandingSettings",
        id=channel_id
    )

    return (request_data(request), cost)

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
    cost = 10 # minimum+1 to be sure

    request = service.videos().list(
        part="snippet,contentDetails,statistics,topicDetails",
        id=video_id
    )

    return (request_data(request), cost)

def request_data(request):
    try:
        response = request.execute()
    except HttpError as e:
        stderr.write("API HTTP Error: %s\n" % (e))
        return (dict(), False)
    except exceptions.RequestException as e:
        stderr.write("Request Error: %s\n" % (e))
        return (dict(), False)

    return (response['items'][0], True) # strip request meta data

def save_progress(data):
    with open(TEMPFILE, 'w') as f:
        dump(data, f, indent=4)

def main(quota=False):
    developer_key = read_developer_key(DEVELOPER_KEY_FILE)
    service = build_service_object(API_SERVICE_NAME, API_VERSION, developer_key)

    costs = 0
    data = dict()
    for video_id in video(stdin):
        if quota and costs >= QUOTA_DEFAULT - QUOTA_MIN:
            save_progress(data)
            costs = 0
            sleep(QUOTA_RESET_TIME)

        i = 0
        (video_data, success), cost = request_video_data(service, video_id)
        while not success:
            if i < 5:
                sleep(60)
            elif i > 5:
                stderr.write("Failed retrieving video %s\n" % (video_id))
                break
            else:
                sleep(600)

            (video_data, success), cost = request_video_data(service, video_id)
            i += 1

        if not success:
            continue

        video_data['retrieved_on'] = datetime.today().strftime("%Y-%m-%dT%H:%M:%S")
        costs += cost

        # extract channel ID
        channel_id = video_data['snippet']['channelId']
        if channel_id not in data.keys():
            if quota and costs >= QUOTA_DEFAULT - QUOTA_MIN:
                save_progress(data)
                costs = 0
                sleep(QUOTA_RESET_TIME)

            i = 0
            (channel_data, success), cost = request_channel_data(service, channel_id)
            while not success:
                if i < 5:
                    sleep(60)
                elif i > 5:
                    stderr.write("Failed retrieving channel %s\n" % (channel_id))
                    break
                else:
                    sleep(600)

                (channel_data, success), cost = request_channel_data(service, channel_id)
                i += 1

            if success:
                channel_data['retrieved_on'] = datetime.today().strftime("%Y-%m-%dT%H:%M:%S")
                costs += cost

            channel_data['videos'] = list()

            # add new channel
            data[channel_id] = channel_data

        # add new video to channel
        data[channel_id]['videos'].append(video_data)

    return data

if __name__ == "__main__":
    data = main(quota=True)

    dump(data, stdout, indent=4)
