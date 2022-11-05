# Twitter Archive Builder

----

### Background

Although rarely a prolific one, I first started using Twitter in 2010.

It's unlikely that I've tweeted too much of value, however I am a bit of a [datahoarder](https://www.reddit.com/r/DataHoarder/), and felt that it'd be a shame to lose that content just because Elon Musk buys and tries to run businesses without any understanding for how they works, or earn their money.

So, I decided I to build an archive of my tweets. 

The script in this repo consumes the JSON file created by [twitter-dump](https://github.com/pauldotknopf/twitter-dump) (I have a [dockerised version](https://github.com/bentasker/docker-twitter-dump)) and generates a static HTML archive.

![Tweet Screenshot](Docs/screenshot.png)

It's a hastily hacked together script, originally built for [some other analysis](https://projects.bentasker.co.uk/gils_projects/issue/jira-projects/MISC/5.html).


----

### Usage

Usage is simple, but you will need [`dominate`](https://github.com/Knio/dominate) installed:
```sh
pip3 install dominate
```

Then, call the script and pass it the path to your twitter-dump JSON file as the first and only argument
```sh
./build_mirror.py bentasker.json
```

----

### Limitations

The biggest limitation is that only Tweet text is mirrored - videos and images are not pulled into the archive.

This is because Twitter heavily obfuscates media URLs in the front-end.

That information **is** available via the API, but to access that you need an API token, which requires you to have provided a verified phone number (and I'm [not doing that](https://www.bentasker.co.uk/posts/blog/software-development/dont-require-users-to-provide-valid-phone-numbers.html), especially now).


----

### Avatar Support

As noted above, media links are heavily obfuscated in Twitter's front-end, so user avatars cannot automatically be fetched.

However, tweets really do look quite weird without an avatar attached to them, so there is *some* support built into the eventual archive.

A directory called `avatar` will be created.

If you put a JPG in there, using the user's handle as the filename (e.g. `bentasker.jpg`) then it will be used/displayed in the archive.


----

### Copyright

Copyright (c) 2022 [B Tasker](https://www.bentasker.co.uk/)

Released under BSD 3-clause license, see [LICENSE](LICENSE)
