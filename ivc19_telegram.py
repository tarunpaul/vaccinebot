import argparse
import hashlib
import sys
import requests
import datetime
from pymemcache.client import base

class Command:
    help = "Gets vaccine available slots and sends telegram to subscribers"

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--dist_ids", nargs="+", default=[])
        parser.add_argument("-d", "--dist_name", type=str)
        parser.add_argument("-c", "--channel", type=str)
        self.options = parser.parse_args()
        self.cache = base.Client(('localhost', 11211))


    def handle(self, *args, **options):
        sys.stdout.write('----------------------------------------\n')
        now = datetime.datetime.now()
        sys.stdout.write(now.strftime("%a, %d-%b-%Y %I:%M:%S"))

        print("\n", self.options)

        DIST_NAME = self.options.dist_name
        districts = self.options.dist_ids
        #pincode = "600096"
        your_age = 30
        CHANNEL_NAME = self.options.channel

        # telegram bot auth token
        bot2_token = ""

        date = now.strftime("%d-%m-%Y")
        #date = "12-05-2021"

        print("Trying to get data for", date, "for", DIST_NAME, "...")

        headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
                'referer': 'https://selfregistration.cowin.gov.in/',
                "accept": "*/*",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",

                "referrerPolicy": "strict-origin-when-cross-origin",
                "body": None,
                "method": "OPTIONS",
                "mode": "cors"
        }


        centers = []
        for dist in districts:
            url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByDistrict?district_id={dist}&date={date}"
            res = requests.get(url, headers=headers)
            if res.ok is False:
                print("Could not get cowin data.")
                print(res)
                print("----------------------------------------")
                sys.exit()

            result = res.json()
            #print(result)
            centers.extend(result['centers'])
        
        print("Centers", len(centers))
        available_centers = []
        available_centers_unique = []
        available_centers_availibity_count = []
        slots_count = {}
        for center in centers:
            sessions = center['sessions']
            for session in sessions:
                #print(session)
                slots_count['overall'] = slots_count.get('overall', 0) + 1
                if int(session['min_age_limit']) < int(your_age):
                    slots_count['18plus'] = slots_count.get('18plus', 0) + 1
                    slots = ", ".join(session['slots'])
                    if session['available_capacity']  <= 1:
                        continue
                    available_centers.append("Available: " + str(session['available_capacity']) + " | " + "Date: " + session['date'] + "\nVaccine: " + session['vaccine'] + " | Pincode:" + str(center['pincode']) + "\nName: " + center['name'] + "\n Dose 1:" + str(session['available_capacity_dose1']) + " | Dose 2: " + str(session['available_capacity_dose2']) + "\n----\n")

                    available_centers_availibity_count.append(session['available_capacity'])
                    available_centers_unique.append(session['date'] + session['vaccine'] + str(center['pincode']) + center['name'])

                    print("Available:", session['available_capacity'])
                    print("CenterID:", center['center_id'], "| Name:", center['name'], "| PIN", center['pincode'], "| block:", center['block_name'], "| Fees", center['fee_type'])
                    print("Date:", session['date'], "| Age Limit:", session['min_age_limit'], "| Vaccine:", session['vaccine'], "| Slots: ", slots)
                    print("----------")


        print(slots_count)

        text_message = "Available vaccine slots in " + DIST_NAME + "\nAge group: 18-45\n"
        text_message += "Book: https://selfregistration.cowin.gov.in\n\n"
        #text_message += "".join(available_centers)

        send_message = False
        for i, acenter in enumerate(available_centers):
            #print(available_centers_unique[i])
            #print(acenter)
            key = available_centers_unique[i]
            hash_object = hashlib.sha256(key.encode('utf-8'))
            key_hexdigest = hash_object.hexdigest()
            if self.cache.get(key_hexdigest):
                if str(self.cache.get(key_hexdigest).decode('utf-8')) == str(available_centers_availibity_count[i]):
                    print("Skipping as availability didn't change:", available_centers[i])
                    self.cache.set(key_hexdigest, available_centers_availibity_count[i], 60*15)
                continue
            self.cache.set(key_hexdigest, available_centers_availibity_count[i], 60*30)
            text_message += available_centers[i]
            send_message = True

        
        #subscribers = models.TelegramUser.get_subscribers()

        if len(available_centers) < 1:
            print("No slots available")
        elif send_message is False:
            print("Not sending message, will try again in 30 mins")
        elif send_message is True and len(available_centers) > 0:
            channel_url =  f'https://api.telegram.org/bot{bot2_token}/sendMessage'
            data = {'chat_id': CHANNEL_NAME, 'text': text_message}
            res = requests.post(channel_url, data)
            print(res.status_code)
            #print(res.json())
            print("Notification sent to channel", CHANNEL_NAME)

            #print("Sending to subscribers:", subscribers)
            #for subscriber in subscribers:
            #    data = {'chat_id': subscriber, 'text': text_message}
            #    res = requests.post(url, data)
            #    print(res.status_code)
            #    print("Telegram sent to subscribers", subscriber)
        else:
            print("No slots available")

        sys.stdout.write('----------------------------------------\n')


command = Command()
command.handle()
