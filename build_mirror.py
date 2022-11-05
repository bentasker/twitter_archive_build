#!/usr/bin/env python3
#
#
# Read a tweet dump and build a DB
#
# project-management-only/staging#1
#

import influxdb_client
import json
import os
import re
import requests
import sys


CURSES = [
    "fuck",
    "cunt",
    "twat",
    "shit",
    "feck",
    "knob",
    "bollocks", # legally speaking not actually swearing
    "bellend",
    "wazzock",
    "arse",
    "smeg",
    "bugger",
    "fubar",
    "cock",
    "wank"
    ]

CURSES_WHITELIST = [
    "matthancock",
    "parses",
    "hancock",
    "cockup",
    "arsetechnica",
    "daveadcock",
    "parse",
    "cockney",
    "arsenal",
    "hancock-up",
    "charset",
    "parser",
    "swanky"
    ]

def check_for_links(tweet_text):
    ''' Check whether the tweet contains links
    
    '''
    res = re.findall('http(s)?:\/\/([^ ]+)', tweet_text)
    mentions = re.findall('@([^ ]+)', tweet_text)
    photos = re.findall('\/photo\/([0-9]+)', tweet_text)
    
    
    words = tweet_text.split(" ")
    
    o = {
        "has_links" : True,
        "num_links" : len(res),
        "has_mentions" : False,
        "num_mentions" : len(mentions),
        "mentions" : "",
        "has_image" : False,
        "num_images": len(photos),
        "has_swear": False,
        "num_swear": 0,
        "swear_words": "",
        "num_words" : len(words),
        "has_hashtags" : False,
        "num_hashtags" : 0,
        "hashtags" : ""
    }
    
    if o["num_links"] < 1:
        o["has_links"] = False
    
    if o["num_mentions"] > 0:
        o['mentions'] = ','.join(mentions)
        o["has_mentions"] = True
    
    if o["num_images"] > 0:
        o["has_image"] = True
    
    
    # Check my language
    lcase = tweet_text.lower()
    i_said = []
    i_matched = []
    for swearword in CURSES:
        if swearword in lcase:
            use = re.findall("(([a-z0-9\-]+)?" + swearword + "([a-z0-9\-]+)?)", lcase)
            if use and len(use) > 0:
                for usage in use:
                    if usage[0] not in CURSES_WHITELIST:
                        print("You said " + usage[0])
                        i_said.append(usage[0])
                        i_matched.append(swearword)
    
    # Uniquify
    l = list(set(i_said))
    l2 = list(set(i_matched))
    
    if len(l) > 0:
        o["has_swear"] = True
        o["num_swear"] = len(i_said)
        o["swear_words"] = ",".join(l)
        o["matched_swears"] = ",".join(l2)
    
    hashtags = []
    for word in words:
        if word.startswith('#'):
            hashtags.append(word)
    
    c = len(hashtags)
    if c > 0:
        o["has_hashtags"] = True
        o["hashtags"] = ",".join(hashtags)
        o["num_hashtags"] = c
    
    return o
    
    

def handle_embedded_links(tweet_text):
    ''' Identify any t.co URLs and convert them to their full version
    
    Note: this *may* make the tweet longer than actually fits in a tweet
    '''
    
    return re.sub("http(s)?:\/\/t\.co\/([A-Z0-9a-z]+)", get_tco_dest, tweet_text)
    

def get_tco_dest(match_o):
    ''' Place a request to t.co to find out where a given URL redirects to
    
    We only take the first redirect - Twitter will have replaced whatever the 
    tweeter pasted, so we're not concerned with whether it redirects further
    down the line.
    '''
    source_url = match_o.group()
    r = SESSION.head(source_url)
    if "location" not in r.headers:
        print("ERR: Failed to get redirect location for" + source_url)
        return source_url
    
    # Return the redirect target
    return r.headers['location']
    


fh = open(sys.argv[1], 'r')
j = json.load(fh)
fh.close()


INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://127.0.0.1:8086")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "myorg")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "zzzza")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "telegraf")
MEASUREMENT = os.getenv("MEASUREMENT", "tweets")

# Set up the Influx client
client = influxdb_client.InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)

# Instantiate a session so we can use keep-alives
SESSION = requests.session()

# Write in batches
write_api = client.write_api()


# Build a list of users by id
user_list = {}
for user in j['users']:
    user_list["user_" + str(user['id']) ] = {
                    "handle" : user['screen_name'],
                    "name" : user['name']
                }


print("Handling tweets from query {j['query']}")
for tweet in j['tweets']:
    
    # Convert the text
    text = handle_embedded_links(tweet['full_text'])
    link_info = check_for_links(text)
    
    # Build a point
    p = influxdb_client.Point(MEASUREMENT)
    p.tag("id", tweet['id'])
    p.tag("user_id", tweet['user_id'])
    p.tag("user_handle", user_list["user_" + str(tweet['user_id'])]['handle'])
    p.tag("contains_links", link_info["has_links"])
    p.tag("has_mentions", link_info["has_mentions"])
    p.tag("has_image", link_info["has_image"])
    p.tag("has_swear", link_info["has_swear"])
    p.tag("has_hashtags", link_info["has_hashtags"])
    p.field("url", tweet['url'])
    p.field("tweet_text", text)
    p.field("num_links", link_info["num_links"])
    p.field("num_mentions", link_info["num_mentions"])
    p.field("mentions", link_info["mentions"])
    p.field("num_images", link_info["num_images"])
    p.field("num_swear", link_info["num_swear"])
    p.field("swear_words", link_info["swear_words"])
    p.field("num_words", link_info["num_words"])
    p.field("num_hashtags", link_info["num_hashtags"])
    p.field("hashtags", link_info["hashtags"])
    p.time(tweet['created_at'])
    
    write_api.write(bucket=INFLUXDB_BUCKET, record=p)
    
write_api.close()
