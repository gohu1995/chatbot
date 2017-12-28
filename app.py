import os
import sys
import json
import re
from datetime import datetime

import requests
from flask import Flask, request

app = Flask(__name__)
KB = {}

@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200

#METHODS FOR ADVICE TAKER


# forwardDFS is for returning a list of all forward inferences
def forwardDFS(KB,tup,list2,val):
    if bool(KB[tup]) == True:
        for key in KB[tup]:
            if list2.has_key(key) == False:
                if KB[tup][key] == False  and val == 1:
                    list2[key] = KB[tup][key]
                elif KB[tup][key] == True:
                    list2[key] = KB[tup][key]
                    forwardDFS(KB,key,list2,-1) 

# BackwardDFS is used for returning a list of backward inferences.

def backwardHelper(KB,tup,list2,parentval,nextval,val):
    if bool(KB[nextval]) == True:
        for key in KB[nextval]:
            if key == tup:
                list2[parentval] = KB[nextval][key]
            elif key != tup and KB[nextval][key] == True:
                backwardHelper(KB,tup,list2,parentval,key,val)

def backwardDFS(KB,tup,list2):
    for key in KB:
        backwardHelper(KB,tup,list2,key,key,1)

#for the questions you need to print out statement responses
# this formats the statement responses based on the X and Y inputs, 
# a TorF var which is True or False, and the KB(Knowledge base)

def statementCreation(x,y,TorF,KB):
    SorP = isPlural(KB,x)
    if SorP == 0:
        if isVowel(x[0]):
            output = "An "+x
        else:
            output = "A "+x
        if TorF:
            output = output +" is"
        else:
            output = output +" is not"
    elif SorP == 1:
        output = x.title()
        if TorF:
            output = output +" are"
        else:
            output = output +" are not"
    elif SorP == -1:
        output = x.title()
        if TorF:
            output = output + " is"
        else:
            output = output + " is not"
        if isPlural(KB,y) == 1:
            y = find_tuple(KB,y,1)[0]
    SorP = isPlural(KB,y)
    if SorP == 0:
        if isVowel(y[0]):
            output = output + " an "+y
        else:
            output = output +  " a "+y
    else:
        output = output+" "+y
    return output


# checks if a character is a vowel, used for formatting statements

def isVowel(val):
    if val == "a" or val == "e" or val == "i" or val == "o" or val == "u":
        return True
    else:
        return False
# This checks whether a word is plural, used for printing out formatted statements

def isPlural(KB,tupval):
    for key in KB:
        if key[0] == tupval and key[1] != tupval:
            return 0
        elif key[1] == tupval and key[0] != tupval:
            return 1
        elif key[1] == tupval and key[0] == tupval:
            return -1
    return None

#You can put in either a singular or plural and this will find you the tuple 
# for that word, if it exists in the KB, None is the same as null in java

def find_tuple(KB,tup,SorP):
    for key in KB:
        if key[SorP] == tup:
            return key
    return None

# Inserts a new statement into knowledge base,you have to ask for plurals,
# if you have the plurals for both x and y, you just say OK,
# if you already mapped the relation, you say I know.

def insert(KB,text1):
    statement = re.compile("(A\s|An\s)*(\w+)\s(is|are)+\s(not\s)*(a\s|an\s)*(\w+)")

    result1 = re.search(statement,text1)

    if result1:
        signal = 0
        values = result1.groups()

        x = values[1].lower()
        y = values[5].lower()
        
        if values[2] == "is":
            tupx = find_tuple(KB,x,0)
            tupy = find_tuple(KB,y,0)

            if tupx != None and tupy != None:
                if bool(KB[tupx]) == False:
                    send_message(sender_id,"Ok.")
                elif KB[tupx].has_key(tupy):
                    send_message(sender_id,"I know")
                else:
                    send_message(sender_id,"Ok.")


            if tupx == None:
                pluralx = raw_input('what is the plural form of '+values[1]+'\n').lower()
                if pluralx == "na":
                    pluralx = x
                tupx = (x,pluralx)
            if tupy == None:
                pluraly = raw_input('what is the plural form of '+values[5]+'\n').lower()
                if pluraly == "na":
                    pluraly = y
                tupy = (y,pluraly)
            
        elif values[2] == "are":
            tupx = find_tuple(KB,x,1)
            tupy = find_tuple(KB,y,1)

            if tupx != None and tupy != None:
                if bool(KB[tupx]) == False:
                    send_message(sender_id,"Ok.")
                elif KB[tupx].has_key(tupy):
                    send_message(sender_id,"I know")
                else:
                    send_message(sender_id,"Ok.")

            if tupx == None:
                singularx = raw_input('what is the singular form of '+values[1]+'\n').lower()
                if singularx == "na":   
                    singularx = x
                tupx = (singularx,x)
            if tupy == None:
                singulary = raw_input('what is the singular form of '+values[5]+'\n').lower()
                if singulary == "na":
                    singulary = y
                tupy = (singulary,y)

            
        if KB.has_key(tupx) == False:
            KB[tupx] = {}
        if KB.has_key(tupy) == False:
            KB[tupy] = {}
        if values[3] == None:
            KB[tupx][tupy] = True
        else :
            KB[tupx][tupy] = False
    return KB

#END METHODS FOR ADVICE TAKER



@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    # you may not want to log every incoming message in production, but it's good for testing
    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text


                    #Andrew's Attempt at editing
                    INPUT = message_text

                    if INPUT == "Bye." or INPUT == "bye.":
                        break

                    
                    if INPUT.find(','):
                        INPUTlist = INPUT.split(',')
                    else :
                        INPUTlist[0] = INPUT
                    
                    statement = re.compile("(A\s|An\s)*(\w+)\s(is|are)+\s(not\s)*(a\s|an\s)*(\w+)")
                    result1 = re.search(statement,INPUT)

                    if result1:
                        for index in INPUTlist:
                            KB = insert(KB,index)
                        
                    question = re.compile("(Is|Are)+\s(a\s|an\s)*(\w+)\s(a\s|an\s)*(\w+)\?")
                    result2 = re.search(question,INPUT)

                    if result2:
                        signal = 0
                        values = result2.groups()
                        x = values[2].lower()
                        y = values[4].lower()
                        SorP = values[0].lower()
                        if(SorP == "is"):
                            tupx = find_tuple(KB,x,0)
                            tupy = find_tuple(KB,y,0)
                        else:
                            tupx = find_tuple(KB,x,1)
                            tupy = find_tuple(KB,y,1)

                        if tupx == None or tupy == None or KB[tupx].has_key(tupy) == False:
                            if SorP == "is":
                                decision = raw_input("I'm not sure,is it?\n")
                                if(decision == "yes"):
                                    text = "A "+x+" "+SorP+" "+y
                                    KB = insert(KB,text)
                                elif(decision == "no"):
                                    text = "A "+x+" "+SorP+" "+"not"+" "+y
                                    KB = insert(KB,text)
                            else:
                                decision = raw_input("I'm not sure,are they?\n")
                                if(decision == "yes"):
                                    text = x+" "+SorP+" "+y
                                    KB = insert(KB,text)
                                elif(decision == "no"):
                                    text = x+" "+SorP+" "+"not"+" "+y
                                    KB = insert(KB,text)
                        elif KB[tupx][tupy] == True:
                            send_message(sender_id,"Yes")
                        elif KB[tupx][tupy] == False:
                            send_message(sender_id,"No")

                    question3 = re.compile("What do you know about (\w+)?")
                    result3 = re.search(question3,INPUT)
                    printForward = {}
                    printBackward = {}
                    
                    if result3:
                        counter = 0
                        signal = 1
                        values = result3.groups()
                        x = values[0].lower()
                        tupx = find_tuple(KB,x,0)
                        SorP = isPlural(KB,x)
                        if tupx == None:
                            tupx = find_tuple(KB,x,1)

                        forwardDFS(KB,tupx,printForward,1)
                        backwardDFS(KB,tupx,printBackward)
                        
                        flist = printForward.items()
                        blist = printBackward.items()
                        
                        output = values[0]

                        y = flist[0]

                        
                        if isPlural(KB,x):
                            send_message(sender_id,statementCreation(x.lower(),y[0][1],y[1],KB))
                            counter = counter + 1
                        else:
                            send_message(sender_id,statementCreation(x.lower(),y[0][0],y[1],KB))
                            counter = counter + 1

                    question4 = re.compile("Anything else?")
                    result4 = re.search(question4,INPUT)

                    if result4 and signal == 1:
                        val = len(flist)-1
                        if counter <= val:
                            y = flist[counter]
                            if isPlural(KB,x):
                                send_message(sender_id,statementCreation(x.lower(),y[0][1],y[1],KB))
                                counter = counter + 1
                            else:
                                send_message(sender_id,statementCreation(x.lower(),y[0][0],y[1],KB))
                                counter = counter + 1
                        elif counter-val-1 < len(blist):
                            y = blist[counter - val-1]
                            if isPlural(KB,x):
                                send_message(sender_id,statementCreation(y[0][1],x.lower(),y[1],KB))
                                counter = counter + 1
                            else:
                                send_message(sender_id,statementCreation(y[0][0],x.lower(),y[1],KB))
                                counter = counter + 1
                        else:
                            out = "I don't know anything else about "+x
                            send_message(sender_id,out)

                    if result1 == None and result2 == None and result3 == None and result4 == None:
                        send_message(sender_id,"I dont understand.")

                    log(message_text)
                    # send_message(sender_id, message_text)


                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200





def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(msg, *args, **kwargs):  # simple wrapper for logging to stdout on heroku
    try:
        if type(msg) is dict:
            msg = json.dumps(msg)
        else:
            msg = unicode(msg).format(*args, **kwargs)
        print u"{}: {}".format(datetime.now(), msg)
    except UnicodeEncodeError:
        pass  # squash logging errors in case of non-ascii text
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
