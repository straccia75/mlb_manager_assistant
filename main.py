import pandas as pd
import os
import sqlite3
#MIGHT BE MOVING THIS PORTION OF CODE TO ANOTHER FILE LATER... I AM SCALATING THE CODE TO A MONOREPO FOR MY OWN WEB FRONT END
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
#This is the library that will help me change from a static csv file i got from Kaggle to a LIVE MLB API so I get REAL TIME DATA!!! 
import statsapi
#Loading variables in the memory
load_dotenv()

#TELEGRAM BOT TOKEN TO AUTHENTICATE ON TELEGRAM BOT API
# MOVED TO A .ENV FILE FOR ENHANCED SECURITY
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

## MOVING TO A .ENV FILE LATER FOR ENHANCED SECURITY
file_route = "C:/Users/strac/Documents/Portfolio/mlb_manager_assistant/data/mlb_2025.csv"

def load_clean_data(raw_data):

    """This function has been created
    to load and clean all data before
    starting its journey through the 
    pipeline"""

    try:
        df_mlb = pd.read_csv(raw_data)
    except FileNotFoundError:
        return f"File in {raw_data} not found"

    # By doing df_mlb.info() can be observed that streamer_category column has around 158 empty/null rows
    # I thought about dropping these rows but I am keeping them and assigning a "No Category" tag. Might be useful later on.
    
    df_mlb["streamer_category"] = df_mlb["streamer_category"].fillna("No Category")

    #Normalizing Data
    #Converting "game_date" column to clean US Date format for accurate error free usage.
    df_mlb["game_date"] = pd.to_datetime(df_mlb["game_date"])


    # last_start_fp is a very important metric. If a row has an empty value here it could mess all calculations. 
    # So I am using a filter to return a DataFrame that contains last_start_fp valid values 

    df_mlb = df_mlb [ df_mlb["last_start_fp"].notna()]



    return df_mlb

#print(load_clean_data(file_route)) #This is a debugg line just in case during development I have to go back to this function.

df_mlb = load_clean_data(file_route)


class GMBot:

    def __init__(self, csv_file):
        """Cleaning Data before usage"""
        #Creating the memory of the bot
        self.data = load_clean_data(csv_file)
    
    def save_db(self, db_name="mlb_stats.db"):
        """Saving clean DataFrame to a Database 
        to create persistency of data. In the real world
        the MLB would upload data with new stats every day.
        The bot would pick it up, clean, and save to DB
        so it would be up to date all the time"""

        conn = sqlite3.connect(db_name)
        try:
            self.data.to_sql("daily_stats", conn, if_exists="replace", index=False)
            return f"Success. Daily Database has been created"
        except Exception as e:
            return f"Error Saving DB: {e}"
            
        finally:
            conn.close()

    
    def get_hot_streak_pitchers(self, top_n=5):

        """The BOT will execute this function 
        to find the best pitchers in data.
        clean_df is the previously cleaned dataframe 
        and top_n will be the number of pitchers 
        to return in ranking. 
        
        Top_n has a default value because if someone asks: 
        Who are the best pitchers? and doesnt specify a 
        number then the code will crash"""

        #The best pitchers will be over their last season average on most recent game. So last_start_fp has to be over season_avg_fp_prior
        #Also sorting the dataframe and ordering in descending order will make it easier to read
        top_pitchers = self.data[self.data["last_start_fp"] > self.data["season_avg_fp_prior"]].sort_values(by="last_start_fp", ascending=False)
        
        #Top_n will be specified in the interaction
        return top_pitchers.head(top_n)
    
    def find_pitcher(self, name):
        #Managers will be able to find specific player statistics by name, or even just a last name. Ignoring case of strings.
        #Descending order so manager can see last game first on list
        pitcher_info = self.data[self.data["pitcher_name"].str.contains(name, case=False, na=False)].sort_values(by="game_date", ascending=False)

        return pitcher_info
    
# BOT INTANTIATION 

mlb_assistant = GMBot(file_route)

## BOT COMMANDS WITH ASYNC FUNCTIONS AND AWAIT / HANDLERS
## CONTEXT RECEIVES EVERYTHING AFTER /START COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #I will be adding new commands as the bot scalates. In testing phase /stats, /streaks will do.
    await update.message.reply_text(
        "⚾ ¡Welcome Manager! I am your MLB Decision Making Assistant.\n\n"
        "You can use commands like:\n"
        "🔥 /streak - See the top 5 pitchers on a hot streak right now.\n"
        "📊 /stats [Last Name] or [Full Name] - Get the last 5 games of a specific pitcher.\n\n"
        "🧪 Test Examples (Copy & Paste):\n"
        "👉 /stats Skenes\n"
        "👉 /stats Cole\n"
        "👉 /stats Wheeler\n\n"
        "These commands will give you access to up-to-date information on player stats to help you make decisions!"
    )

## Streak Handler - Command /streak
## Returns records of players with a recent streak for decision making
async def streak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    

        top_players = mlb_assistant.get_hot_streak_pitchers()
        #print(top_players) DEBUGG LINE IN CASE I NEED TO SEE HOW DATA LOOKS BEFORE I CHANGE ANYTHING
        #I decided to normalize column names so on Front End the information looks clean and 100% readable for final user
        top_players = top_players.rename(columns=
                            {"game_date": "Game Date", 
                            "pitcher_name" :"Pitcher Name", 
                            "opponent": "Opponent", 
                            "ballpark": "Ballpark", 
                            "fantasy_points": "Fantasy Points", 
                            "last_start_fp": "Last Start Points", 
                            "season_avg_fp_prior": "Prior Season Points", 
                            "streamer_category": "Category"
                            }, 
                        )
        #print(top_players) DEBUGG LINE TO SEE RESULTS ON HOW DATA IS BEING TRANSFORMED BEFORE BEING PRESENTED
        try:
            #I thought the raw response from the Telegram Bot wasnt "beautiful" enough. So I decided to make it look prettier. 
            # Could've tried tabulate or prettytable but that would bring extra libraries to the code when we dont really need them. So I went classic
            # This creates a header, just a simple header
            header = f"{'Pitcher':<18} {'Pts':<5}"
            divider = "-" * 24
            
            # Formatting Each row with padding so they look NICE!
            # <18 means "left-align and pad to 18 characters"
            rows = []
            for _, row in top_players.iterrows():
                name = str(row['Pitcher Name'])[:17]  # Truncate if name is too long Important for a good view
                pts = str(row['Last Start Points'])
                rows.append(f"{name:<18} {pts:<5}")

            # Combining everything on 1 string
            response_text = "\n".join([header, divider] + rows)

            # I used Markdown to wrap ito triple backsticks (not V2 to avoid escaping issues)
            await update.message.reply_text(
                f"🔥 *Pitchers on Streak:*\n```\n{response_text}\n```", 
                parse_mode='Markdown'
            )
            #I like to see what happens in my console so...
            print(f"{response_text}")


        except KeyError:
            await update.message.reply_text(f"There's are no scores available to determine who's on streak at the moment")
    




## Stats Handler - Command /stats

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Capturing what args receives after command /stats (Ex. Max Scherzer)
    if not context.args:
        await update.message.reply_text("Hey Coach! Tell me what player are you trying to get stats from. Example: /stats Clayton Kershaw")
        return
    
    #Accessing the string sent by the user to be dissectionated.
    last_name = context.args[0]
    player_file = mlb_assistant.find_pitcher(last_name)
    
    # print(player_file) DEBUGG LINE TO SEE HOW DATA LOOKS BEFORE CHANGES
    #I decided to normalize column names so on Front End the information looks clean and 100% readable for final user
    player_file = player_file.rename(columns=
                            {"game_date": "Game Date", 
                            "pitcher_name" :"Pitcher Name", 
                            "opponent": "Opponent", 
                            "ballpark": "Ballpark", 
                            "fantasy_points": "Fantasy Points", 
                            "last_start_fp": "Last Start Points", 
                            "season_avg_fp_prior": "Prior Season Points", 
                            "streamer_category": "Category"
                            }, 
                        )
    # print(player_file) DEBUGG TO SEE HOW DATA IS BEING TRANSFORMED    
    if player_file.empty:
        await update.message.reply_text(f"❌ I couldnt find a player with name or last name {last_name} on Roster.")
    else:
        try:
                    # 1. Generate the string from Pandas
                    response_text = player_file[["Game Date", "Pitcher Name", "Last Start Points"]].head(5).to_string(index=False)
                    
                    # Wrapping the text into backsticks again
                    # Using Markdown as parse mode so Telegram recognizes the backticks
                    await update.message.reply_text(
                        f"📊 Last 5 games of {last_name}:\n\n```\n{response_text}\n```",
                        parse_mode='Markdown'
                    )

                    #I liked to see what happens in my console so... DO NOT CHANGE the f-string format... It will print "/n" if done like that
                    print(f"{response_text}")
        except KeyError:
            await update.message.reply_text(f"The player is not on roster")
            


## SWITCH

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("streak", streak))
    app.add_handler(CommandHandler("stats", stats))

    print("🤖 GMlb-Bot is on. Open Telegram and send a message")
    
    app.run_polling() #THIS LINE IS IMPORTANT SO THE SYSTEM CONTINUES TO RUN INDEFINETELY TILL CTRL+C KEYBOARD INTERRUPT