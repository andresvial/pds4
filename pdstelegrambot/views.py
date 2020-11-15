import json
import requests
import numpy as np
import matplotlib.pyplot as plt
from django.http import JsonResponse
from django.views import View
from datetime import datetime,timedelta

from .models import pdstelegrambot_collection
from .models import message_collection

TELEGRAM_URL = "https://api.telegram.org/bot"
TUTORIAL_BOT_TOKEN = "1284944972:AAHuf8KsNu2qcLUZN3K37b0gl53wN5QLtzo"
  
# https://api.telegram.org/bot1284944972:AAHuf8KsNu2qcLUZN3K37b0gl53wN5QLtzo/setWebhook?url=<url>/webhooks/tutorial/
class TutorialBotView(View):
    def get_user_info(self, chat_id, user_id):
        x = requests.get(f"https://api.telegram.org/bot{TUTORIAL_BOT_TOKEN}/getChatMember", params={"chat_id": chat_id, "user_id": user_id})
        x = json.loads(x.content)
        return x
    
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
        
        usr = self.get_user_info(chat_id, max_user_id)
        if usr:
            r=usr["result"]["user"]["first_name"] + " " +usr["result"]["user"]["last_name"]
            self.send_message("The user that sent the most messages in the past "+ str(period) +" days is " + r, chat_id)
        else:
            self.send_message("Error in the request", chat_id)
        
    ##################################################################################
    # Pregunta 3: Usuario que ha enviado más caracteres

    def get_user_most_sent_characters(self, chat_id, period):
        d = datetime.utcnow() - timedelta(days=period)
        
        agr = [
               {"$match": {"$and": [{ "chat_id" : chat_id}, {"datetime": {"$gte": d}}]}},
               {'$group': {
                            "_id": {
                                  "user_id": "$user_id",
                            },
                            "characters": {
                                  "$sum": "$total_characters"
                            }
                        }
                }]
        
        val = list(message_collection.aggregate(agr))
        
        max_user_id = 0
        max_user_characters = 0
        
        for i in val:
            if i["characters"] >= max_user_characters:
                max_user_id = i["_id"]["user_id"]
                max_user_characters = i["characters"]
        
        usr = self.get_user_info(chat_id, max_user_id)
        if usr:
            r=usr["result"]["user"]["first_name"] + " " +usr["result"]["user"]["last_name"]
            self.send_message("The user that sent the most characters in the past "+ str(period) +" days is " + r, chat_id)
        else:
            self.send_message("Error in the request", chat_id)

    ##################################################################################
    # Pregunta 5 Mensajes x Dia
    def get_messages_by_day(self, chat_id, period):
        d = datetime.utcnow() - timedelta(days=period)
        
        agr = [
            {"$match": {"$and": [{ "chat_id" : -439406000}, {"datetime": {"$gte": d}}]}},
            {'$project': 
                { 'formattedMsgDate':
                        { "$dateToString": {'format':"%Y-%m-%d", 'date':"$datetime"}}
                }
            },
            {'$group': {
                    "_id": "$formattedMsgDate",
                    "count":{"$sum":1}
                }
            }
        ]
        
        val = list(message_collection.aggregate(agr))
        
        #pasar los datos en val a una imagen
        
        usr = val[0]
        if usr:
            r = ""
            for i in val:
                r+= i["_id"] + ": " + i["count"] + "\n"
            self.send_message("The ammount of messages by day sent in the past "+ str(period) +" days is:\n" + r, chat_id)
        else:
            self.send_message("Error in the request", chat_id)

        x = []
        y = []
        
        #Fill the x list with the dates for the graphs
        base=datetime.utcnow()
        for i in reversed(range(period)):
            aux= base - timedelta(days=int(i))
            x.append(str(aux.day) + "/" + str(aux.month) + "/" + str(aux.year))
            
        #Fill the y list with the respective characters sent by each date position of x
        for i in val:
            date= str(i["_id"]["day"]) + "/" + str(i["_id"]["month"]) + "/" + str(i["_id"]["year"])
            if (date in x):
                y[x.index(date)] = i["total_characters"]
            
        #Plot the graph and send it
        plt.figure()
        ax = plt.subplot()
        plt.xticks(rotation=90)
        ax.bar(x,y)
        plt.title('Characters sent across the past '+ str(period) +" days" )
        plt.savefig('characters_per_day.png', bbox_inches='tight')
        self.send_photo('characters_per_day.png', chat_id)
        
    
    ##################################################################################
    def innactive_users(self, chat_id, period):
        d = datetime.utcnow() - timedelta(days=period)
        
        users_in_period = message_collection.find({"$and": [{ "chat_id" : chat_id}, {"datetime": {"$gte": d}}]}).distinct('user_id')
        
        all_users = message_collection.find({ "chat_id" : chat_id}).distinct('user_id')
        
        set_difference = set(all_users) - set(users_in_period)
        list_difference = list(set_difference)
        
        string=""
        if len(list_difference)==0:
            self.send_message("No inactive user found", chat_id)
            
        else:       
            for u_id in list_difference:
                usr = self.get_user_info(chat_id, u_id)
                string += usr["result"]["user"]["first_name"] + " " +usr["result"]["user"]["last_name"] + '\n'
            
            self.send_message("Inactive users in "+ str(period) +" days: \n" + string, chat_id)
    
    
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

            #/get_user_most_sent_characters [days]
            elif (words[0] == "/get_user_most_sent_characters"):
                try:
                    if(len(words)==2 and int(words[1])>0):
                        self.get_user_most_sent_characters(chat["chat_id"], int(words[1]))
                    elif(len(words)==1):
                        self.get_user_most_sent_characters(chat["chat_id"], 7)
                    else:
                        self.send_message("Error, please use the format: /get\_user\_most\_sent\_characters \[days]", chat["chat_id"])
                except Exception as e:
                    self.send_message("Error, please use the format: /get\_user\_most\_sent\_characters \[days]", chat["chat_id"])
                    
                 
            #/innactive_users [days]
            elif (words[0] == "/innactive_users"):        
                try:
                    if(len(words)==2 and int(words[1])>0):
                        self.innactive_users(chat["chat_id"], int(words[1]))
                    elif(len(words)==1):
                        self.innactive_users(chat["chat_id"], 7)
                    else:
                        self.send_message("Error, please use the format: /innactive\_users \[days]", chat["chat_id"])
                except Exception as e:
                    self.send_message("Error, please use the format: /innactive\_users \[days]", chat["chat_id"])
                
            elif (words[0] == "/plot"):    
                self.send_photo("dde",chat["chat_id"])
            #/help
            elif (words[0] == "/help"):
                #Send list of commands
                string=""
                string+="/set\_word <word> <response>: Set a automatic responce for a word sent by a user \n"
                string+="/get\_user\_most\_sent\_messages \[days]: Get the user with most messages in a certain period of time \n"
                string+="/innactive\_users \[days]: Get innactive users in a certain period of time \n"
                self.send_message(string, chat["chat_id"])
                
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
                "message": text,
                "total_characters": len(text)
            }
            message_collection.insert_one(msg)
            self.send_automatic_responce(text, chat)

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

    @staticmethod
    def send_photo(message, chat_id):
        y = [2,4,6,8,10,12,14,16,18,20]
        x = np.arange(10)
        fig = plt.figure()
        ax = plt.subplot(111)
        ax.plot(x, y, label='$y = numbers')
        plt.title('Legend inside')
        ax.legend()
        fig= plt.savefig('plot.png')
        
        data = {
            "chat_id": chat_id,
        }
        
        files= {
            "photo": open('plot.png','rb'), 
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendPhoto", data=data, files=files
        )