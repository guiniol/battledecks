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
from sqlalchemy import desc
import os
import sys
from subprocess import Popen, PIPE
from uuid import uuid4, UUID
import random
from datetime import datetime, timedelta
import requests
from lxml import html
import base64
import re
from urllib import unquote, quote


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.environ['OPENSHIFT_DATA_DIR'], 'sqlite3.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

base_url = 'http://www.cardkingdom.com/catalog/shop/battle-decks'
google_search = 'https://www.google.fr/search?q=gatherer+'
gatherer_base = 'http://gatherer.wizards.com'
wizards_base = 'http://www.wizards.com'
gatherer_url = [gatherer_base + '/Pages/Card/Details.aspx?multiverseid=',
                gatherer_base + '/Pages/Card/Details.aspx?name=',
                wizards_base + '/magic/autocard.asp?name=',
                ]
gatherer_ext_url = 'http://gatherer.wizards.com/Pages/Card/' 

card_re = re.compile(r'^(?P<quantity>[1-9]\d*) +(?P<name>.+)')

n_cards = 60
colours_order = ['White', 'Blue', 'Black', 'Red', 'Green', 'Colorless', 'Any']
colours_abbrv = ['W', 'U', 'B', 'R', 'G', 'C', 'A']
types_order = ['Creature',
               'Artifact',
               'Enchantment',
               'Planeswalker',
               'Instant',
               'Sorcery',
               'Land']
card_lang = 'English'

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
gatherer_cardaltname = '//div[contains(@id, "nameRow")]/div[@class="value"]/text()'
gatherer_language = '//a[contains(@id,"LanguagesLink")]'
gatherer_english = '//table[@class="cardList"]/tr/td/a[contains(@id, "cardTitle")]'


class BattleDecks(db.Model):
    __tablename__ = 'battledecks'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    name = db.Column(db.Text)
    url = db.Column(db.Text)
    description = db.Column(db.Text)
    thumb = db.Column(db.Text)
    colour = db.Column(db.String(7))
    version = db.Column(db.Integer)
    active = db.Column(db.Boolean)

    def __init__(self, name, url, description, thumb, colour='', version=1, active=True):
        self.timestamp = datetime.now()
        self.name = name
        self.url = url
        self.description = description
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
                                                      self.description,
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

class TranslationCards(db.Model):
    __tablename__ = 'translationcards'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    cardid = db.Column(db.Integer)
    language = db.Column(db.String(2))

    def __init__(self, name, cardid, language='ck'):
        self.name = name
        self.cardid = cardid
        self.language = language

    def __repr__(self):
        return 'Card %s is %d in %s\n' % (self.name, self.cardid, self.language)


@app.before_request
def redirect_https():
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)


@app.route('/')
def show_decks():
    decks = []
    shown = set()
    for deck in BattleDecks.query.order_by(desc(BattleDecks.timestamp)).all():
        cards = {}
        for card in DeckCards.query.filter_by(deck=deck.id).all():
            ucard = UniqueCards.query.filter_by(id=card.card).first()
            cards.setdefault(ucard.type, []).append({'name': ucard.name,
                                                     'quantity': str(card.quantity),
                                                     'image': ucard.image,})
        cards_txt = ''
        for types in types_order:
            if types in cards:
                cards_txt += '<li class="cardtypelist"><span class="cardtype">' + types + '</span>\n'
                cards_txt += '<table class="cardlist">\n'
                for card in sorted(cards[types], key=lambda x: x['name']):
                    cards_txt += '<tr class="carddesc">'
                    cards_txt += '<td class="cardquantity">' + card['quantity'] + '</td>'
                    cards_txt += '<td class="cardname"' +\
                                 'oli="' + card['image'] + '" ' +\
                                 'onmouseover="show(this)" ' +\
                                 'onmouseout="hide(this)"' +\
                                 '>' + card['name'] + '</td>'
                    cards_txt += '</tr>\n'
                cards_txt += '</table></li>\n'
        colours = ''
        for c in deck.colour:
            if c != 'A':
                colours += '<img src="' +\
                           url_for('static', filename='img/' + c + '.svg') +\
                           '" class="manasymbol"/>'
        old = False
        if deck.name in shown:
            old = True
        decks.append((deck.name,
                      str(deck.id),
                      old,
                      deck.thumb,
                      deck.url,
                      deck.timestamp.date(),
                      deck.description,
                      deck.colour,
                      colours,
                      deck.version,
                      deck.active,
                      cards_txt))
        shown.add(deck.name)
    response = make_response(render_template('list.html', decks=decks))
    return response

@app.route('/export/<int:deckid>')
def export(deckid):
    deck = BattleDecks.query.filter_by(id=deckid).first()
    decktxt = deck_txt(deckid)

    response = make_response(decktxt)
    response.headers[bytes('Content-Disposition')] = bytes(('attachment; filename="' + deck.name + '-v' + str(deck.version) + '.txt"').encode('utf-8'))
    response.mimetype = 'text/plain'
    return response

@app.route('/exports/')
def exports():
    decks = request.args.getlist('id')
    merge = request.args.get('merge')
    nobasic = request.args.get('nobasic')

    basic = True
    if nobasic == '1':
        basic = False

    decktxt = ''
    if merge == '1':
        cards = {}
        names = ''
        for deck in decks:
            names += BattleDecks.query.filter_by(id=deck).first().name
            names += ' & '
            for card in DeckCards.query.filter_by(deck=deck).all():
                ucard = UniqueCards.query.filter_by(id=card.card).first()
                if (not basic) and ucard.basic:
                    continue
                cards[ucard.name] = cards.get(ucard.name, 0) + card.quantity
        decktxt += names[:-3] + '\r\n\r\n'
        for card, quantity in sorted(cards.items(), key=lambda x: x[0]):
            decktxt += str(quantity) + ' ' + card + '\r\n'
    else:
        for deck in decks:
            decktxt += deck_txt(deck, basic)
            decktxt += '\r\n'

    response = make_response(decktxt)
    response.headers[bytes('Content-Disposition')] = bytes(('attachment; filename="battledecks.txt"').encode('utf-8'))
    response.mimetype = 'text/plain'
    return response

def deck_txt(deckid, basic=True):
    deck = BattleDecks.query.filter_by(id=deckid).first()
    decktxt = deck.name + '\r\n'
    decktxt += deck.url + '\r\n'
    decktxt += deck.description + '\r\n'

    cards = {}
    for card in DeckCards.query.filter_by(deck=deckid).all():
        ucard = UniqueCards.query.filter_by(id=card.card).first()
        if (not basic) and ucard.basic:
            continue
        cards.setdefault(ucard.type, []).append({'name': ucard.name,
                                                 'quantity': card.quantity})
    for types in types_order:
        if types in cards:
            for card in sorted(cards[types], key=lambda x: x['name']):
                decktxt += str(card['quantity']) + ' ' + card['name'] + '\r\n'

    return decktxt

def update_db():
    page_url = base_url
    active_decks = []
    buf = ''
    buf += print_log('Checking decks')
    ok_decks = []
    while True:
        page = requests.get(page_url)
        tree = html.fromstring(page.content)
        decks = tree.xpath(cardkingdom_decks)
        for deck in decks:
            a = deck.xpath(cardkingdom_link)[0]
            title = a.xpath('text()')[0].split(':', 1)[1].strip()
            thumb = deck.xpath(cardkingdom_thumb)[0].xpath('a/img')[0].get('src')
            thumb = requests.get(thumb)
            thumb = base64.b64encode(thumb.content)
            url = a.get('href')
            details = deck.xpath(cardkingdom_details)
            description = ''
            uniquecards = {}
            check = 0
            for d in details:
                m = re.search(card_re, d.strip())
                if m:
                    quantity = int(m.group('quantity'))
                    card = make_card(m.group('name'))
                    uniquecards[card.id] = quantity
                    check += quantity
                else:
                    description += d
            if check != n_cards:
                buf += print_log(' -> Deck %s is incomplete (%d), skipping' % (title, check))
                continue

            old_deck = BattleDecks.query.filter_by(name=title)\
                                        .order_by(desc(BattleDecks.version))\
                                        .first()
            if old_deck:
                is_new = False
                for card in DeckCards.query.filter_by(deck=old_deck.id):
                    if (card.card not in uniquecards) or\
                       (uniquecards[card.card] != card.quantity):
                        is_new = True
                        buf += print_log(' -> Deck %s has a new version: v%s' % (title, old_deck.version + 1))
                        break
            else:
                is_new = True
                buf += print_log(' -> Deck %s is new' % title)

            if is_new:
                dbDeck = BattleDecks(title, url, description, thumb)
                dbDeck.colour = combine_colours(uniquecards)
                if old_deck:
                    dbDeck.version = old_deck.version + 1
                db.session.add(dbDeck)
                db.session.commit()
                for card, quantity in uniquecards.items():
                    dbDeckCard = DeckCards(card, dbDeck.id, quantity)
                    db.session.add(dbDeckCard)
                active_decks.append(dbDeck.id)
            else:
                ok_decks.append(title)
                active_decks.append(old_deck.id)

            db.session.commit()

        next_li = tree.xpath(cardkingdom_currentpage)[0].getnext()
        if next_li is None:
            break
        page_url = next_li.xpath('a')[0].get('href')

    for deck in BattleDecks.query.all():
        if deck.id in active_decks:
            deck.active = True
        else:
            deck.active = False
    db.session.commit()

    buf += print_log('Decks up to date:')
    for deck in ok_decks:
        buf += print_log(' -> %s' % deck)

    return buf

def add_from_file(filename, date):
    diff = timedelta(seconds=1)
    title = ''
    url = ''
    uniquecards = {}
    check = 0

    with open(filename, 'r') as fd:
        for line in fd.readlines():
            if line == '\n':
                if check != n_cards:
                    print ' -> Deck is incomplete (%d), skipping' % check
                    title = ''
                    url = ''
                    uniquecards = {}
                    check = 0
                    continue

                url = url.strip()
                is_new = []
                version = 0
                thumb = ''
                description = ''
                o_deck = None
                for old_deck in BattleDecks.query\
                                           .filter_by(name=title)\
                                           .order_by(BattleDecks.version)\
                                           .all():
                    version = max(version, old_deck.version)
                    thumb = old_deck.thumb
                    description = old_deck.description
                    if url == '':
                        url = old_deck.url
                    this_new = True
                    for card in DeckCards.query.filter_by(deck=old_deck.id):
                        if (card.card not in uniquecards) or\
                           (uniquecards[card.card] != card.quantity):
                            this_new = False
                            break
                    is_new.append(this_new)
                    if this_new:
                        o_deck = old_deck

                version += 1

                if len(is_new) == []:
                    print ' -> Deck is new'
                    is_new = True
                elif True in is_new:
                    is_new = False
                else:
                    print ' -> Deck has a new version: v%s' % (version)
                    is_new = True

                if is_new:
                    dbDeck = BattleDecks(title, url, description, thumb)
                    dbDeck.colour = combine_colours(uniquecards)
                    dbDeck.version = version
                    dbDeck.timestamp = date
                    db.session.add(dbDeck)
                    db.session.commit()
                    for card, quantity in uniquecards.items():
                        dbDeckCard = DeckCards(card, dbDeck.id, quantity)
                        db.session.add(dbDeckCard)
                else:
                    if o_deck.timestamp > date:
                        o_deck.timestamp = date
                    print ' -> Deck is up to date'

                db.session.commit()

                date = date - diff
                title = ''
                url = ''
                uniquecards = {}
                check = 0
                continue

            if title == '':
                title = line.strip()
                print 'Checking deck %s' % title
                continue

            if url == '':
                url = line
                continue

            m = re.search(card_re, line.strip())
            quantity = int(m.group('quantity'))
            card = make_card(m.group('name'))
            uniquecards[card.id] = quantity
            check += quantity

def make_card(name):
    trCard = TranslationCards.query.filter_by(name=name).first()
    if trCard:
        return UniqueCards.query.filter_by(id=trCard.cardid).first()
    search = requests.get(google_search + '+'.join(name.split()))
    tree = html.fromstring(search.content)
    href = ''
    for res in tree.xpath(google_result):
        href = res.get('href')
        href = unquote(href[7:].split('&')[0])
        do_break = False
        for url in gatherer_url:
            if href.lower().startswith(url.lower()):
                do_break = True
                break
        if do_break:
            break
        href = ''

    old_href = href
    info = requests.get(href)
    infotree = html.fromstring(info.content)
    href = infotree.xpath(gatherer_language)[0].get('href')
    href = gatherer_ext_url + href
    info = requests.get(href)
    infotree = html.fromstring(info.content)
    href = ''
    for lang in infotree.xpath(gatherer_english):
        if lang.getparent().getnext().xpath('text()')[0].strip() == card_lang:
            href = gatherer_ext_url + lang.get('href')
            break
    if href == '':
        href = old_href

    try:
        info = requests.get(href)
        infotree = html.fromstring(info.content)
        cardname = infotree.xpath(gatherer_cardname)[0].strip()
        cardimage = [img.get('src') for img in infotree.xpath(gatherer_cardimg)]
        if len(cardimage) > 1:
            if not cardimage[0] == cardimage[1]:
                cardaltname = infotree.xpath(gatherer_cardaltname)[0].strip()
                if not cardname == cardaltname:
                    return make_card(cardaltname)
            else:
                cardimage = cardimage[0:1]
        dbCard = UniqueCards.query.filter_by(name=cardname).first()
        if dbCard is None:
            cardcolour = set()
            for colour in infotree.xpath(gatherer_cardcolour):
                cardcolour.add(colour.get('alt'))
            cardcolour = filter_colour(cardcolour)
            cardtype = infotree.xpath(gatherer_cardtype)[0].split('—')[0].strip()
            cardtype, basic = filter_type(cardtype)
            cardimage = " ".join([gatherer_base + img[5:] for img in cardimage])
            dbCard = UniqueCards(cardname, cardcolour, cardtype, basic, cardimage)
            db.session.add(dbCard)
            db.session.commit()
            trCard = TranslationCards(name, dbCard.id)
            db.session.add(trCard)
            db.session.commit()
            print_log('  New card: %s' % cardname)
        trCard = TranslationCards.query.filter_by(cardid=dbCard.id).first()
        if trCard is None:
            trCard = TranslationCards(name, dbCard.id)
            db.session.add(trCard)
            db.session.commit()
        return dbCard
    except:
        print href

def filter_colour(colours):
    to_discard = set()
    to_add = set()
    for colour in colours:
        try:
            int(colour)
            to_discard.add(colour)
            to_add.add('Any')
        except:
            to_add = to_add.union(colour.split())
            continue
    colours = to_add - to_discard
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
        dbCard = UniqueCards.query.filter_by(id=card).first()
        if dbCard.colour == 'A':
            colours.add('A')
            continue
        for c in dbCard.colour:
            if c == 'A':
                continue
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
        if not n == n_cards:
            print 'problem with deck %s: %d cards' % (deck.name, n)

def check_dualcards():
    for card in UniqueCards.query.order_by(UniqueCards.id).all():
        sys.stdout.write('card %s' % card.name)
        padding = 50 - len(card.name)
        name = card.name
        search = requests.get(google_search + '+'.join(name.split()))
        tree = html.fromstring(search.content)
        href = ''
        for res in tree.xpath(google_result):
            href = res.get('href')
            href = unquote(href[7:].split('&')[0])
            do_break = False
            for url in gatherer_url:
                if href.lower().startswith(url.lower()):
                    do_break = True
                    break
            if do_break:
                break
            href = ''
        old_href = href
        info = requests.get(href)
        infotree = html.fromstring(info.content)
        href = infotree.xpath(gatherer_language)[0].get('href')
        href = gatherer_ext_url + href
        info = requests.get(href)
        infotree = html.fromstring(info.content)
        href = ''
        for lang in infotree.xpath(gatherer_english):
            if lang.getparent().getnext().xpath('text()')[0].strip() == card_lang:
                href = gatherer_ext_url + lang.get('href')
                break
        if href == '':
            href = old_href
        info = requests.get(href)
        infotree = html.fromstring(info.content)
        cardname = infotree.xpath(gatherer_cardname)[0].strip()
        cardimage = [img.get('src') for img in infotree.xpath(gatherer_cardimg)]
        if len(cardimage) == 1:
            print ' ' * padding + 'is single'
            continue
        if cardimage[0] == cardimage[1]:
            print ' ' * padding + 'is same face dual'
            continue
        cardaltname = infotree.xpath(gatherer_cardaltname)[0].strip()
        if cardname == cardaltname:
            card.image = ' '.join([gatherer_base + img[5:] for img in cardimage])
            print ' ' * padding + 'is dual'
            continue
        altcard = UniqueCards.query.filter_by(name=cardaltname).first()
        if altcard:
            trCards = TranslationCards.query.filter_by(cardid=card.id).all()
            for trc in trCards:
                trc.cardid = altcard.id
            dCards = DeckCards.query.filter_by(card=card.id).all()
            for dc in dCards:
                dc.card = altcard.id
            db.session.delete(card)
            print ' ' * padding + 'is duplicate dual, original name is %s' % altcard.name
            continue
        card.name = cardaltname
        card.image = ' '.join([gatherer_base + img[5:] for img in cardimage])
        print ' ' * padding + 'is dual, adjusting'
        db.session.commit()

def reorder_versions():
    names = set()
    for d in BattleDecks.query.all():
        names.add(d.name)
    for name in names:
        version = 1
        for d in BattleDecks.query.filter_by(name=name).order_by(BattleDecks.timestamp).all():
            d.version = version
            version += 1
    db.session.commit()

def print_log(data):
    print data
    return data + '\n'


if __name__ == '__main__':
    buf = update_db()
    if len(sys.argv) > 1:
        p = Popen(['mail',
                   '-r', 'Battle decks <no-reply@rhcloud.com>',
                   '-s', 'Battle decks update',
                   sys.argv[1]],
                  stdin=PIPE)
        p.communicate(input=buf)

