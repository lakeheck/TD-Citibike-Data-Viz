from pymongo import MongoClient
def get_database():
 
   # Provide the mongodb atlas url to connect python to mongodb using pymongo
   # see https://www.mongodb.com/docs/guides/atlas/connection-string/
   CONNECTION_STRING = "mongodb+srv://lakeheck:<password>@cluster0.bchriqh.mongodb.net/?retryWrites=true&w=majority"
 
   # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
   client = MongoClient("mongodb+srv://watershed:watershed@cluster0.bchriqh.mongodb.net/?retryWrites=true&w=majority")
 
   # Create the database for our example (we will use the same database throughout the tutorial
   return client['station_ebike_changes']
  
# This is added so that many files can reuse the function get_database()
if __name__ == "__main__":   
  
   # Get the database
   dbname = get_database()

