#This library is responsible for connecting to MLB Real Time Data! LETS DO THIS!
import statsapi
#QUICK TEST TO SEE WHAT DATA STRUCTURE THE API RESPONSE HAS SO I CAN STUDY HOW TO TRANSFORM AND USE IN MY BOT
# 1. LOOKING FOR A PLAYER
player_name = "Ohtani"
print(f"Looking for: {player_name}...")

# 2. We ask the MLB API to bring player stats using the lookup_player() func
player_file = statsapi.lookup_player(player_name)

# 3. Printing RAW Data so I can see what it looks like.
print("\nReceived Data:")
print(player_file)

## The data I got is a nested list with dictionaries inside, so a JSON File!... EXCITING!
## I can see the first info I get is the player id number... Meaning the MLB Api doesnt understand
#  names when it comes to pulling statistics. So I will pull it all with an own function that will 
# first extract ID from a player name to be used to pull statistics data later.
# 
# 

def extract_mlb_data(player_data):

    

    #This Dictionary is a Conceptual Dictionary I will use to extract position so I dont need to write a LONG ASS IF/ELIF/ELSE rule to match it.
    #I will also be using this dictionary with .map() so I can normalize a full data frame position column
    mlb_positions = {
                        "P": "Pitcher",
                        "SP": "Starting Pitcher",
                        "RP": "Relief Pitcher",
                        "CP": "Closer",
                        "C": "Catcher",
                        "1B": "First Baseman",
                        "2B": "Second Baseman",
                        "3B": "Third Baseman",
                        "SS": "Shortstop",
                        "LF": "Left Fielder",
                        "CF": "Center Fielder",
                        "RF": "Right Fielder",
                        "OF": "Outfielder",
                        "DH": "Designated Hitter",
                        "TWP": "Two-Way Player",    # The National League  rules changed in 2022... Now Pitchers dont need to bat 
                                                    #so they have the Universal Designated Hitter
                                                    # however this TWP is applied to monsters like Shohei Ohtani... 
                        "PH": "Pinch Hitter",
                        "PR": "Pinch Runner"
                    }
    #Mapping also the MLB Teams ID so I can make it readable for end user. Best is it happening on back 
    # end so front end developing will be easier
    mlb_teams = {
                108: "LA Angels",
                109: "Arizona Diamondbacks",
                110: "Baltimore Orioles",
                111: "Boston Red Sox",
                112: "Chicago Cubs",
                113: "Cincinnati Reds",
                114: "Cleveland Guardians",
                115: "Colorado Rockies",
                116: "Detroit Tigers",
                117: "Houston Astros",
                118: "Kansas City Royals",
                119: "LA Dodgers",
                120: "Washington Nationals",
                121: "New York Mets",
                133: "Oakland Athletics",
                134: "Pittsburgh Pirates",
                135: "San Diego Padres",
                136: "Seattle Mariners",
                137: "San Francisco Giants",
                138: "St. Louis Cardinals",
                139: "Tampa Bay Rays",
                140: "Texas Rangers",
                141: "Toronto Blue Jays",
                142: "Minnesota Twins",
                143: "Philadelphia Phillies",
                144: "Atlanta Braves",
                145: "Chicago White Sox",
                146: "Miami Marlins",
                147: "New York Yankees",
                158: "Milwaukee Brewers"
            }
    
    #I used several player names and I realized not all players have current stats so we need error handling 
    # in case we get an empty response
    try:

        player_info = player_data[0]
        player_team_id = player_info["currentTeam"]["id"]
        player_id = player_info["id"]
    
    except IndexError:
        return f"{player_data} Returned an EMPTY LIST"
    
    #I didnt add error Handling to extract info because I assume if the API returns info, it will be complete... 
    # We will see later what kind of problems we could have, for now it will stay as is.

    #RAW abbreviation from original data
    player_position_abbr = player_info["primaryPosition"]["abbreviation"]
    
    #Thinking on Front-End from the beginning... This will normalize and map the abbrebiation to the position string in the dictionary.
    #Making it 100% readable for non MLB literals...

    if player_position_abbr in mlb_positions:
        player_position = mlb_positions[player_position_abbr]
    
    #Thinking on front end too I am normalizing the MLB Team ID so it is readable 
    #from backend. Making front end developing easier and clean
    if player_team_id in mlb_teams:
        player_team_name = mlb_teams[player_team_id]
  
    #The API function wont work with my player_position normalization so it will use the raw abbreviation player_position_abbr
    #I had to specify the group according to API documentation because as I mentioned in previous 
    # comments pitchers like Ohtani can have more than 1 type of stats. 1 for Pitching and 1 for batting and maybe fielding stats too
    #Initializing all possible variables for stats as None to avoid crashing the program

    pitching_stats = None
    hitting_stats = None
    fielding_stats = None

    if player_position_abbr == "TWP":
        
        try:
            #Will Extract Pitching Stats for the TWP player
            pitching_stats = statsapi.player_stat_data(player_id, group="pitching", type="season")
            #Will Extract Hitting or Batting stats for the TWP player
            hitting_stats = statsapi.player_stat_data(player_id, group="hitting", type="season")
            #Will Extract Fielding stats for the TWP player
            fielding_stats = statsapi.player_stat_data(player_id, group="fielding", type="season")
        except Exception as e:
            return f"{e} Returned an empty list"
        
    #This rule is becauase I assume P stands for pitchers but PH and PR are not pitchers   
    elif "P" in player_position_abbr and player_position_abbr not in ["PH", "PR"]:
        try: 
            # Normal Pitchers(SP, RP, CP): They just pitch
            pitching_stats = statsapi.player_stat_data(player_id, group="pitching", type="season")
            player_stats = statsapi.player_stat_data(player_id, type="season")
        except Exception as e:
            return f"{e} Returned an empty list"
        
    elif player_position_abbr == "DH" or player_position_abbr in ["PH", "PR"]:
        try:
            # Designated Hitters or Relief Hitters: JUST HIT... NO FIELDING STATS NOR PITCHING OC.
            hitting_stats = statsapi.player_stat_data(player_id, group="hitting", type="season")
        except Exception as e:
            return f"{e} Returned an empty list"
    
    else:
        try:
            # The rest of mortals (1B, SS, OF, C...): they hit and they field so we get both stats for them
            hitting_stats = statsapi.player_stat_data(player_id, group="hitting", type="season")
            fielding_stats = statsapi.player_stat_data(player_id, group="fielding", type="season")
        except Exception as e:
            return f"{e} Returned an empty list"        
        

    
    return hitting_stats, pitching_stats, fielding_stats

#For what I can see Data for stats is messy and also returns a lot of metrics... most of them I dont need:
#that we dont need yet so I will be cleaning and extracting with another function. 
# #I will convert to a Panda DataFrame for better handling


print(extract_mlb_data(player_file))

    


