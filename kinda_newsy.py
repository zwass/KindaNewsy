import random
import os
import re
import json
import time

from bs4 import BeautifulSoup
import requests
import tweepy

MOSTVIEWED_URL = "http://api.nytimes.com/svc/mostpopular/v2/mostviewed/all-sections/1.json?api-key=%s"

NYT_API_KEY = os.environ.get('NYT_API_KEY')
TWITTER_CONSUMER_KEY = os.environ.get('TWITTER_CONSUMER_KEY')
TWITTER_CONSUMER_SECRET = os.environ.get('TWITTER_CONSUMER_SECRET')
TWITTER_ACCESS_KEY = os.environ.get('TWITTER_ACCESS_KEY')
TWITTER_ACCESS_SECRET = os.environ.get('TWITTER_ACCESS_SECRET')
2
class MarkovGenerator:
    """Uses first order Markov Chains to generate new text from seed text

    Tries to create more coherent text by remembering which words
    began sentences in the original text, and using those for
    generated sentences."""

    def __init__(self, text):
        self.text = text
        self.mappings = {}
        self.openers = []
        self._generate_mappings()

    def _generate_mappings(self):
        """Generates the markov chain using input text"""
        words = self.text.split()
        for i in range(len(words) - 1):
            word = words[i].strip()
            next_word = words[i+1].strip()

            #Check whether this is a sentence opener
            if word[-1] == ".":
                self.openers.append(next_word)

            #add it to our markov mapping
            if word in self.mappings:
                self.mappings[word].append(next_word)
            else:
                self.mappings[word] = [next_word]

    def generate_text(self, min_length=100,):
        """Generates text from the markov chain mappings"""
        output = ""
        word = random.choice(self.openers)
        i = 0
        while len(output) + len(word) < min_length or word[-1] != ".":
            output += word + " "
            try:
                word = random.choice(self.mappings[word])
            except KeyError:
                #there was no string following this
                word = random.choice(self.mappings.keys())
            i += 1
        output += word
        return output

class TimesArticle:
    """Class for retrieving and parsing NYT articles"""
    def __init__(self, data):
        self.url = data['url']
        self.keywords = data['adx_keywords'].split(";")
        self.text = None

    def get_text(self):
        """Returns the text of the article, with as much HTML stripped as
        possible

        If this article has already been retrieved, returns the cached version"""
        if self.text:
            return self.text
        else:
            article_request = requests.get(self.url)
            if article_request.status_code != requests.codes.ok:
                article_request.raise_for_status()
            article_html = article_request.content
            self.text = self._get_article_body(article_html)
            return self.text

    def _get_article_body(self, article_html):
        """Extract the article body text from the full html"""
        soup = BeautifulSoup(article_html, "lxml")
        body_div = soup.findAll("div", "articleBody")[1]
        article_body = " ".join([p.renderContents().strip()
                                 for p in body_div.findAll("p")])
        #remove any extraneous html entities
        article_body = re.sub("<.*?>", "", article_body)
        return article_body



class TopArticlesGetter:
    """Retrieves top articles using the NYT API

    A valid API key must be provided"""
    def __init__(self, api_key):
        self.request_string =  MOSTVIEWED_URL % (api_key)

    def get_article_list(self):
        """Returns a list of TimesArticle objects for the top articles"""
        r = requests.get(self.request_string)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()
        rdata = json.loads(r.text)
        return [TimesArticle(article_data) for article_data in rdata['results']]

class TwitterBot:
    """Deals with the tweeting side of things"""
    def __init__(self):
        auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        auth.set_access_token(TWITTER_ACCESS_KEY, TWITTER_ACCESS_SECRET)
        self._api = tweepy.API(auth)

    def tweet(self):
        articles = TopArticlesGetter(NYT_API_KEY).get_article_list()
        tweet_contents = None
        while tweet_contents is None:
            try:
                source = random.choice(articles)
                generator = MarkovGenerator(source.get_text())
                tweet_contents = generator.generate_text()
                while len(tweet_contents) > 140:
                    tweet_contents = generator.generate_text()
            except:
                tweet_contents = None
        self._api.update_status(tweet_contents)

def sleep_minutes(minutes):
    time.sleep(minutes * 60)

if __name__ == "__main__":
    bot = TwitterBot()
    while True:
        bot.tweet()
        sleep_time = 30 + random.randint(0, 300)
        sleep_minutes(sleep_time)