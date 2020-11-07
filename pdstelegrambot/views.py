import json
import requests
from django.http import JsonResponse
from django.views import View

from .models import pdstelegrambot_collection

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
                
    def set_word_responce(self, word, responce,  chat):
        #Get dictionary of words with responce:
        automatic_responce_dic = chat["word_responces"]
        automatic_responce_dic[word] = responce
        pdstelegrambot_collection.save(chat)
    
    def post(self, request, *args, **kwargs):
        t_data = json.loads(request.body)
        t_message = t_data["message"]
        t_chat = t_message["chat"]

        try:
            text = t_message["text"].strip().lower()
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

        print(chat)
        #If text comes with / at the start is a command
        if text[0] == '/':
            words = text.split()
            if (words[0] == "/set_word"):
                #/set_word <word> <responce>
                self.set_word_responce(words[1], words[2], chat)
            
        #Else is just text
        else:
            text = text.lstrip("/")
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