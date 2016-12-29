# -*- coding: UTF-8 -*-

from __future__ import unicode_literals

from flask import Flask,\
                  abort,\
                  jsonify,\
                  make_response,\
                  redirect,\
                  render_template,\
                  request,\
                  url_for
from flask_sqlalchemy import SQLAlchemy
import os
from uuid import uuid4, UUID
import random
from datetime import datetime
import requests
from lxml import html
import base64
import re
from urllib import unquote


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.environ['OPENSHIFT_DATA_DIR'], 'sqlite3.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

base_url = 'http://www.cardkingdom.com/catalog/shop/battle-decks'
google_search = 'https://www.google.fr/search?q=gatherer+'
gatherer_base = 'http://gatherer.wizards.com'
wizards_base = 'http://www.wizards.com/'
gatherer_url = ['/Pages/Card/Details.aspx?multiverseid=',
                '/Pages/Card/Details.aspx?name=',
                'magic/autocard.asp?name=',
                ]

card_re = re.compile(r'^(?P<quantity>[1-9]\d*) +(?P<name>.+)')

colours_order = ['White', 'Blue', 'Black', 'Red', 'Green', 'Colorless', 'Any']
colours_abbrv = ['W', 'U', 'B', 'R', 'G', 'C', 'A']

cardkingdom_currentpage = '//ul[@class="pagination"]/li[@class="active"]'
cardkingdom_decks = '//div[@class="productListWrapper sealedProduct"]'
cardkingdom_thumb = 'span[@class="productThumb"]'
cardkingdom_link = 'span/span[@class="productTitle"]/a'
cardkingdom_title = 'text()'
cardkingdom_details = 'span/span[@class="productDescDetails"]/text()'
google_result = '//h3[@class="r"]/a'
gatherer_cardname = '//span[contains(@id, "subtitleDisplay")]/text()'
gatherer_cardcolour = '//div[contains(@id, "manaRow")]/div[@class="value"]/img'
gatherer_cardtype = '//div[contains(@id, "typeRow")]/div[@class="value"]/text()'
gatherer_cardimg = '//img[contains(@id, "cardImage")]'

class BattleDecks(db.Model):
    __tablename__ = 'battledecks'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    name = db.Column(db.Text)
    url = db.Column(db.Text)
    desc = db.Column(db.Text)
    thumb = db.Column(db.Text)
    colour = db.Column(db.String(7))
    version = db.Column(db.Integer)
    active = db.Column(db.Boolean)

    def __init__(self, name, url, desc, thumb, colour='', version=1, active=True):
        self.timestamp = datetime.now()
        self.name = name
        self.url = url
        self.desc = desc
        self.thumb = thumb
        self.colour = colour
        self.version = version
        self.active = active

    def __repr__(self):
        return 'Deck %s, %s, %s, %s, %s, %s, %s\n' % (self.name,
                                                      self.colour,
                                                      self.timestamp,
                                                      self.active,
                                                      self.url,
                                                      self.desc,
                                                      self.thumb)

class UniqueCards(db.Model):
    __tablename__ = 'uniquecards'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    colour = db.Column(db.String(7))
    type = db.Column(db.Text)
    basic = db.Column(db.Boolean)
    image = db.Column(db.Text)

    def __init__(self, name, colour, type, basic, image):
        self.name = name
        self.colour = colour
        self.type = type
        self.basic = basic
        self.image = image

    def __repr__(self):
        return 'Card %s (%s): %s\n' % (self.name,
                                       self.colour,
                                       self.image)

class DeckCards(db.Model):
    __tablename__ = 'deckcards'
    id = db.Column(db.Integer, primary_key=True)
    card = db.Column(db.Integer)
    deck = db.Column(db.Integer)
    quantity = db.Column(db.Integer)

    def __init__(self, card, deck, quantity):
        self.card = card
        self.deck = deck
        self.quantity = quantity

    def __repr__(self):
        return '%d cards %d in deck %d\n' % (self.quantity,
                                             self.card,
                                             self.deck)


@app.before_request
def redirect_https():
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)

@app.before_request
def csrf_protect():
    if request.method == 'POST':
        token = request.cookies.get('_csrf_token')
        if not token or token != request.form.get('_csrf_token'):
            abort(403)


@app.route('/')
def show_model():
    session = request.cookies.get('session')
    if session is None:
        session = str(uuid4())
    try:
        UUID(session)
    except:
        return problem('corrupted session', None, None, session)
    nick = ''
    nickDB = Nicknames.query.filter_by(session=session).first()
    if nickDB:
        nick = nickDB.nick
    req_id = str(uuid4())
    model_id = choose_model(session)
    if model_id == -1:
        response = make_response(render_template('congrats.html',
                                                 max_models=max_models))
        response.set_cookie('session', session)
        return response

    cleanup_requests()

    model = generate_model(model_id)
    reqDB = ActiveRequest(req_id, session, model_id)
    db.session.add(reqDB)
    db.session.commit()
    scores = kappa_average(session)
    n_others = len(scores)
    score = sum(scores) / n_others * 100
    csrf_token = uuid4()
    response = make_response(render_template('model.html',
                                             model=model,
                                             model_id=model_id,
                                             req_id=req_id,
                                             score='%.2f' % score,
                                             n_others=n_others,
                                             session=session,
                                             csrf_token=csrf_token))
    response.set_cookie('session', session)
    response.set_cookie('nick', nick)
    response.set_cookie('_csrf_token', csrf_token)
    return response

def update_db():
    page_url = base_url
    active_decks = []
    while True:
        page = requests.get(page_url)
        tree = html.fromstring(page.content)
        decks = tree.xpath(cardkingdom_decks)
        for deck in decks:
            a = deck.xpath(cardkingdom_link)[0]
            title = a.xpath('text()')[0].split(':', 1)[1].strip()
            active_decks.append(title)
            res = BattleDecks.query.filter_by(name=title).first()
            if res:
                continue

            print 'Adding deck %s' % title
            thumb = deck.xpath(cardkingdom_thumb)[0].xpath('a/img')[0].get('src')
            thumb = requests.get(thumb)
            thumb = base64.b64encode(thumb.content)
            url = a.get('href')
            details = deck.xpath(cardkingdom_details)
            desc = ''
            cards = []
            uniquecards = []
            dbDeck = BattleDecks(title, url, desc, thumb)
            db.session.add(dbDeck)
            db.session.commit()
            for d in details:
                m = re.search(card_re, d.strip())
                if m:
                    card, uniquecard = make_card(dbDeck.id,
                                                 m.group('name'),
                                                 int(m.group('quantity')))
                    cards.append(card)
                    uniquecards.append(uniquecard)
                else:
                    desc += d
            dbDeck.colour = combine_colours(uniquecards)
            db.session.commit()

        next_li = tree.xpath(cardkingdom_currentpage)[0].getnext()
        if next_li is None:
            break
        page_url = next_li.xpath('a')[0].get('href')
    for deck in BattleDecks.query.all():
        if deck.name in active_decks:
            deck.active = True
        else:
            deck.active = False

def make_card(deck, name, quantity):
    search = requests.get(google_search + '+'.join(name.split()))
    tree = html.fromstring(search.content)
    href = ''
    for res in tree.xpath(google_result):
        href = res.get('href')
        href = unquote(href[7:].split('&')[0])
        if href.startswith(gatherer_base) or href.startswith(wizards_base):
            dobreak = False
            for url in gatherer_url:
                if url in href:
                    dobreak = True
                    break
            if dobreak:
                break
        href = ''

    info = requests.get(href)
    infotree = html.fromstring(info.content)
    cardname = infotree.xpath(gatherer_cardname)[0].strip()
    dbCard = UniqueCards.query.filter_by(name=cardname).first()
    if dbCard is None:
        cardcolour = set()
        for colour in infotree.xpath(gatherer_cardcolour):
            cardcolour.add(colour.get('alt'))
        cardcolour = filter_colour(cardcolour)
        cardtype = infotree.xpath(gatherer_cardtype)[0].split('—')[0].strip()
        cardtype, basic = filter_type(cardtype)
        cardimage = infotree.xpath(gatherer_cardimg)[0].get('src')
        cardimage = gatherer_base + cardimage[5:]
        dbCard = UniqueCards(cardname, cardcolour, cardtype, basic, cardimage)
        db.session.add(dbCard)
        db.session.commit()
        print '  New card: %s' % cardname
    dbDeckCard = DeckCards(dbCard.id, deck, quantity)
    db.session.add(dbDeckCard)
    return dbDeckCard, dbCard

def filter_colour(colours):
    to_discard = set()
    for colour in colours:
        try:
            int(c)
            to_discard.add(c)
            colours.add('Any')
        except:
            continue
    colours = colours - to_discard
    text = ''
    for w, a in zip(colours_order, colours_abbrv):
        if w in colours:
            text += a
    return text

def filter_type(types):
    basic = False
    if types.startswith('Legend'):
        types = types.split(None, 1)[1]
    if types.startswith('Basic'):
        types = types.split(None, 1)[1]
        basic = True
    if 'Creature' in types:
        types = 'Creature'
    else:
        types = types.split()[0]
    return types, basic

def combine_colours(cards):
    colours = set()
    for card in cards:
        for c in card.colour:
            colours.add(c)
    text = ''
    for c in colours_abbrv:
        if c in colours:
            text += c
    return text

def check_decks():
    for deck in BattleDecks.query.all():
        n = 0
        for card in DeckCards.query.filter_by(deck=deck.id):
            n += card.quantity
        if not n == 60:
            print 'problem with deck %s: %d cards' % (deck.name, n)


if __name__ == '__main__':
    print 'Checking for new decks'
    update_db()

