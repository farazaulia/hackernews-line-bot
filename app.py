import os
import requests
import json

from flask import (
    Flask, request, abort
)

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models import (
    MessageEvent, TextSendMessage, TextMessage,
    CarouselColumn, URITemplateAction, TemplateSendMessage,
    CarouselTemplate, FollowEvent, MessageTemplateAction,
    ButtonsTemplate
)

from decouple import config


app = Flask(__name__)

line_bot_api = LineBotApi(
    config("LINE_ACCESS_TOKEN", default=os.environ.get('LINE_ACCESS_TOKEN'))
)
handler = WebhookHandler(
    config(
        "LINE_CHANNEL_SECRET", default=os.environ.get('LINE_CHANNEL_SECRET'))
)


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


def prepareTitle(keyword, text):
    result = text[:30] + "..." if len(text) > 40 else text
    result = "[{}] {}".format(keyword.upper(), result)
    return result


def getStories(event, keyword):
    stories = []
    result = []

    data = requests.get(
        'https://hacker-news.firebaseio.com/v0/{}stories.json?print=pretty'.format(keyword))

    for num in data.json()[:5]:
        stories.append(requests.get(
            'https://hacker-news.firebaseio.com/v0/item/{}.json?print=pretty'.format(num)).json())

    for value in stories:
        title = prepareTitle(keyword, value['title'])
        desc = "oleh {} | {} poin".format(
            value['by'], str(value['score']))
        comment_url = 'https://news.ycombinator.com/item?id={}'.format(
            str(value['id']))

        try:
            url = value['url']
        except KeyError:
            url = comment_url

        column = CarouselColumn(
            title=title,
            text=desc,
            actions=[
                URITemplateAction(
                    label='Baca',
                    uri=url
                ),
                URITemplateAction(
                    label='Lihat komentar',
                    uri=comment_url
                ),
            ]
        )
        result.append(column)

    carousel = TemplateSendMessage(
        alt_text="Carousel",
        template=CarouselTemplate(
            columns=result
        )
    )

    result_text = 'Berikut 5 hasil teratas'
    result = [TextSendMessage(text=result_text),
              carousel]
    return result


def getMenu():
    buttons_template = ButtonsTemplate(text='Menu yang tersedia', actions=[
        MessageTemplateAction(label='Artikel Populer', text='@hn best'),
        MessageTemplateAction(label='Artikel Terbaru', text='@hn new'),
        MessageTemplateAction(label='Lowongan Kerja', text='@hn job'),
        MessageTemplateAction(label='Menu', text='@hn menu'),

    ])
    template_message = TemplateSendMessage(
        alt_text='Buttons alt text', template=buttons_template)

    return template_message


@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(
        event.reply_token, [
            TextSendMessage(
                text='Hai! Aku adalah HackerNews bot \uDBC0\uDC8D'),
            getMenu()
        ])


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    message = str.lower(event.message.text).strip()

    message = message.split(" ")

    if message[0] == '@hn':
        if message[1] == 'best' or message[1] == 'new' or message[1] == 'job':
            keyword = message[1]
            try:
                line_bot_api.reply_message(
                    event.reply_token, getStories(event, keyword))
            except Exception:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="Terjadi kesalah. Silahkan coba beberapa saat lagi!"))

        elif message[1] == 'menu':
            line_bot_api.reply_message(
                event.reply_token, getMenu())

        else:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="Ketik '@hn menu' untuk melihat menu. "))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
