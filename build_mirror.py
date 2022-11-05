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
    "swanky",
    "fuckmusk8",
    "shitkemisays",
    "isnortarsenic",
    "scunthorpe"
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
    ''' Identify mentions and link out to the mentioned user
    
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
    ''' Receive a hashtag and replace it with a link)
    '''

    handle = match_o.group().lstrip("#")

    return f"<a href='https://twitter.com/hashtag/{handle}' rel='nofollow noopener' target=_blank>#{handle}</a>"


def build_tweet_page(tweet, user_list):
    ''' Build a HTML page containing the tweet
    '''
    
    tweet_user = user_list["user_" + str(tweet['user_id'])]['handle']
    tweet_date = datetime.strptime(tweet['created_at'], '%Y-%m-%dT%H:%M:%S%z')
    tweet_year = tweet_date.strftime('%Y')

    user_link = "https://twitter.com/" + tweet_user
    tweet_link = user_link + f"/status/{tweet['id']}"

    
    tweet_summary = tweet["full_text"][0:80]
    pagetitle = f"{tweet_user}: \"{tweet_summary}\""
    
    with document(title=f"{tweet_user}: \"{pagetitle}\"") as doc:
        link(_href="../style.css", _rel="stylesheet", _type="text/css")
        
        a(tweet_year, href=f"../{tweet_year}.html", _class="yearindex")
        
        authordiv = div(_class="author_block")
        authordiv += img(src=f"../avatar/{tweet_user}.jpg",
                         style="display: none",
                         _class="authorimg",
                         onload="this.style.display = 'inline-block'"
            )
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
    script(src="../static.js", type="text/javascript")
    
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
   
    .tweet {    
        padding-top: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid #aaa2a2;
    }
    
    .tweet a {
        text-decoration: none;
        color: #000;
    }
    
    .viewtweetlink {
        display: block;
        color: rgb(29, 155, 240) !important;
        margin-top: 5px;
        font-size: 0.8em;
    }
    
    .tweet .tweetdate {
        margin-top: 0;
        font-size: 0.8em;
    }
    
    .year {
        text-decoration: none
    }
    
    .authorimg {
        float: left;
        margin-right: 10px;
        padding-top: 2px;
    }
    
    .yearindex {
        margin-bottom: 20px;
        display: block;
    }
    '''
    with open(f"{OUTPUT}/style.css", 'w') as f:
        f.write(css)
    

def writeJS():
    js = """
    """
    with open(f"{OUTPUT}/static.js", 'w') as f:
        f.write(js)
    


def writeTweetIndex(tweet, j, user_list):
    ''' Write a tweet onto the relevant yearly index page
    '''
    
    # Set some vars
    linktext = tweet['full_text']
    linkdest = f"status/{tweet['id']}.html"
    tweet_date = datetime.strptime(tweet['created_at'], '%Y-%m-%dT%H:%M:%S%z')
    tweet_user = user_list["user_" + str(tweet['user_id'])]['handle']
    
    year = tweet_date.strftime('%Y')
    
    # Create the object if it doesn't exist
    if year not in YEARS:
       YEARS[year] = {}
       YEARS[year]['count'] = 0
       YEARS[year]['doc'] = document(title=f"{year} Tweet Archive for query {j['query']}")
       YEARS[year]['doc'] += link(_href="style.css", _rel="stylesheet", _type="text/css")
       YEARS[year]['doc'] += h1(f"{year} Tweet Archive for query {j['query']}")
       YEARS[year]['doc'] += a("Index", href="index.html")
       
    tdiv = div(_class="tweet")
    tdiv += img(src=f"avatar/{tweet_user}.jpg",
                         style="display: none",
                         _class="authorimg",
                         onload="this.style.display = 'inline-block'"
            )
    tdiv += a(linktext, href=linkdest)
    tdiv += div(tweet_date.strftime('%d %b %Y %H:%M'), _class="tweetdate")
    tdiv += a("View Tweet", href=linkdest, _class="viewtweetlink")

    YEARS[year]['doc'] += tdiv
    YEARS[year]['count'] += 1


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

if not os.path.exists(f"{OUTPUT}/avatar"):
    os.mkdir(f"{OUTPUT}/avatar")

# Stats object
global_stats = {
    "total" : 0,
    "has_mentions" : 0,
    "has_swear" : 0,
    "has_images" : 0,
    "has_hashtags" : 0,
    "has_links" : 0,
    "num_mentions" : 0,
    "num_swear" : 0,
    "num_images" : 0,
    "num_hashtags" : 0,
    "num_links" : 0,
    "hashtags" : set(),
    "profanities": set()
    }


# Create the CSS file
write_css()
writeJS()

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
    
    link_info = check_for_links(tweet['full_text'])
    build_tweet_page(tweet, user_list)
    
    global_stats["total"] += 1
    
    if link_info["has_swear"]:
        global_stats["has_swear"] += 1
        global_stats["num_swear"] += link_info["num_swear"]
        y = [global_stats["profanities"].add(z) for z in link_info["swear_words"].split(",")]
    
    if link_info["has_mentions"]:
        global_stats["has_mentions"] += 1
        global_stats["num_mentions"] += link_info["num_mentions"]
        
    if link_info["has_image"]:
        global_stats["has_images"] += 1
        global_stats["num_images"] += link_info["num_images"]

    if link_info["num_links"] > 0:
        global_stats["has_links"] += 1
        global_stats["num_links"] += link_info["num_links"]

    if link_info["has_hashtags"]:
        global_stats["has_hashtags"] += 1
        global_stats["num_hashtags"] += link_info["num_hashtags"]
        y = [global_stats["hashtags"].add(z) for z in link_info["hashtags"].split(",")]
        
        

stats = f"""
Archive Stats
================

Number of tweets: {global_stats['total']}

Stats
* {global_stats['has_mentions']} tweets contain a total of {global_stats['num_mentions']} mentions.
* {global_stats['has_swear']} tweets contain a total of {global_stats['num_swear']} profanities.
* {global_stats['has_hashtags']} tweets contain a total of {global_stats['num_hashtags']} hashtags.
* {global_stats['has_links']} tweets contain a total of {global_stats['num_links']} links.
* {global_stats['has_images']} tweets reference a total of {global_stats['num_images']} images.

"""

print(stats)


# Create the Index Page

# This looks quite messy without use of contexts. The problem is, we make calls out to write
# into other pages. If you do those calls from within a context, dominator will write into *both* pages
YEARS={}
doc = document(title=f"Tweet Archive for query {j['query']}")
doc += link(_href="style.css", _rel="stylesheet", _type="text/css")
doc += h1(f"Tweet Archive for query {j['query']}")

stats = div(_class="statsdiv")
stats += h3("Archive Stats")
stats += li(f"Number of tweets: {global_stats['total']}")
stats += li(f"{global_stats['has_mentions']} tweets contain a total of {global_stats['num_mentions']} mentions.")
stats += li(f"{global_stats['has_swear']} tweets contain a total of {global_stats['num_swear']} profanities.")
stats += li(f"{global_stats['has_hashtags']} tweets contain a total of {global_stats['num_hashtags']} hashtags.")
stats += li(f"{global_stats['has_links']} tweets contain a total of {global_stats['num_links']} links.")
stats += li(f"{global_stats['has_images']} tweets reference a total of {global_stats['num_images']} images.")

doc += stats

# Add links to tweets
doc += hr()
doc += h3("Tweet Archives")

for tweet in j['tweets']:
    writeTweetIndex(tweet, j, user_list)

# Iterate over the years and write out their pages, and a link to them
for year in YEARS:
    doc += li(a(f"{year} ({YEARS[year]['count']} tweets)", href=f"{year}.html", _class="year"))
    with open(f"{OUTPUT}/{year}.html", 'w') as f:
        f.write(YEARS[year]['doc'].render())


# Write out
with open(f"{OUTPUT}/index.html", 'w') as f:
    f.write(doc.render())

# I'm curious
with open(f"{OUTPUT}/profanities.txt", 'w') as f:
    f.write('\n'.join(sorted(global_stats['profanities'])))
