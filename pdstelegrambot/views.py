import json,datetime
import requests
from django.http import JsonResponse
from django.views import View
from datetime import datetime,timedelta

from .models import pdstelegrambot_collection
from .models import message_collection
from .models import user_collection

TELEGRAM_URL = "https://api.telegram.org/bot"
TUTORIAL_BOT_TOKEN = "1284944972:AAHuf8KsNu2qcLUZN3K37b0gl53wN5QLtzo"
  
# https://api.telegram.org/bot1284944972:AAHuf8KsNu2qcLUZN3K37b0gl53wN5QLtzo/setWebhook?url=<url>/webhooks/tutorial/
class TutorialBotView(View):
    def send_automatic_responce(self, sentence, chat):
        #Auxiliary list to not repeat words
        list_aux=[]
        #Get dictionary of words with responce:
        automatic_responce_dic = chat["word_responces"]
        for word in sentence.split():
            if word in automatic_responce_dic and word not in list_aux:
                self.send_message(automatic_responce_dic[word], chat["chat_id"])
                list_aux.append(word)
    ##################################################################################
                
    def set_word_responce(self, word, responce,  chat):
        #Get dictionary of words with responce:
        automatic_responce_dic = chat["word_responces"]
        automatic_responce_dic[word] = " ".join(responce)
        pdstelegrambot_collection.save(chat)
        self.send_message("Response set for " + word, chat["chat_id"])
    ##################################################################################
        
    def get_user_most_sent_messages(self, chat_id, period):
        d = datetime.utcnow() - timedelta(days=period)
        
        agr = [
               {"$match": {"$and": [{ "chat_id" : chat_id}, {"datetime": {"$gte": d}}]}},
               {'$group': {
                            "_id": {
                                  "user_id": "$user_id",
                            },
                            "messages": {
                                  "$addToSet": "$message"
                            }
                        }
                }]
        
        val = list(message_collection.aggregate(agr))
        
        max_user_id = 0
        max_user_messages_count = 0
        
        for i in val:
            cant_msg = len(i['messages'])
            if cant_msg >  max_user_messages_count:
                max_user_messages_count = cant_msg
                max_user_id = i['_id']['user_id']
        
        usr = user_collection.find_one({"user_id": max_user_id})
        if usr:
            r=usr["first_name"] + " " +usr["last_name"]
            self.send_message("The user that sent the most messages in the past "+ str(period) +" days is " + r, chat_id)
        else:
            self.send_message("Error in the request", chat_id)
        
    ##################################################################################
    
    def post(self, request, *args, **kwargs):
        t_data = json.loads(request.body)
        print(t_data)
        try:
            t_message = t_data["message"]
            text = t_message["text"].strip().lower()
            t_chat = t_message["chat"]
        except Exception as e:
            return JsonResponse({"ok": "POST request processed"})

        chat = pdstelegrambot_collection.find_one({"chat_id": t_chat["id"]})
        if not chat:
            chat = {
                "chat_id": t_chat["id"],
                "word_responces": {}
            }
            response = pdstelegrambot_collection.insert_one(chat)
            # we want chat obj to be the same as fetched from collection
            chat["_id"] = response.inserted_id

        #If text comes with / at the start is a command
        if text[0] == '/':
            words = text.split()
            #/set_word <word> <responce>
            if (words[0] == "/set_word"):
                if(len(words)<3):
                    self.send_message("Error, please use the format: /set\_word <word> <response>", chat["chat_id"])
                else:
                    self.set_word_responce(words[1], words[2:], chat)
            #/get_user_most_sent_messages [days]
            elif (words[0] == "/get_user_most_sent_messages"):
                try:
                    if(len(words)==2 and int(words[1])>0):
                        self.get_user_most_sent_messages(chat["chat_id"], int(words[1]))
                    elif(len(words)==1):
                        self.get_user_most_sent_messages(chat["chat_id"], 7)
                    else:
                        self.send_message("Error, please use the format: /get\_user\_most\_sent\_messages \[days]", chat["chat_id"])
                except Exception as e:
                    self.send_message("Error, please use the format: /get\_user\_most\_sent\_messages \[days]", chat["chat_id"])
                    
            #/help
            elif (words[0] == "/help"):
                #Send list of commands
                self.send_message("/set\_word <word> <response>: Set a automatic responce for a word sent by a user", chat["chat_id"])
                self.send_message("/get\_user\_most\_sent\_messages \[days]: Get the user with most messages in a certain period of time", chat["chat_id"])
                
            else:
                self.send_message("Unknown command, type /help for list of commands", chat["chat_id"])
            
        #Else is just text
        else:
            text = text.lstrip("/")
            #Insert the message in the databasse for messages
            msg = {
                "chat_id": t_chat["id"],
                "user_id": t_message["from"]["id"],
                "datetime": datetime.utcnow(),
                "message": text
            }
            message_collection.insert_one(msg)
            self.send_automatic_responce(text, chat)
            
            #Insert/update user in the user database if is not already
            usr = user_collection.find_one({"user_id": t_message["from"]["id"]})
            if not usr:
                usr={
                    "user_id": t_message["from"]["id"],
                    "first_name": t_message["from"]["first_name"],
                    "last_name": t_message["from"]["last_name"],
                }
                user_collection.insert_one(usr)

        return JsonResponse({"ok": "POST request processed"})

    @staticmethod
    def send_message(message, chat_id):
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendMessage", data=data
        )
