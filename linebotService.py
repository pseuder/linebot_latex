from flask import Flask
import sys
import os
import base64
import requests
import json
import sympy
from pylatexenc.latexwalker import LatexWalker
app = Flask(__name__)

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage

import boto3
import hashlib
from boto3.session import Session

from sympy.plotting import plot
import matplotlib.pyplot as plt


line_bot_api = LineBotApi('crfjl/NW143XUz6WH2Jiqxurvv8B5NonMXmUdZMqV9FKqqds7i3qv9Abz13XYmvsjLHYHifo7ZOYiA3zxebQPjmollqxjg/tU1cnSswtqZam+z0yZ42P9m4faklXLqgO2uEA0id5LXfvvjW+fzf6wAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('7eb8282db360e146047283b4aac0f01c')

userOperation = {}

def convertImageToLatex(content):
    service = 'https://api.mathpix.com/v3/latex'
    env = os.environ
    default_headers = {
        'app_id': env.get('APP_ID', 'iop890520_gmail_com_4c4131_66969a'),
        'app_key': env.get('APP_KEY', '31c6e42201622f0099b2ebc2ce407bae5f020aaf396ac112ce201365252789db'),
        'Content-type': 'application/json'
    }

    img_url =  "data:image/jpg;base64," + base64.b64encode(content).decode()
    args = {
        "src": img_url,
        "formats": ["text", 'latex_simplified'],
        "data_options": {
            "include_asciimath": True,
            "include_latex": True
        }
    }
    r = requests.post(service, data=json.dumps(args), headers=default_headers, timeout=30)
    rr = json.loads(r.text)
    print(rr['latex_simplified'])
    return rr['latex_simplified']

def parseNodelist2Function(nodelist, begin, end, variable):
    toSympyString = ''
    basicOper = ['+', '(', ')']
    sympyStrDict = {'\sqrt': 'sympy.sqrt', '\infty': 'sympy.oo', '\log': 'sympy.log'}

    preType = ''
    operFrac = False
    FracStack = []
    for node in range(begin, end):
        nodelat = nodelist[node].latex_verbatim()
        nodeSplit = nodelat.split(' ')
        for nosp in nodeSplit:
            if nosp == '': continue
            if nosp == str(variable):
                if preType == 'number':
                    toSympyString += '*'
                toSympyString += 'x'
                preType = ''
            elif nosp in basicOper:
                toSympyString += nosp
                preType = ''
            elif str.isnumeric(nosp):
                toSympyString += nosp
                preType = 'number'
            elif nosp == '–' or nosp == '-':
                toSympyString += '-'
                preType = ''
            elif nosp == '^':
                toSympyString += '**'
                preType = ''
            elif nosp == '{':
                if operFrac:
                    FracStack.append('{')
                toSympyString += '('
                preType = ''
            elif nosp == '}':
                toSympyString += ')'
                preType = ''
                if operFrac:
                    FracStack.pop()
                    if len(FracStack) == 0:
                        operFrac = False
                        toSympyString += '/'
            elif nosp in sympyStrDict:
                preType = ''
                toSympyString += sympyStrDict[nosp]
                
            elif 'frac' in nosp:
                preType = ''
                operFrac = True
            elif 'sin' in nosp:
                if preType == 'number':
                    toSympyString += '*'
                toSympyString += 'sympy.sin'
                preType = ''
            elif 'cos' in nosp:
                if preType == 'number':
                    toSympyString += '*'
                toSympyString += 'sympy.cos'
                preType = ''
            elif 'tan' in nosp:
                if preType == 'number':
                    toSympyString += '*'
                toSympyString += 'sympy.tan'
                preType = ''

    return toSympyString


def convertToLim(s):
    try:
        return int(s)
    except ValueError:
        return float(s)

def latexToSympy(mathType, latextOri):
    print("latextOri: " + str(latextOri))
    w = LatexWalker(latextOri)
    (nodelist, pos, len_) = w.get_latex_nodes(pos=0)


    # mathType = nodelist[0].latex_verbatim()

    if mathType == '極限':
        lim_part = nodelist[2].latex_verbatim()
        variable = lim_part.split(' ')[1]
        toLimit = lim_part.split(' ')[3]
        if str.isnumeric(toLimit):
            toLimit = convertToLim(toLimit)
        elif toLimit == '\\infty':
            toLimit = sympy.oo

        x = sympy.Symbol(variable)

        toSympyString = parseNodelist2Function(nodelist, 3 , len(nodelist), x)
        evalSympy = eval(toSympyString)
        sympyResult = sympy.limit(evalSympy, x, toLimit)
        
    elif mathType == '微分':
        diffPart = nodelist[-1].latex_verbatim()
        diffCount = 0
        for diff_part in diffPart.split(' '):
            if 'prime' in diff_part:
                diffCount += 1

        x = sympy.Symbol('x')
        toSympyString = parseNodelist2Function(nodelist, 0,len(nodelist),x)[:-4]
        evalSympy = eval(toSympyString)
        sympyResult = sympy.diff(evalSympy,x,diffCount)
    elif mathType == '積分':
        for node in nodelist:
            print(node.latex_verbatim())
        
        
        if '_' in  nodelist[1].latex_verbatim():
            mathType = '定積分'
        elif 'int' in  nodelist[0].latex_verbatim():
            mathType = '不定積分'

        if mathType == '定積分':
            intStart = nodelist[2].latex_verbatim().split(' ')[1]
            intEnd = nodelist[4].latex_verbatim().split(' ')[1]

            if str.isnumeric(intStart):
                intStart = convertToLim(intStart)
            elif intStart == '\\infty':
                intStart = sympy.oo
            elif intStart == '\\pi':
                intStart = sympy.pi

            if str.isnumeric(intEnd):
                intStart = convertToLim(intEnd)
            elif 'infty' in intEnd:
                intEnd = sympy.oo
            elif 'pi' in intEnd:
                intEnd = sympy.pi

            x = sympy.Symbol('x')
            toSympyString = parseNodelist2Function(nodelist, 6, len(nodelist), x)[:-1]
            evalSympy = eval(toSympyString)
            sympyResult = sympy.integrate(evalSympy,(x, intStart, intEnd))
        elif mathType == '不定積分':
            x = sympy.Symbol('x')
            toSympyString = parseNodelist2Function(nodelist, 1, len(nodelist), x)[:-1]
            evalSympy = eval(toSympyString)
            sympyResult = sympy.integrate(evalSympy, x)

    print("toSympyString: " + toSympyString)
    print('sympyResult:' + str(sympyResult))
    return sympyResult, mathType


def storeToS3(pbHash, fileName):
    aws_key = 'AKIA6LFYBZGYW2LFHMYO'
    aws_secret = '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'
    session = Session(aws_access_key_id=aws_key, aws_secret_access_key=aws_secret,  region_name='us-west-1')
    s3 = session.resource('s3')
    bucket = 'linebot1071539'
    file = open(fileName, 'rb')
    s3 = boto3.resource('s3', aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
    s3.Object(bucket, f"{pbHash}/{fileName}").put(Body = file)


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        userId = event.source.user_id
        timestame = event.timestamp
        if userId not in userOperation:
            userOperation[userId] = ''
        reply_text = '未知的指令'
        if '@我想計算' in event.message.text:
            userOperation[userId] = event.message.text.split('@我想計算')[1]
            reply_text = '請傳送圖片'
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        print( event.message.text)
    except Exception as e:
        print(e)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=e))



@handler.add(MessageEvent, message=ImageMessage)
def handle_message(event):
    try:
        userId = event.source.user_id
        timestamp = event.timestamp
        hash_object = hashlib.sha1(str.encode(f"{userId}{timestamp}"))
        pbHash = hash_object.hexdigest()
        print('pbHash: ' + pbHash)
        print('messageid: ' + event.message.id)
        image_content = line_bot_api.get_message_content(event.message.id)
        with open("source.png", "wb") as fh:
            fh.write(image_content.content)
        storeToS3(pbHash, "source.png")


        latex = convertImageToLatex(image_content.content)

        if userOperation[userId] == 'LaTeX':
            line_bot_api.reply_message( event.reply_token, TextSendMessage(text=str(latex)) )
            return



        # latex = '\lim _ { x \rightarrow \infty } ( ( x ^ { 2 } + 1 ) + 2 x )'
        SympyResult, mathType = latexToSympy(userOperation[userId] , latex)


        reply_arr=[]
        reply_arr.append( TextSendMessage(text=f'LaTeX: {latex}') )
        
        if userOperation[userId] == '極限' or  mathType == '定積分':
            reply_arr.append(TextSendMessage(text=str(SympyResult)) )
        elif userOperation[userId] == '微分' or mathType == '不定積分':
            graph = plot(SympyResult, show=False)
            graph.save('graph.png')
            sympyResultLetex = '$' + sympy.latex(SympyResult) + '$'
            plt.title(sympyResultLetex, loc='left', fontsize=20)
            plt.savefig('sympyResult.png')
            
            storeToS3(pbHash, "sympyResult.png")
            reply_arr.append(ImageSendMessage(
                    original_content_url=f"https://linebot1071539.s3.us-west-1.amazonaws.com/{pbHash}/sympyResult.png", 
                    preview_image_url=f"https://linebot1071539.s3.us-west-1.amazonaws.com/{pbHash}/sympyResult.png"))
    
        line_bot_api.reply_message( event.reply_token, reply_arr )
    except Exception as e:
        print(e)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=e))
    


if __name__ == '__main__':
    app.run()
