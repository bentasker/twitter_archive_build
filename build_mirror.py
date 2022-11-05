#!/usr/bin/env python3
#
#
# Read a tweet dump and build a DB
#
# pip3 install dominate
#

import json
import os
import re
import requests
import sys

from datetime import datetime
from dominate import document
from dominate.tags import *
from dominate.util import raw


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


# Output directory filename
OUTPUT = "output"


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
    
    s = re.sub("http(s)?:\/\/t\.co\/([A-Z0-9a-z]+)", get_tco_dest, tweet_text)
    s = re.sub("http(s)?:\/\/bit\.ly\/([A-Z0-9a-z]+)", get_tco_dest, s)
    return s
    

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
    return f"<a href='{r.headers['location']}' target=_blank rel='nofollow noopener'>{r.headers['location']}</a>"
    

def handle_mentions(tweet_text):
    ''' Identify any t.co URLs and convert them to their full version
    
    Note: this *may* make the tweet longer than actually fits in a tweet
    '''
    
    return re.sub("@([^\ ]+)", replace_mention, tweet_text)


def replace_mention(match_o):
    ''' Receive a username, and replace it with a link)
    '''

    handle = match_o.group().lstrip("@")

    return f"<a href='https://twitter.com/{handle}' rel='nofollow noopener' target=_blank>@{handle}</a>"



def handle_tags(tweet_text):
    ''' Identify hashtags and link them
    
    Note: this *may* make the tweet longer than actually fits in a tweet
    '''
    
    return re.sub("#([^\ ]+)", replace_hashtag, tweet_text)


def replace_hashtag(match_o):
    ''' Receive a username, and replace it with a link)
    '''

    handle = match_o.group().lstrip("#")

    return f"<a href='https://twitter.com/hashtag/{handle}' rel='nofollow noopener' target=_blank>#{handle}</a>"


def build_tweet_page(tweet, user_list):
    ''' Build a HTML page containing the tweet
    '''
    
    tweet_user = user_list["user_" + str(tweet['user_id'])]['handle']
    tweet_date = datetime.strptime(tweet['created_at'], '%Y-%m-%dT%H:%M:%S%z')

    user_link = "https://twitter.com/" + tweet_user
    tweet_link = user_link + f"/status/{tweet['id']}"

    
    tweet_summary = tweet["full_text"][0:80]
    pagetitle = f"{tweet_user}: \"{tweet_summary}\""
    
    with document(title=f"{tweet_user}: \"{pagetitle}\"") as doc:
        link(_href="../style.css", _rel="stylesheet", _type="text/css")
        authordiv = div(_class="author_block")
        authordiv += div(user_list["user_" + str(tweet['user_id'])]['name'], _class="author_name")
        authordiv += div(a("@" + tweet_user, 
                           href=user_link,
                           _target="_blank",
                           _rel="nofollow noopener"
                           ),
                        _class="authorhandle")
        
        div(raw(tweet["text"]), _class="tweettext")
        
        # Metadata
        div(tweet_date.strftime('%d %b %Y %H:%M'), _class="tweetdate")
        div(a("View on Twitter", href=tweet_link), _class="originallink")
        
    
    # TODO: figure out how to handle images 
    
    with open(f"{OUTPUT}/status/{tweet['id']}.html", 'w') as f:
        f.write(doc.render())


def write_css():
    ''' Write CSS to the stylesheet
    '''
    css = '''
    body {padding: 10px; background-color: #f1f6fb}
    a {color: rgb(29, 155, 240)}
    .author_block {padding-bottom: 20px; font-weight: bolder}
    .authorhandle a {color: gray}
    .tweetdate {margin-top: 20px; color: rgb(83, 100, 113); font-style: italic}
    .tweettext {
        border: 1px solid;
        border-radius: 5px;
        padding: 5px;
        max-width: 80%;
        font-size: 1.05em;
    }
    .originallink {font-size: 0.8em; padding-top: 10px;}
    '''
    with open(f"{OUTPUT}/style.css", 'w') as f:
        f.write(css)
    



fh = open(sys.argv[1], 'r')
j = json.load(fh)
fh.close()


# Instantiate a session so we can use keep-alives
SESSION = requests.session()

# Create an output directory
if not os.path.exists(OUTPUT):
    os.mkdir(OUTPUT)

if not os.path.exists(f"{OUTPUT}/status"):
    os.mkdir(f"{OUTPUT}/status")


write_css()

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
    tweet['text'] = handle_embedded_links(tweet['full_text'])
    tweet['text'] = handle_mentions(tweet['text'])
    tweet['text'] = handle_tags(tweet['text'])
    
    link_info = check_for_links(tweet['text'])
    build_tweet_page(tweet, user_list)
    
    # Build a point
    # p = influxdb_client.Point(MEASUREMENT)
    # p.tag("id", tweet['id'])
    # p.tag("user_id", tweet['user_id'])
    # p.tag("user_handle", user_list["user_" + str(tweet['user_id'])]['handle'])
    # p.tag("contains_links", link_info["has_links"])
    # p.tag("has_mentions", link_info["has_mentions"])
    # p.tag("has_image", link_info["has_image"])
    # p.tag("has_swear", link_info["has_swear"])
    # p.tag("has_hashtags", link_info["has_hashtags"])
    # p.field("url", tweet['url'])
    # p.field("tweet_text", text)
    # p.field("num_links", link_info["num_links"])
    # p.field("num_mentions", link_info["num_mentions"])
    # p.field("mentions", link_info["mentions"])
    # p.field("num_images", link_info["num_images"])
    # p.field("num_swear", link_info["num_swear"])
    # p.field("swear_words", link_info["swear_words"])
    # p.field("num_words", link_info["num_words"])
    # p.field("num_hashtags", link_info["num_hashtags"])
    # p.field("hashtags", link_info["hashtags"])
    # p.time(tweet['created_at'])
    

    

