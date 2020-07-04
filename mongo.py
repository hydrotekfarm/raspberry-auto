from typing import List
from datetime import datetime
import paho.mqtt.client as mqtt
import pymongo
import pymongo.database
import pymongo.collection
import pymongo.errors
import threading
import os
import time
from signal import pause


MONGO_URI = "mongodb://0.0.0.0:27017"  # mongodb://user:pass@ip:port || mongodb://ip:port
MONGO_DB = "buck"
MONGO_COLLECTION = "live_system_data"
MONGO_COLLECTION1 = "live_grow_room_data"
#MONGO_TIMEOUT = 20  # Time in seconds
MONGO_DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"

MONGO_URI = os.getenv("MONGO_URI", MONGO_URI)
MONGO_DB = os.getenv("MONGO_DB", MONGO_DB)
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", MONGO_COLLECTION)
MONGO_COLLECTION1 = os.getenv("MONGO_COLLECTION1", MONGO_COLLECTION1)
#MONGO_TIMEOUT = float(os.getenv("MONGO_TIMEOUT", MONGO_TIMEOUT))
MONGO_DATETIME_FORMAT = os.getenv("MONGO_DATETIME_FORMAT", MONGO_DATETIME_FORMAT)


class Mongo(object):
    def __init__(self):
        self.client: pymongo.MongoClient = None
        self.database: pymongo.database.Database = None
        self.collection: pymongo.collection.Collection = None
        self.collection1: pymongo.collection1.Collection = None
        self.queue: List[mqtt.MQTTMessage] = list()

    def connect(self):
        
        self.client = pymongo.MongoClient(MONGO_URI)
        self.database = self.client.get_database(MONGO_DB)
        self.collection = self.database.get_collection(MONGO_COLLECTION)
        self.collection1 = self.database.get_collection(MONGO_COLLECTION1)
        
        
    def disconnect(self):
        
        if self.client:
            self.client.close()
            self.client = None

    def connected(self) -> bool:
        if not self.client:
            return False
            try:
                self.client.admin.command("ismaster")
            except pymongo.errors.PyMongoError:
                return False
        else:
            return True

    def _enqueue(self, msg: mqtt.MQTTMessage):
        
        self.queue.append(msg)
        

    def __store_thread_f(self, msg: mqtt.MQTTMessage):
        seg=msg.topic.split('/')
        segcnt=len(seg)
        
        D2=eval(msg.payload.decode())
        
        try:
            if segcnt==3:
                    
                    
                result = self.collection.update_one({
                    "grow_room_id": seg[0],
                    "system_id":seg[2],
                    "nsamples":{'$lt':5}
                    },
                    {
                        '$push': { 
                            "samples": D2
                                
                                },
                        '$set': { "last_time": D2["time"]},
                        '$setOnInsert':{"first_time":D2["time"]},
                        '$inc': { "nsamples": 1 }
                            
                        }, upsert=True)
                    
            elif segcnt==2:
                    
                    
                result = self.collection1.update_one({
                    "grow_room_id": seg[0],
                        
                    "nsamples":{'$lt':5}
                    },
                    {
                        '$push': { 
                            "samples": D2
                                
                                },
                        '$set': { "last_time": D2["time"]},
                        '$setOnInsert':{"first_time":D2["time"]},
                        '$inc': { "nsamples": 1 }
                            
                        }, upsert=True)
            else: print("Incorrect topic name. Use topic with 2 or 3 fields.")
                        
            if not result.acknowledged:
                    # Enqueue message if it was not saved properly
                    self._enqueue(msg)
        except Exception as ex:
                print(ex)

    def _store(self, msg):
        
        th = threading.Thread(target=self.__store_thread_f, args=(msg,))
        th.daemon = True
        th.start()

    def save(self, msg: mqtt.MQTTMessage):
        
        if msg.retain:
            print("Skipping retained message")
            return
        if self.connected():
            self._store(msg)
        else:
            self._enqueue(msg)

