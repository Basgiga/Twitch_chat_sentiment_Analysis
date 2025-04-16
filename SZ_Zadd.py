import asyncio
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
from flask import Flask, render_template, request, jsonify, session
import plotly.express as px
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from twitchio.ext import commands
import threading
#from transformers import pipeline
#from googletrans import Translator
import networkx as nx
import time


nltk.downloader.download('vader_lexicon')
app = Flask(__name__)

# Twitch API
CLIENT_ID = '-'
CLIENT_SECRET = '-'

app.secret_key = 'your_secret_key'

sentiment_counts = {
    "Positive": 0,
    "Negative": 0,
    "Neutral": 0
}
twitch_lexicon = {
    "XD": "Positive",
    "LULW": "Positive",
    "LUL": "Positive",
    "OMEGALUL": "Positive",
    "KEKW": "Positive",
    ":(": "Negative",
    "FeelsBadMan": "Negative",
    "D:": "Negative",
    "wtf": "Negative",
    "lol": "Positive",
    "LOL": "Positive",
    "mhm": "Neutral",
    "yeah": "Positive",
    "Yeah": "Positive",
    "HUH": "Positive",
    "YEAH": "Positive",
    "yes": "Positive",
    "no": "Positive",
    "Sadge": "Negative",
    "xdd": "Positive"
}
boty = ("moobot","nightbot","streamelements")
dict_uzyt = {}


last_update_time = time.time()
def create_graph_mentions():
    G = nx.DiGraph()
    for kto, ile in dict_uzyt.items():
        uz1, uz2 = kto.split("<-")
        _,uz1 = uz1.split('@')
        uz1 = uz1.lower()
        uz2 = uz2.lower()
        #print(uz1,uz2)
        if uz1 not in G.nodes():
            G.add_node(uz1)
        if uz2 not in G.nodes():
            G.add_node(uz2)
        G.add_edge(uz2, uz1, weight=ile)
    last_update_time = time.time()
    return G


def analiza_sentymentu(text):
    sia = SentimentIntensityAnalyzer()

    sentiment_score = sia.polarity_scores(text)['compound']
    if sentiment_score > 0.1:
        return "Positive"
    elif sentiment_score < -0.1:
        return "Negative"
    else:
        return "Neutral"
"""
def analiza_sentymentu_pl(text):
    nlp = pipeline("sentiment-analysis", model="bardsai/twitter-sentiment-pl-base")
    sentiment_score = nlp(text)
    if sentiment_score > 0.1:
        return "Pozytywny"
    elif sentiment_score < -0.1:
        return "Negatywny"
    else:
        return "Neutralny"
"""
class Bot(commands.Bot):

    def __init__(self, token, client_id, channel_name):
        super().__init__(token=token, prefix='!', initial_channels=[channel_name])
        self.channel_name = channel_name

    async def event_message(self, message):
        if message.author.name.lower() not in boty:
            slowa = message.content.split(' ')
            #print(slowa,message.author.name)
            for slowo in slowa:
                if '@' in slowo:
                    saved = slowo + '<-' + message.author.name
                    #print(saved)
                    if saved not in dict_uzyt:
                        dict_uzyt[saved] = 1
                    else:
                        dict_uzyt[saved] += 1
            if len(slowa) >1:
                sentiment = analiza_sentymentu(message.content)
                sentiment_counts[sentiment] += 1
                print(f"Received message: {message.content} - Sentiment: {sentiment}, length: {len(message.content)}")
            elif message.content in twitch_lexicon:
                sentiment_counts[twitch_lexicon[message.content]] += 1
                print(f"Received LEXICON: {message.content} - Sentiment: {twitch_lexicon[message.content]}, length: {len(message.content)}")
        await self.handle_commands(message)

    async def event_ready(self):
        print(f"Bot connected to {self.channel_name}!")


async def authenticate_twitch(channel_name):
    global twitch
    twitch = await Twitch(CLIENT_ID, CLIENT_SECRET)
    target_scope = [AuthScope.CHAT_READ]
    auth = UserAuthenticator(twitch, target_scope, force_verify=False)
    token, refresh_token = await auth.authenticate()
    await twitch.set_user_authentication(token, target_scope, refresh_token)
    await twitch.authenticate_app([AuthScope.CHAT_READ])

    bot = Bot(token=token, client_id=CLIENT_ID, channel_name=channel_name)
    await bot.start()


def start_bot_in_thread(channel_name):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(authenticate_twitch(channel_name))


@app.route('/graph_data', methods=['GET'])
def graph_data():
    G = create_graph_mentions()
    data = nx.node_link_data(G)
    return jsonify(data=data)

@app.route('/', methods=['GET', 'POST'])
async def index():
    if request.method == 'POST':
        try:
            channel_name = request.form['channel_name']

            threading.Thread(target=start_bot_in_thread, args=(channel_name,), daemon=True).start()

            labels = list(sentiment_counts.keys())
            values = list(sentiment_counts.values())
            fig = px.pie(names=labels, values=values, title="Analiza sentymentu czatu")
            graph_html = fig.to_html(full_html=False)

            return render_template('index1.html', channel_name=channel_name, graph_html=graph_html)

        except Exception as e:
            print(f"Error: {e}")
            return "An error occurred while processing your request.", 500

    return render_template('index1.html')


@app.route('/update_sentiment', methods=['GET'])
def update_sentiment():
    labels = list(sentiment_counts.keys())
    values = list(sentiment_counts.values())
    return jsonify(labels=labels, values=values)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
