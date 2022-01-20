from requests.exceptions import ConnectionError # used for connecting to HTTP server
import echovr_api                               # importing echovr api information and functions
import json                                     # importing functions for json manipulation
from os import path                             # importing path to see if file exist
import numpy as np                              # importing to be able to calculate velocity from vectors
from datetime import date                       # importing to set time stamps
import time
import logging
import sys

#File location for overlay
overlay_information = 'C:/Users/Treehouse/Documents/Steaming/Information'

# setting IP and port to grab echoVR API data
echovr_api = echovr_api.api.API(base_url="http://127.0.0.1:6721")

# boolean to control overlay writing
overlay_active = False

# tkinter widget to display speed information
display_widget = None

# Setting up file name variables
file_name = 'speed_results.csv'            # base of file name
cast_file_name = 'GameInfo.json'
error_log = 'CrashLog.log'                  # creating log for crash files
today = date.today()                        # getting today's date
today_date = today.strftime('%y_%m_%d_')    # changing date format to be year_month_day
file_open = str(today_date + file_name)     # creating variable to have the entire file name
file_index = 0                              # used to increment files created in the same day
max_time = 10                               # seconds after start that data will be collected
def_time = 2.5                              # time in seconds to write overlay defensive joust

file_info = {                               # putting all file info into dictionary
        'file_directory': 'Results/',
        'file_name': file_name,
        'today': date.today(),
        'today_date': date.today().strftime('%y_%m_%d_'),
        'file_index': 0,
        'first_write': True,                     # flag used to write table index
        'wrote_file': False,                     # flag used to only write the file once
        'error_occured' : False,                 # flag to see if there is a connection error
        'new_file_needed': True
        }
casting_file_Info = {
#    'file_name': cast_file_name
    'file_name': overlay_information + '/' + cast_file_name
}

game_info = {}                         # setting up blank game info dictionary
player_info = {}                       # setting up blank player info dictionary
# flag used for t/s and debugging
test = True                                 # flag to prevent debug print from blowing up read port

def update_widget(new_widget):
    global display_widget
    
    display_widget = new_widget
    return
  
def setup_file_info(file_info):
    file_info['file_open'] = file_info['file_directory'] + str(date.today().strftime('%y_%m_%d_')) + file_info['file_name']
    return

# finds the magnitude of the velocity from vector velocities.
# takes the velocity as a vector and returns the magnitude of that vector
def find_velocity_mag(velocity):

    velocity = np.linalg.norm(velocity)
    return velocity


# creating game_info dictionary
# takes an active dictionary as an argument, clears the data and makes it match our blank_game_info dictionary
def create_game_info(info):

    # clearing dictionary
    info.clear()

    # setting default parameters
    info['max_time'] = max_time         # time after start that data will be collected
    info['current_round'] = 0
    info['team'] = list()              # list of teams
    info['team'].append({              # blue team data
        'present': False,               # are players present
        'num_players': 0,               # number of players
        'team': 'Blue Team',            # name of team
        'team_sign': -1,                # team sign (used in determine direction)
        'team_exit': False,             # has entire team left tunnel
        'team_center': False,           # has entire team crossed half
        'team_disc': False,             # has entire team reached the disc
        'possession':0,
        'shots_taken':0,
        'assists':0,
        'saves':0,
        'steals':0,
        'stuns':0,
        'roundScore': list(),
        'joust_time':0,
        'joust_speed':0
    })
    info['team'][0]['player'] = list()
    
    info['team'].append({              # orange team data
        'present': False,               # are players present
        'num_players': 0,               # number of players
        'team': 'Orange Team',          # name of team
        'team_sign': 1,                 # team sign (used in determine direction)
        'team_exit': False,             # has entire team left tunnel
        'team_center': False,           # has entire team crossed center
        'team_disc': False,              # has entire team reached disc
        'possession':0,
        'shots_taken':0,
        'assists':0,
        'saves':0,
        'steals':0,
        'stuns':0,
        'roundScore': list(),
        'joust_time':0,
        'joust_speed':0
    })
    info['team'][1]['player'] = list()
    
    info['team'].append({              # spectator data (only for completeness, never used)
        'present': False,               # members present (always False)
        'num_players': 0,               # number of players (always 0)
        'team': 'Spectator',            # team name
        'team_sign': 0,                 # team sign (not used)
        'team_exit': True,              # flag always set true
        'team_center': True,            # flag always set true
        'team_disc': True               # flag always set true
    })

    info['name_in_game'] = list()       # list of names of players who are in the game
    info['ran_once'] = False            # flag to determine if the program has ran once
    info['joust_index'] = -1            # index to count the joust, starting at -1 to have first number = 0
    info['joust_name'] = 'joust_0'      # dictionary key name to pull each joust info
    info['disc_position'] = list()      # list of positions the disc
    info['disc_found'] = False          # flag used to see if the disc location has been found
    info['disc_position_z'] = 0         # storing the disc z position for current round
    info['initial_time'] = False        # flag used to see if we have the start time
    info['game_state'] = ''             # current game state the game is in
    info['start_time'] = 0              # start time of the current round
    info['orange_points'] = 0           # orange team points
    info['blue_points'] = 0             # blue team points
    info['game_playing'] = False        # is game currently playing
    info['time']=600
    info['blue_joust']=False
    info['orange_joust']=False


# sets all the flags back to false to run the test again
# takes a dictionary at the level of teams. dict['teams'][index]['players'][index]['name']
def zero_out_player_data(teams_data, game_info):

    # first setting teams exit and teams disc to False
    if 'players' in teams_data[0]:
        game_info['team'][0]['team_disc'] = False
        game_info['team'][0]['team_center'] = False
        game_info['team'][0]['team_exit'] = False
        game_info['team'][0]['joust_time'] = 0
        game_info['team'][0]['joust_speed'] = 0
        game_info['blue_joust'] = False

    if 'players' in teams_data[1]:
        game_info['team'][1]['team_disc'] = False
        game_info['team'][1]['team_center'] = False
        game_info['team'][1]['team_exit'] = False
        game_info['team'][1]['joust_time'] = 0
        game_info['team'][1]['joust_speed'] = 0
        game_info['orange_joust'] = False

    # setting individual player flags to False
    if 'players' in teams_data[0]:
        for player in teams_data[0]['players']:
            player_info[player['name']]['exit_found'] = False
            player_info[player['name']]['center_found'] = False
            player_info[player['name']]['disc_found'] = False
    if 'players' in teams_data[1]:
        for player in teams_data[1]['players']:
            player_info[player['name']]['exit_found'] = False
            player_info[player['name']]['center_found'] = False
            player_info[player['name']]['disc_found'] = False


# This will add any players who are in the game and not in the dictionary to the dictionary
# takes a dictionary at the level of teams. dict['teams'][index]['players'][index]['name']
def creating_player_info(teams_data):

    # making sure players are on the team
    if 'players' in teams_data[0]:
        for player in teams_data[0]['players']:

            # if the player isn't in the dictionary, they will be added.
            if not (player['name'] in player_info):
                player_info[player['name']] = {}
                player_info[player['name']]['exit_found'] = False
                player_info[player['name']]['center_found'] = False
                player_info[player['name']]['disc_found'] = False
                player_info[player['name']]['team_color'] = teams_data[0]['team']
                player_info[player['name']]['data'] = {}

    # making sure players are on the team
    if 'players' in teams_data[1]:
        for player in teams_data[1]['players']:
            if not (player['name'] in player_info):
                player_info[player['name']] = {}
                player_info[player['name']]['exit_found'] = False
                player_info[player['name']]['center_found'] = False
                player_info[player['name']]['disc_found'] = False
                player_info[player['name']]['team_color'] = teams_data[1]['team']
                player_info[player['name']]['data'] = {}

    return

def clear_player_info():
    global player_info

    player_info.clear()

    return

# creating players in game info dictionary
def logPlayers(teams_data, game_info):

    for k in range(2):
      # making sure players are on the team
      if 'players' in teams_data[k]:
          for player in teams_data[k]['players']:
              write = True
              side_switch = False
              for i in range(len(game_info['team'][k]['player'])):
                  if 'name' in game_info['team'][k]['player'][i]:
                      if player['name'] == game_info['team'][k]['player'][i]['name']:
                          write = False
                          break
              if write:
                  # checking to see if player switched sides
                  if 'players' in teams_data[not k]:
                      for i in range(len(game_info['team'][not k]['player'])):
                          if 'name' in game_info['team'][not k]['player'][i]:
                              # person changed sideds
                              if player['name'] == game_info['team'][not k]['player'][i]['name']:
                                  side_switch = True
                                  old_index = i
                                  break
                              
                  if not side_switch:
                      # add new info
                      game_info['team'][k]['player'].append({
                        'name': player['name'],
                        'possession_time': 0,
                        'points': 0,
                        'saves': 0,
                        'goals': 0,
                        'stuns': 0,
                        'passes': 0,
                        'catches': 0,
                        'steals': 0,
                        'blocks': 0,
                        'interceptions': 0,
                        'assists': 0,
                        'shots_taken': 0,
                        'dropped_data': {
                            'possession_time': 0,
                            'points': 0,
                            'saves': 0,
                            'goals': 0,
                            'stuns': 0,
                            'passes': 0,
                            'catches': 0,
                            'steals': 0,
                            'blocks': 0,
                            'interceptions': 0,
                            'assists': 0,
                            'shots_taken': 0,
                            }
                      })
                  else:
                      # player switched sides
                      game_info['team'][k]['player'].append(game_info['team'][not k]['player'].pop(old_index))
                
# expands the dictionary of all players in the game to hold the current joust information
# takes a dictionary at the level of teams. dict['teams'][index]['players'][index]['name']
# also takes in a string for the name of the new joust
# player information is added to the data dictionary
def creating_joust_dict(teams_data, game_info):

    name = game_info['joust_name']

    # checking to make sure team has players on itw
    if 'players' in teams_data[0]:
        for player in teams_data[0]['players']:

            # expands the data dictionary to hold new joust name
            player_info[player['name']]['data'][name] = {}

    # checking to make sure team has players on it
    if 'players' in teams_data[1]:
        for player in teams_data[1]['players']:

            # expands the data dictionary to hold new joust name
            player_info[player['name']]['data'][name] = {}
            
    return
  
# expands the dictionary, but for players that have joined between joust and
# writing of the file, this should remove key value error for joust_X
def buffer_joust_dict(game_info):
    global player_info
  
    name = game_info['joust_name']

    ###I don't think I need this part so I remove team data that is current_status['teams'] passed in
    # # checking to see that everyone has the correct info
    # if 'players' in teams_data[0]:
    #     for player in teams_data[0]['players']:
    #         if name not in player_info[player['name']]['data']:
    #             player_info[player['name']]['disc_found'] = False
    #             player_info[player['name']]['exit_found'] = False
    #             player_info[player['name']]['center_found'] = False
    #
    # if 'players' in teams_data[1]:
    #     for player in teams_data[1]['players']:
    #         if name not in player_info[player['name']]['data']:
    #             player_info[player['name']]['disc_found'] = False
    #             player_info[player['name']]['exit_found'] = False
    #             player_info[player['name']]['center_found'] = False

    for pname in game_info['name_in_game']:
        if name not in player_info[pname]['data']:
            player_info[pname]['disc_found'] = False
            player_info[pname]['exit_found'] = False
            player_info[pname]['center_found'] = False

    if len(game_info['disc_position']) == 0:
        game_info['disc_position'].append("NO DATA")
                
    return

# aligning game info players with the current players in game
def update_stats(current_status, game_info):

  # global overlay_active

  for team in game_info['team']:
    if 'player' in team:
      for player in team['player']:
        for liveTeam in current_status['teams']:
          if 'players' in liveTeam:
            for livePlayer in liveTeam['players']:
              if player['name'] == livePlayer['name']:
                writeStat(player, livePlayer)
  if overlay_active:
      write_gameInfoJson()

# writing stats to game info dictionary
def writeStat(data, copy):
  dropped = False
  if data['stuns'] != 0:
    if data['stuns'] > copy['stats']['stuns']:
        dropped = True
  elif data['passes'] != 0:
    if data['passes'] > copy['stats']['passes']:
        dropped = True
  elif data['catches'] != 0:
    if data['catches'] > copy['stats']['catches']:
        dropped = True

  if not dropped:
      data['possession_time'] = copy['stats']['possession_time']
      data['points'] = copy['stats']['points']
      data['saves'] = copy['stats']['saves']
      data['goals'] = copy['stats']['goals']
      data['stuns'] = copy['stats']['stuns']
      data['passes'] = copy['stats']['passes']
      data['catches'] = copy['stats']['catches']
      data['steals'] = copy['stats']['steals']
      data['blocks'] = copy['stats']['blocks']
      data['interceptions'] = copy['stats']['interceptions']
      data['assists'] = copy['stats']['assists']
      data['shots_taken'] = copy['stats']['shots_taken']
  else:
      data['dropped_data']['possession_time'] += data['possession_time']
      data['dropped_data']['points'] += data['points']
      data['dropped_data']['saves'] += data['saves']
      data['dropped_data']['goals'] += data['goals']
      data['dropped_data']['stuns'] += data['stuns']
      data['dropped_data']['passes'] += data['passes']
      data['dropped_data']['catches'] += data['catches']
      data['dropped_data']['steals'] += data['steals']
      data['dropped_data']['blocks'] += data['blocks']
      data['dropped_data']['interceptions'] += data['interceptions']
      data['dropped_data']['assists'] += data['assists']
      data['dropped_data']['shots_taken'] += data['shots_taken']

      data['possession_time'] = copy['stats']['possession_time']
      data['points'] = copy['stats']['points']
      data['saves'] = copy['stats']['saves']
      data['goals'] = copy['stats']['goals']
      data['stuns'] = copy['stats']['stuns']
      data['passes'] = copy['stats']['passes']
      data['catches'] = copy['stats']['catches']
      data['steals'] = copy['stats']['steals']
      data['blocks'] = copy['stats']['blocks']
      data['interceptions'] = copy['stats']['interceptions'] 
      data['assists'] = copy['stats']['assists']
      data['shots_taken'] = copy['stats']['shots_taken']

# called to write current players in the game most recent joust data onto the csv file
# takes in a boolean to trigger the first write process and returns that flag to be monitored by main function
def write_file(game_info):
    global player_info

    # will use an appending method to keep updating the CSV file. To do this, we will copy the file line by line into
    # a variable, make our modifications, then write the entire file back to the CSV file.

    # need to make sure our variable is blanked out before we start each iteration
    file_text = ''

    first_write = file_info['first_write']
    file_to_open = file_info['file_open']

    # buffer_joust_dict(current_status['teams'], game_info)
    buffer_joust_dict(game_info)

    # have to open file in r+ (w+ will erase the contents of the file before we can read it)
    # therefore, file must already be created before calling function
    with open(file_to_open, 'r+') as active_write:

        # during the first iteration, we want to put all the players names and default info
        if first_write:

            # adding title for player name and what team they are on
            active_write.write('Name, Team Color, \n')

            # looping through the players to get their name and Team Color
            for name in player_info:
                active_write.write(name + ', ' + player_info[name]['team_color'] + ', \n')

            # setting first write flag False now that we have wrote the first part of the file
            first_write = False
            file_info['first_write'] = first_write

        # moving the cursor to the top of the file
        active_write.seek(0)

        # counting the number of lines in the file
        num_lines = len(active_write.readlines())

        # moving cursor back to the top of the file
        active_write.seek(0)

        # looping through the lines of the file
        loop = 0                                # starting the loop at 0

        while loop < num_lines:

            # first we read a line from the file, strip the \n character and store it in a variable
            stripped_line = active_write.readline().strip()

            # first column is the reference for all the other information
            # partition the read line by the ',' and the first string is our reference
            name_str = stripped_line.partition(',')

            # checking to see if the reference is still in the game
            if name_str[0] in game_info['name_in_game']:
          

                # checking to see if the player crossed the disc on this joust
                # if they passed the disc, they had to exit the tunnel and crossed center as well
                if player_info[name_str[0]]['disc_found']:

                    # creating a new variable that is all the previous data plus new data
                    new_line = stripped_line + ' ' + game_info['disc_position'][game_info['joust_index']] + ', ' + str(
                        player_info[name_str[0]]['data'][game_info['joust_name']]['velocity_exit']) \
                               + ', ' + str(player_info[name_str[0]]['data'][game_info['joust_name']]['time_exit']) + \
                               ', ' + str(player_info[name_str[0]]['data'][game_info['joust_name']]['velocity_disc']) \
                               + ', ' + str(player_info[name_str[0]]['data'][game_info['joust_name']]['time_disc'])

                    # checking to see if the player crossed the center on this joust
                    # if they passed the center, they had to exit the tunnel as well
                    if player_info[name_str[0]]['center_found']:
                        # creating a new variable that is all the previous data plus new data
                        new_line += ', ' + str(
                            player_info[name_str[0]]['data'][game_info['joust_name']]['velocity_center']) \
                                    + ', ' + str(
                            player_info[name_str[0]]['data'][game_info['joust_name']]['time_center'])
                    else:

                        new_line += ", Null, Null"

                # checking to see if the players that did not cross the disc, did exit the tunnel
                elif player_info[name_str[0]]['exit_found']:

                    # adding just the exiting the tunnel information onto the existing information (Null for disc info)
                    new_line = stripped_line + ' ' + game_info['disc_position'][game_info['joust_index']] + ', ' + str(
                        player_info[name_str[0]]['data'][game_info['joust_name']]['velocity_exit']) \
                               + ', ' + str(player_info[name_str[0]]['data'][game_info['joust_name']]['time_exit']) + \
                               ', Null, Null'

                    # checking to see if the player crossed the center on this joust
                    # if they passed the center, they had to exit the tunnel as well
                    if player_info[name_str[0]]['center_found']:
                        # creating a new variable that is all the previous data plus new data
                        new_line += ', ' + str(
                            player_info[name_str[0]]['data'][game_info['joust_name']]['velocity_center']) \
                                   + ', ' + str(
                            player_info[name_str[0]]['data'][game_info['joust_name']]['time_center'])
                    else:

                        new_line += ", Null, Null"

                # player is in the game, but didn't exit the tunnel
                else:

                    # adding Null for all velocities and times
                    new_line = stripped_line + ' ' + game_info['disc_position'][game_info['joust_index']] + \
                               ', Null, Null, Null, Null, Null, Null'

                # compiling our new file by adding what we had and the new_line plus a return character to move to the
                # next line
                file_text += new_line + ', \n'
                game_info['name_in_game'].remove(name_str[0])          # removing name from the players in the game list

            # if the reference is our title reference
            elif name_str[0] == 'Name':

                # adding the new headers to the current header of the table
                file_text += stripped_line + ' ' + game_info['joust_name'] + '_Disc Pos, Exit Velocity, Exit Time, ' \
                            'Disc Velocity, Disc Time, Center Velocity, Center Time,\n'

            # player in the table is no longer in the game, filling in Null for all values
            else:
                new_line = stripped_line + 'Null, Null, Null, Null, Null, Null, Null'
                file_text += new_line + ', \n'

            loop += 1                                           # moving to next line in the file

        # after going through the file, if any players are in the game that wasn't on the table already, they will
        # be added now
        while len(game_info['name_in_game']) > 0:
            # print('new_players have entered')                   # debug prompt used to show a new player is in

            # adding the players name and Team Color to the first column
            file_text += game_info['name_in_game'][0] + ', ' + player_info[game_info['name_in_game'][0]]['team_color'] \
                         + ', '

            # need to fill in Null for the missed joust information
            current_num = 0                                     # counter to loop through the joust that were missed
            while current_num < game_info['joust_index']:
                file_text += 'Null, Null, Null, Null, Null, Null, Null,'
                current_num += 1

            # checking to see if player passed the disc
            if player_info[game_info['name_in_game'][0]]['disc_found']:

                # adding all information to the list
                new_line = game_info['disc_position'][game_info['joust_index']] + ', ' + str(
                    player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]['velocity_exit']) + ', '\
                      + str(player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]['time_exit']) + \
                      ', ' + str(player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]['velocity_disc'])\
                      + ', ' \
                      + str(player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]['time_disc'])

                # checking to see if the player crossed the center on this joust
                # if they passed the center, they had to exit the tunnel as well
                if player_info[game_info['name_in_game'][0]]['center_found']:
                    # creating a new variable that is all the previous data plus new data
                    new_line += ', ' + str(
                        player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]['velocity_center']) \
                                + ', ' + str(
                        player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]['time_center'])
                else:

                    new_line += ", Null, Null"

            # if player only exit the tunnel
            elif player_info[game_info['name_in_game'][0]]["exit_found"]:

                # adding exiting stats to the list, Null for disc information
                new_line = game_info['disc_position'][game_info['joust_index']] + ', ' + \
                      str(player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]['velocity_exit']) \
                      + ', ' + \
                      str(player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]['time_exit']) + \
                      ', Null, Null, Null, Null'

                # checking to see if player crossed the center
                if player_info[game_info['name_in_game'][0]]['center_found']:
                    # found a key bug in python. For some reason the key isn't showing up even though it is there when printing dictionary
                    if 'velocity_center' in player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]:
                        # adding all information to the list
                        new_line += ', ' + str(
                                player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]['velocity_center']) \
                                       + ', ' + str(
                                player_info[game_info['name_in_game'][0]]['data'][game_info['joust_name']]['time_center'])
                    else:
                        print("key bug")
                        new_line += ", Null, Null"
                else:

                    new_line += ", Null, Null"

            # player didn't even leave the tunnel, adding Null for velocities and times
            else:
                new_line = game_info['disc_position'][game_info['joust_index']] + ', Null, Null, Null, Null, Null, Null'

            # adding new line to the file with a return character
            file_text += new_line + ', \n'

            # removing name from list of playing characters
            game_info['name_in_game'].remove(game_info['name_in_game'][0])

        # file is complete and ready to be written. Moving cursor to the top of the file and writing over exiting data
        active_write.seek(0)
        active_write.write(file_text)

# creating a new file
def create_new_file():

    # while loop used create a file name that doesn't exist yet
    while path.exists(file_info['file_open']):
        file_info['file_index'] += 1
        file_info['file_open'] = \
            file_info['file_directory'] + str(file_info['today_date'] + str(file_info['file_index']) + '_' + file_info['file_name'])

    # need to create the new file before we can call our writing CSV function
    with open(file_info['file_open'], 'w+'):
        file_info['first_write'] = True

# writing gameIinfo json file
def write_gameInfoJson():
  file_to_open = casting_file_Info['file_name']
  
  with open(file_to_open, 'w+') as active_write:
    json.dump(game_info, active_write, indent=2)
  
  return

def write_widget(string):
  global display_widget
  
  if display_widget != None:
    display_widget.config(state="normal")
    display_widget.insert("end", string + "\n")
    display_widget.yview_pickplace("end")
    display_widget.config(state="disabled")
    
  return

# first part of speed report, it is ran every time.
# checks the game state and verifies it has already ran once.
# this ensures no errors if started in the middle of the match.
# also keeps the players in the game list up to date and the player info 
# dictionary upto date with new people joining in mid match.
def speed_report_every_scan(current_status, game_info):

    game_info['game_state'] = current_status["game_status"]
    game_info['time'] = current_status['game_clock']
    logPlayers(current_status['teams'], game_info)
    if current_status['pause']['paused_state'] == 'paused':
        game_info['game_playing'] = False
    update_stats(current_status, game_info)

    # first iteration of the loop has to start with round_start.
    # waiting for round_start
    if not game_info['ran_once']:
        game_info['game_state'] = current_status["game_status"]
        logPlayers(current_status["teams"], game_info)


        if game_info['game_state'] == "round_start":

            # writing current score to overlay
            game_info['orange_points'] = current_status['orange_points']
            game_info['blue_points'] = current_status['blue_points']
            game_info['time'] = current_status['game_clock']
            game_info['ran_once'] = True
            #write_gameInfoJson();

    # checking to see if we have players on each team
    game_info['team'][0]['present'] = 'players' in current_status['teams'][0]
    game_info['team'][1]['present'] = 'players' in current_status['teams'][1]

    # finding the number of players on the blue team
    if game_info['team'][0]['present']:
        game_info['team'][0]['num_players'] = len(current_status['teams'][0]['players'])
        for player in current_status['teams'][0]['players']:
            if not (player['name'] in game_info['name_in_game']):
                game_info['name_in_game'].append(player['name'])
    else:
        game_info['team'][0]['num_players'] = 0

    # finding the number of players on the orange team
    if game_info['team'][1]['present']:
        game_info['team'][1]['num_players'] = len(current_status['teams'][1]['players'])
        for player in current_status['teams'][1]['players']:
            if not (player['name'] in game_info['name_in_game']):
                game_info['name_in_game'].append(player['name'])
    else:
        game_info['team'][1]['num_players'] = 0

    # if a team doesn't have any players, we do not want to attempt to collect data for that team
    if not game_info['team'][0]['present']:
        game_info['team'][0]['team_disc'] = True
        game_info['team'][0]['team_exit'] = True
    if not game_info['team'][1]['present']:
        game_info['team'][1]['team_disc'] = True
        game_info['team'][1]['team_exit'] = True

    # creating the player info dictionary for all active players
    creating_player_info(current_status["teams"])

    return game_info['ran_once']


# second part of speed report functions. Collects the players speed and 
# position and saves it into the player info dictionary
def speed_report_info_get(current_status, game_info):

    # on the first iteration of playing, we want to grab the disc location
    if not game_info['disc_found']:

        # using this one iteration zone to increment the joust index
        game_info['joust_index'] += 1

        # Pulling the location of the Disc (will tell us if it is Neutral, Blue or Orange)
        game_info['disc_position_z'] = current_status["disc"]["position"][2]     # Z location of the disc

        # appending onto the disc position list
        if game_info['disc_position_z'] == 0:
            game_info['disc_position'].append('Neutral')
        elif game_info['disc_position_z'] < 0:
            game_info['disc_position'].append('Blue')
        else:
            game_info['disc_position'].append('Orange')

        # resetting all the current players flags to begin the testing process
        zero_out_player_data(current_status["teams"], game_info)

        # printing the disc location to monitor for live feed back
        print("Disc Located at " + game_info['disc_position'][game_info['joust_index']])
        write_widget("Disc Located at " + game_info['disc_position'][game_info['joust_index']])
        
        # creating the jousting name used inside the dictionaries
        game_info['joust_name'] = 'joust_' + str(game_info['joust_index'])
        creating_joust_dict(current_status['teams'], game_info)    # calling function to expand dictionaries

        # setting flag to True until the teams return to the tunnels
        game_info['disc_found'] = True

    # checking to see if we have the start time
    if not game_info['initial_time']:

        # finding the clock time when the tunnels open
        game_info['initial_time'] = True
        game_info['start_time'] = current_status['game_clock']

    # going through each team and pulling information for the Exit Velocity and time
    #  if the value has not been found yet
    team_index = 0                                  # starting index (0 is for Blue, 1 is for Orange)

    # iterating through the team information
    for teams in current_status["teams"]:

        # finding the Tunnel Exit Information
        # checking to see if the team has already been found or if the time has elapsed
        if not game_info['team'][team_index]['team_exit'] and \
                (game_info['start_time'] - (current_status['game_clock']) < game_info['max_time']):

            players_found = 0

            # iterating through players on the team
            if "players" in teams:
                for player in teams["players"]:

                    # if the player has not exited yet, we will monitor there position to see when they do
                    if not player_info[player["name"]]['exit_found']:

                        # saving players position
                        pos_z = player['head']['position'][2]

                        # Blue team is has travels in positive z direction
                        if game_info['team'][team_index]['team_sign'] == -1:  # Traveling in the Positive Z direction

                            # once the z is over -40, they have exited the tunnel
                            if pos_z >= -40:

                                # finding teh velocity and saving values into player info
                                velocity_exiting = round(find_velocity_mag(player['velocity']),2)
                                time_exiting = current_status['game_clock']  # Current time after Exiting
                                display_time = round(game_info['start_time'] - time_exiting,2)
                                player_info[player["name"]]['exit_found'] = True
                                player_info[player['name']]['data'][game_info['joust_name']]['velocity_exit'] \
                                    = velocity_exiting
                                player_info[player['name']]['data'][game_info['joust_name']]['time_exit'] = \
                                    display_time

                                # live display of data
                                print(player["name"] + " Exit Velocity = " + str(velocity_exiting) +
                                      " Time to exit tube = " + str(display_time))
                                write_widget(player["name"] + " Exit Velocity = " + str(velocity_exiting) +
                                      " Time to exit tube = " + str(display_time))
                                
                                # incrementing the number of players found by 1
                                players_found += 1


                        # orange team travels in the negative z direction
                        if game_info['team'][team_index]['team_sign'] == 1:

                            # once the z is under 40, they have exited the tunnel
                            if pos_z <= 40:

                                # finding the velocities and saving the values into player info
                                velocity_exiting = round(find_velocity_mag(player['velocity']),2)
                                time_exiting = current_status['game_clock']  # Current time after Exiting
                                display_time = round(game_info['start_time'] - time_exiting,2)
                                player_info[player["name"]]['exit_found'] = True
                                player_info[player['name']]['data'][game_info['joust_name']]['velocity_exit'] = \
                                    velocity_exiting
                                player_info[player['name']]['data'][game_info['joust_name']]['time_exit'] = \
                                    display_time

                                # live display of data
                                print(player["name"] + " Exit Velocity = " + str(velocity_exiting) +
                                      " Time to exit tube = " + str(display_time))
                                write_widget(player["name"] + " Exit Velocity = " + str(velocity_exiting) +
                                      " Time to exit tube = " + str(display_time))
                                
                                # incrementing the number of players found by 1
                                players_found += 1

                    # player was already found, so increase player found by one
                    else:

                        players_found += 1

                # checking to see if either team has found all the players yet
                # if they do, setting the team_exit flag to True
                if team_index == 0:

                    if players_found >= game_info['team'][team_index]['num_players']:
                        game_info['team'][team_index]['team_exit'] = True

                if team_index == 1:

                    if players_found >= game_info['team'][team_index]['num_players']:
                        game_info['team'][team_index]['team_exit'] = True


        # finding the Center Information
        # checking to see if the team has already been found or if the time has elapsed
        if not game_info['team'][team_index]['team_center'] and \
                (game_info['start_time'] - (current_status['game_clock']) < game_info['max_time']):

            players_found = 0

            # iterating through players on the team
            if "players" in teams:
                for player in teams["players"]:

                    # if the player has not crossed the center yet, we will monitor there position to see when they do
                    if not player_info[player["name"]]['center_found']:

                        # saving players position
                        pos_z = player['head']['position'][2]

                        # Blue team is has travels in positive z direction
                        if game_info['team'][team_index][
                            'team_sign'] == -1:  # Traveling in the Positive Z direction

                            # once the z is over 0, they have crossed the center
                            if pos_z >= 0:
                                # finding teh velocity and saving values into player info
                                velocity_center = round(find_velocity_mag(player['velocity']),2)
                                time_center = current_status['game_clock']  # Current time after Exiting
                                display_time = round(game_info['start_time'] - time_center,2)
                                player_info[player["name"]]['center_found'] = True
                                player_info[player['name']]['data'][game_info['joust_name']]['velocity_center'] \
                                    = velocity_center
                                player_info[player['name']]['data'][game_info['joust_name']]['time_center'] = \
                                    display_time

                                # live display of data
                                print(player["name"] + " Velocity at the Center = " + str(velocity_center) +
                                      " Time to center = " + str(display_time))
                                write_widget(player["name"] + " Velocity at the Center = " + str(velocity_center) +
                                      " Time to center = " + str(display_time))
                                
                                # incrementing the number of players found by 1
                                players_found += 1

                        # orange team travels in the negative z direction
                        if game_info['team'][team_index]['team_sign'] == 1:

                            # once the z is under 0, they have crossed the center
                            if pos_z <= 0:
                                # finding the velocities and saving the values into player info
                                velocity_center = round(find_velocity_mag(player['velocity']),2)
                                time_center = current_status['game_clock']  # Current time after crossing center
                                display_time = round(game_info['start_time'] - time_center,2)
                                player_info[player["name"]]['center_found'] = True
                                player_info[player['name']]['data'][game_info['joust_name']]['velocity_center'] = \
                                    round(velocity_center,2)
                                player_info[player['name']]['data'][game_info['joust_name']]['time_center'] = \
                                    round(game_info['start_time'] - time_center,2)

                                # live display of data
                                print(player["name"] + " Velocity at the Center = " + str(velocity_center) +
                                      " Time to cross center = " + str(display_time))
                                write_widget(player["name"] + " Velocity at the Center = " + str(velocity_center) +
                                      " Time to cross center = " + str(display_time))
                                
                                # incrementing the number of players found by 1
                                players_found += 1

                    # player was already found, so increase player found by one
                    else:

                        players_found += 1

                # checking to see if either team has found all the players yet
                # if they do, setting the team_center flag to True
                if team_index == 0:

                    if players_found >= game_info['team'][team_index]['num_players']:
                        game_info['team'][team_index]['team_center'] = True

                if team_index == 1:

                    if players_found >= game_info['team'][team_index]['num_players']:
                        game_info['team'][team_index]['team_center'] = True

        # finding the information at the Disc location
        # checking to see if the team_disc has been found or if the time has elapsed
        if not game_info['team'][team_index]['team_disc'] and \
                (game_info['start_time'] - (current_status['game_clock']) < game_info['max_time']):

            players_found = 0

            # interating through the players
            if "players" in teams:
                for player in teams["players"]:

                    # checking to see if the players info has been found
                    if not player_info[player["name"]]['disc_found']:

                        # grabbing players position
                        pos_z = player['head']['position'][2]

                        # blue team has to travel in the positive z direction
                        if game_info['team'][team_index]['team_sign'] == -1:

                            # if the players current position is equal to or greater than the disc starting
                            # location, the velocities and times are saved
                            if pos_z >= game_info['disc_position_z']:

                                # getting velocity and other information
                                velocity_disc = round(find_velocity_mag(player['velocity']),2)
                                time_disc = current_status['game_clock']
                                display_time = round(game_info['start_time'] - time_disc,2)
                                player_info[player["name"]]['disc_found'] = True
                                player_info[player['name']]['data'][game_info['joust_name']]['velocity_disc'] = \
                                    velocity_disc
                                player_info[player['name']]['data'][game_info['joust_name']]['time_disc'] = \
                                    display_time

                                # live read of the data
                                print(player["name"] + " Velocity at the disc = " + str(velocity_disc) +
                                      " Time to disc = " + str(display_time))
                                write_widget(player["name"] + " Velocity at the disc = " + str(velocity_disc) +
                                      " Time to disc = " + str(display_time))
                                
                                # increment player count by 1
                                players_found += 1

                                if not game_info['blue_joust']:

                                    if game_info['disc_position'][game_info['joust_index']] == 'Orange' and (game_info['start_time'] - time_disc) < def_time:
                                        game_info['team'][0]['joust_time'] = display_time
                                        game_info['team'][0]['joust_speed'] = velocity_disc
                                    elif game_info['disc_position'][game_info['joust_index']] == 'Neutral':
                                        game_info['team'][0]['joust_time'] = display_time
                                        game_info['team'][0]['joust_speed'] = velocity_disc
                                    game_info['blue_joust'] = True
                                    #write_gameInfoJson()

                        # orange team travels in the negative z direction
                        if game_info['team'][team_index]['team_sign'] == 1:

                            # if the players current position is equal to or less than the disc starting
                            # location, the velocities and times are saved
                            if pos_z <= game_info['disc_position_z']:

                                # getting velocity and other information
                                velocity_disc = round(find_velocity_mag(player['velocity']),2)
                                time_disc = current_status['game_clock']  # Current time after Exiting
                                display_time = round(game_info['start_time'] - time_disc,2)
                                player_info[player["name"]]['disc_found'] = True
                                player_info[player['name']]['data'][game_info['joust_name']]['velocity_disc'] = \
                                    velocity_disc
                                player_info[player['name']]['data'][game_info['joust_name']]['time_disc'] = \
                                    display_time

                                # live read of the data
                                print(player["name"] + " Velocity at the disc = " + str(velocity_disc) +
                                      " Time to disc = " + str(display_time))
                                write_widget(player["name"] + " Velocity at the disc = " + str(velocity_disc) +
                                      " Time to disc = " + str(display_time))
                                
                                # increment player count by 1
                                players_found += 1

                                if not game_info['orange_joust']:
                                  if game_info['disc_position'][game_info['joust_index']] == 'Blue' and (game_info['start_time'] - time_disc) < def_time:
                                    game_info['team'][1]['joust_time'] = display_time
                                    game_info['team'][1]['joust_speed'] = velocity_disc
                                  elif game_info['disc_position'][game_info['joust_index']] == 'Neutral':
                                    game_info['team'][1]['joust_time'] = display_time
                                    game_info['team'][1]['joust_speed'] = velocity_disc
                                  game_info['orange_joust'] = True
                                  #write_gameInfoJson()

                    # player has already been found, incrementing count by 1
                    else:

                        players_found += 1

                # checking to see if any team has all the players found yet
                if team_index == 0:

                    if players_found >= game_info['team'][team_index]['num_players']:
                        game_info['team'][team_index]['team_disc'] = True

                if team_index == 1:

                    if players_found >= game_info['team'][team_index]['num_players']:
                        game_info['team'][team_index]['team_disc'] = True

        # incrementing the team to the next team
        team_index += 1


# sequence of speed report program       
def speed_report_structure(current_status, game_info):
    # calling first part of report functions
    ready = speed_report_every_scan(current_status, game_info)

    # checking game states

    if ready:
        # during round stat, set the flags back the starting values
        if game_info['game_state'] == "round_start":                 # This is when players are in the tunnels
            game_info['disc_found'] = False
            game_info['initial_time'] = False
            file_info['wrote_file'] = False

            if file_info['new_file_needed']:
                create_new_file()
                file_info['new_file_needed'] = False


        # during playing, we collect all the data
        elif game_info['game_state'] == "playing":                   # This is when the game is actually playing

            # writes scores for game starting
            if not game_info['game_playing']:
                game_info['orange_points'] = current_status['orange_points']
                game_info['blue_points'] = current_status['blue_points']
                game_info['time'] = current_status['game_clock']
                game_info['game_playing'] = True
                #write_gameInfoJson()

            if file_info['new_file_needed']:
                create_new_file()
                file_info['new_file_needed'] = False

            if file_info['wrote_file']:
                file_info['wrote_file'] = False

            # calling second part of speed report. Collecting player data
            speed_report_info_get(current_status, game_info)

        # game status score, right after the goal is scored
        elif game_info['game_state'] == "score":

            # checking to see if the file has been written, if not, write it now
            if not file_info['wrote_file']:
                write_file(game_info)
                file_info['wrote_file'] = True

            # writing score files for overlay
            if game_info['initial_time']:

                game_info['orange_points'] = current_status['orange_points']
                game_info['blue_points'] = current_status['blue_points']
                game_info['initial_time'] = False
                update_stats(current_status, game_info)

        # game status post_match
        elif game_info['game_state'] == "post_match" or game_info['game_state'] == "pre_match":

            # checking to see if the file has been written in this iteration, if not, do so now
            if not file_info['wrote_file']:
                write_file(game_info)
                file_info['wrote_file'] = True

            # game has ended
            if game_info['game_playing']:
                game_info['game_playing'] = False
                update_stats(current_status, game_info)
                file_info['new_file_needed'] = True

        # game status post_match
        elif game_info['game_state'] == "round_over":

            # checking to see if the file has been written in this iteration, if not, do so now
            if not file_info['wrote_file']:
                write_file(game_info)
                file_info['wrote_file'] = True

            # game has ended
            if (game_info['game_playing']):
                game_info['team'][0]['roundScore'].append(game_info['blue_points'])
                game_info['team'][1]['roundScore'].append(game_info['orange_points'])
                game_info['current_round'] += 1
                game_info['game_playing'] = False
                update_stats(current_status, game_info)

    return

def main():
    global error_log
    global game_info

    if file_info['new_file_needed']:
        if not file_info['error_occured']:
            # creating blank dictionaries
            create_game_info(game_info)

            # calling function to create a new file
            create_new_file()
            file_info['new_file_needed'] = False

    # loop to collect times and velocity data
    while True:
        try:
            # retrieve data from server and check to see what the game status is
            current_status = echovr_api.fetch_state_data()
            speed_report_structure(current_status, game_info)
            if file_info['error_occured']:
                file_info['error_occured'] = False

        # had a lot of KeyError going through the file writing with the dictionaries
        # this is added to make trouble shooting easier
        except (ConnectionError, json.decoder.JSONDecodeError) as e:

            clear_player_info()                      # initializing player info dictionary (all player info is stored here)

            # this did not rewrite the blank_game_info into game_info
            # game_info.clear()
            # game_info = blank_game_info                  # setting up blank game info dictionary

            # attempt two to recreate blank_game_info into game_info
            create_game_info(game_info)
            if not file_info['new_file_needed']:
                file_info['error_occured'] = True
                file_info['new_file_needed'] = True
                # checking to see if the file has been written in this iteration, if not, do so now
                if not file_info['wrote_file']:
                    write_file(game_info)
                    file_info['wrote_file'] = True

            main()

        # log any other error in the crash log
        except:

            logging.exception(sys.exc_info()[0])
            print('error occured')

            # checking to see if the file has been written in this iteration, if not, do so now
            if not file_info['wrote_file']:
                write_file(game_info)
                file_info['wrote_file'] = True

            clear_player_info()                        # initializing player info dictionary (all player info is stored here)

            main()


if __name__ == "__main__":
    # setting up log file
    logging.basicConfig(filename=error_log, level=logging.ERROR)
    setup_file_info(file_info)
    main()

# examples of dictionaries
'''

example_player_info = {                     # initializing player info dictionary (all player info is stored here)
    "player_0": {
        "data": {
          "joust_0": {
            "velocity_exit": 22.32831528172522,
            "time_exit": 0.22358700000000198,
            "velocity_disc": 21.56207239867729,
            "time_disc": 0.8050350000000037
          },
          "joust_1": {
            "velocity_exit": 22.32831528172522,
            "time_exit": 0.22358700000000198,
            "velocity_disc": 21.56207239867729,
            "time_disc": 0.8050350000000037
          }
        },
        "exit_found": True,
        "disc_found": True
      },
      "player_1": {
        "data": {
          "joust_0": {
            "velocity_exit": 13.321660543564418,
            "time_exit": 0.21247500000000485,
            "velocity_disc": 16.58251269169003,
            "time_disc": 0.939152
          },
          "joust_1": {
            "velocity_exit": 13.321660543564418,
            "time_exit": 0.21247500000000485,
            "velocity_disc": 16.58251269169003,
            "time_disc": 0.939152
          }
        },
        "exit_found": True,
        "disc_found": True
      },
      "player_2": {
        "data": {
          "joust_0": {
            "velocity_exit": 10.052622593269879,
            "time_exit": 1.3303259999999995,
            "velocity_disc": 9.748612614885273,
            "time_disc": 2.5709990000000005
          },
          "joust_1": {
            "velocity_exit": 10.052622593269879,
            "time_exit": 1.3303259999999995,
            "velocity_disc": 9.748612614885273,
            "time_disc": 2.5709990000000005
          }
        },
        "exit_found": True,
        "disc_found": True
      },
      "player_3": {
        "data": {
          "joust_0": {
            "velocity_exit": 17.489090199117967,
            "time_exit": 0.17895200000000244,
            "velocity_disc": 16.675856383376537,
            "time_disc": 0.9056290000000047
          },
          "joust_1": {
            "velocity_exit": 17.489090199117967,
            "time_exit": 0.17895200000000244,
            "velocity_disc": 16.675856383376537,
            "time_disc": 0.9056290000000047
          }
        },
        "exit_found": True,
        "disc_found": True
      },
      "player_4": {
        "data": {
          "joust_0": {
            "velocity_exit": 15.330681545858324,
            "time_exit": 0.9056290000000047
          },
          "joust_1": {
            "velocity_exit": 15.330681545858324,
            "time_exit": 0.9056290000000047
          }
        },
        "exit_found": True,
        "disc_found": False
      },
      "player_5": {
        "data": {
          "joust_0": {
            "velocity_exit": 9.394408205588054,
            "time_exit": 1.5090490000000045
          },
          "joust_1": {
            "velocity_exit": 9.394408205588054,
            "time_exit": 1.5090490000000045
          }
        },
        "exit_found": True,
        "disc_found": False
      },
      "player_6": {
        "data": {
          "joust_0": {
            "velocity_exit": 10.134681743055575,
            "time_exit": 1.341422999999999
          },
          "joust_1": {
            "velocity_exit": 10.134681743055575,
            "time_exit": 1.341422999999999
          }
        },
        "exit_found": True,
        "disc_found": False
      },
      "player_7": {
        "data": {
          "joust_0": {
            "velocity_exit": 17.51033883170403,
            "time_exit": 0.9280400000000029
          },
          "joust_1": {
            "velocity_exit": 17.51033883170403,
            "time_exit": 0.9280400000000029
          }
        },
        "exit_found": True,
        "disc_found": False
      }
}

blank_game_info = {
  'max_time': 10,                           # max time after start
  'team': [                                
    {                                       # blue team info
      'present': False,                     # are players present
      'num_players': 0,                     # number of players
      'team': 'Blue Team',                  # name of team
      'team_sign': -1,                      # team sign (used in determine direction)
      'team_exit': False,                   # has entire team left tunnel
      'team_disc': False,                   # has entire team reached the disc
      'player':[{
        "possession_time": 0,
        "points": 0,
        "saves": 0,
        "goals": 0,
        "stuns": 0,
        "passes": 0,
        "catches": 0,
        "steals": 0,
        "blocks": 0,
        "interceptions": 0,
        "assists": 0,
        "shots_taken": 0,
        'name':'player1',
        'dropped_data': {
          'possession_time': 0,
          'points': 0,
          'saves': 0,
          'goals': 0,
          'stuns': 0,
          'passes': 0,
          'catches': 0,
          'steals': 0,
          'blocks': 0,
          'interceptions': 0,
          'assists': 0,
          'shots_taken': 0,
      }
      }],
      'possession':0,
      'shots_taken':0,
      'assists':0,
      'saves':0,
      'steals':0,
      'stuns':0,
      'round1Score':0,
      'round2Score':0,
      'round3Score':0,
      'joust_time':0,
      'joust_speed':0
    },
    {                                       # orange team info
      'present': False,                     # are players present
      'num_players': 0,                     # number of players
      'team': 'Orange Team',                # name of team
      'team_sign': 1,                       # team sign (used in determine direction)
      'team_exit': False,                   # has entire team left tunnel
      'team_disc': False                    # has entire team reached disc
      'player':[{
        "possession_time": 0,
        "points": 0,
        "saves": 0,
        "goals": 0,
        "stuns": 0,
        "passes": 0,
        "catches": 0,
        "steals": 0,
        "blocks": 0,
        "interceptions": 0,
        "assists": 0,
        "shots_taken": 0,
        'name':'player1',
        'dropped_data': {
          'possession_time': 0,
          'points': 0,
          'saves': 0,
          'goals': 0,
          'stuns': 0,
          'passes': 0,
          'catches': 0,
          'steals': 0,
          'blocks': 0,
          'interceptions': 0,
          'assists': 0,
          'shots_taken': 0,
      }
      }],
      'possession':0,
      'shots_taken':0,
      'assists':0,
      'saves':0,
      'steals':0,
      'stuns':0,
      'round1Score':0,
      'round2Score':0,
      'round3Score':0,
      'joust_time':0,
      'joust-speed':0
    },
    {                                       # spectate team info
      'present': False,                     # members present (always False)
      'num_players': 0,                     # number of players (always 0)
      'team': 'Spectator',                  # team name
      'team_sign': 0,                       # team sign (not used)
      'team_exit': True,                    # flag always set true
      'team_disc': True                     # flag always set true
    }
  ],
  'name_in_game': list(),                   # list of players in the game
  'ran_once': False,                        # flag to tell if program ran once yet
  'joust_index': -1,                        # starting joust index (0 after incrementing)
  'joust_name': 'joust_0',                  # name used in player info
  'disc_position': list(),                  # list of disc locations in game
  'disc_found': False,                      # flag used to grab disc location after score
  'disc_position_z': 0,
  'initial_time': False,                    # flag used to grab start time
  'game_state': '',                         # current state the game is in
  'start_time': 0                           # time round started
  'game_playing': False,
  'orange_score': 0,
  'blue_score': 0,
  'time':600,
  'blue_joust': False,
  'orange_joust': False
}


current_status = {
  "disc": {
    "position": [
      0.245,
      -0.57900006,
      36.030003
    ],
    "forward": [
      0.001,
      -0.001,
      1.0
    ],
    "left": [
      1.0,
      0.001,
      -0.001
    ],
    "up": [
      -0.001,
      1.0,
      0.001
    ],
    "velocity": [
      0.0,
      0.0,
      0.0
    ],
    "bounce_count": 0
  },
  "sessionid": "191D2CD1-8BB6-450A-ABAB-CDA962FC3A3B",
  "orange_team_restart_request": 0,
  "sessionip": "107.6.72.92",
  "game_status": "score",
  "game_clock_display": "03:37.16",
  "game_clock": 217.16818,
  "match_type": "Echo_Arena",
  "map_name": "mpl_arena_a",
  "client_name": "StufMuff",
  "player": {
    "vr_left": [
      1.0,
      0.0,
      0.0
    ],
    "vr_position": [
      0.0,
      0.0,
      0.0
    ],
    "vr_forward": [
      0.0,
      0.0,
      1.0
    ],
    "vr_up": [
      0.0,
      1.0,
      0.0
    ]
  },
  "orange_points": 2,
  "private_match": False
  ,
  "possession": [
    1,
    0
  ],
  "tournament_match": False
  ,
  "blue_team_restart_request": 0,
  "blue_points": 2,
  "last_score": {
    "disc_speed": 0.0,
    "team": "blue",
    "goal_type": "SELF GOAL",
    "point_amount": 2,
    "distance_thrown": 2.2801604,
    "person_scored": "Ceaser-",
    "assist_scored": "[INVALID]"
  },
  "teams": [
    {
      "players": [
        {
          "rhand": {
            "pos": [
              0.0060000001,
              4.145,
              26.502001
            ],
            "forward": [
              -0.88800007,
              0.45300001,
              -0.081
            ],
            "left": [
              0.38800001,
              0.64400005,
              -0.65900004
            ],
            "up": [
              -0.24600001,
              -0.61700004,
              -0.74700004
            ]
          },
          "playerid": 0,
          "name": "R1sen",
          "userid": 2588168867865624,
          "stats": {
            "possession_time": 1.9672594,
            "points": 0,
            "saves": 0,
            "goals": 0,
            "stuns": 4,
            "passes": 0,
            "catches": 0,
            "steals": 1,
            "blocks": 0,
            "interceptions": 0,
            "assists": 0,
            "shots_taken": 1
          },
          "number": 8,
          "level": 50,
          "stunned": False
          ,
          "ping": 50,
          "invulnerable": False
          ,
          "head": {
            "position": [
              0.108,
              4.1280003,
              26.433001
            ],
            "forward": [
              0.53000003,
              0.37100002,
              0.76200002
            ],
            "left": [
              0.81000006,
              0.044000003,
              -0.58500004
            ],
            "up": [
              -0.25,
              0.92800003,
              -0.27800003
            ]
          },
          "possession": False
          ,
          "body": {
            "position": [
              0.108,
              4.1280003,
              26.433001
            ],
            "forward": [
              0.5,
              -0.029000001,
              0.86500007
            ],
            "left": [
              0.86600006,
              0.033,
              -0.49900001
            ],
            "up": [
              -0.014,
              0.99900007,
              0.042000003
            ]
          },
          "lhand": {
            "pos": [
              0.19600001,
              4.1690001,
              26.349001
            ],
            "forward": [
              0.13700001,
              0.51700002,
              -0.84500003
            ],
            "left": [
              0.84800005,
              -0.50200003,
              -0.17
            ],
            "up": [
              -0.51200002,
              -0.69300002,
              -0.50800002
            ]
          },
          "blocking": False
          ,
          "velocity": [
            -0.0020000001,
            0.0,
            -0.20300001
          ]
        },
        {
          "rhand": {
            "pos": [
              7.1200004,
              1.5460001,
              33.319
            ],
            "forward": [
              -0.43900001,
              -0.56100005,
              -0.70200002
            ],
            "left": [
              -0.52000004,
              -0.47900003,
              0.70700002
            ],
            "up": [
              -0.73300004,
              0.67500001,
              -0.082000002
            ]
          },
          "playerid": 1,
          "name": "Enderslot",
          "userid": 1437120013024299,
          "stats": {
            "possession_time": 11.981951,
            "points": 0,
            "saves": 0,
            "goals": 0,
            "stuns": 1,
            "passes": 0,
            "catches": 0,
            "steals": 0,
            "blocks": 0,
            "interceptions": 0,
            "assists": 0,
            "shots_taken": 1
          },
          "number": 51,
          "level": 51,
          "stunned": False
          ,
          "ping": 41,
          "invulnerable": False
          ,
          "head": {
            "position": [
              6.9680004,
              2.171,
              33.445
            ],
            "forward": [
              -0.28800002,
              -0.091000006,
              -0.95300007
            ],
            "left": [
              -0.95600003,
              -0.037,
              0.29200003
            ],
            "up": [
              -0.062000003,
              0.99500006,
              -0.077000007
            ]
          },
          "possession": False
          ,
          "body": {
            "position": [
              6.9680004,
              2.171,
              33.445
            ],
            "forward": [
              -0.33800003,
              -0.0020000001,
              -0.94100004
            ],
            "left": [
              -0.94100004,
              -0.001,
              0.33800003
            ],
            "up": [
              -0.001,
              1.0,
              -0.001
            ]
          },
          "lhand": {
            "pos": [
              6.6990004,
              1.7760001,
              33.336002
            ],
            "forward": [
              -0.60700005,
              0.69500005,
              -0.38500002
            ],
            "left": [
              0.51500005,
              0.71300006,
              0.47500002
            ],
            "up": [
              0.60500002,
              0.090000004,
              -0.79100001
            ]
          },
          "blocking": False
          ,
          "velocity": [
            1.103,
            0.53000003,
            -1.8830001
          ]
        },
        {
          "rhand": {
            "pos": [
              -0.89600003,
              0.68400002,
              28.625002
            ],
            "forward": [
              -0.42600003,
              -0.70900005,
              0.56200004
            ],
            "left": [
              0.61900002,
              -0.68100005,
              -0.39000002
            ],
            "up": [
              0.65900004,
              0.18200001,
              0.73000002
            ]
          },
          "playerid": 2,
          "name": "SnowBourn",
          "userid": 3002153439860504,
          "stats": {
            "possession_time": 11.736107,
            "points": 0,
            "saves": 0,
            "goals": 0,
            "stuns": 2,
            "passes": 0,
            "catches": 0,
            "steals": 0,
            "blocks": 0,
            "interceptions": 0,
            "assists": 0,
            "shots_taken": 2
          },
          "number": 7,
          "level": 50,
          "stunned": False
          ,
          "ping": 44,
          "invulnerable": False
          ,
          "head": {
            "position": [
              -0.73000002,
              1.46,
              28.419001
            ],
            "forward": [
              0.54800004,
              -0.031000001,
              0.83600003
            ],
            "left": [
              0.83500004,
              -0.037,
              -0.54900002
            ],
            "up": [
              0.048,
              0.99900007,
              0.0050000004
            ]
          },
          "possession": False
          ,
          "body": {
            "position": [
              -0.73000002,
              1.46,
              28.419001
            ],
            "forward": [
              0.51900005,
              0.001,
              0.85500002
            ],
            "left": [
              0.85500002,
              -0.0020000001,
              -0.51900005
            ],
            "up": [
              0.001,
              1.0,
              -0.0020000001
            ]
          },
          "lhand": {
            "pos": [
              -0.57100004,
              0.63300002,
              28.415001
            ],
            "forward": [
              0.53900003,
              -0.81900007,
              0.19700001
            ],
            "left": [
              0.79400003,
              0.57300001,
              0.20600002
            ],
            "up": [
              -0.28200001,
              0.045000002,
              0.95800006
            ]
          },
          "blocking": False
          ,
          "velocity": [
            -0.24600001,
            0.24200001,
            -0.34400001
          ]
        },
        {
          "rhand": {
            "pos": [
              -3.3710001,
              1.4260001,
              15.719001
            ],
            "forward": [
              0.069000006,
              0.147,
              -0.98700005
            ],
            "left": [
              -0.99800003,
              0.023000002,
              -0.066
            ],
            "up": [
              0.013,
              0.98900002,
              0.148
            ]
          },
          "playerid": 5,
          "name": "Zexroms",
          "userid": 2504094623025307,
          "stats": {
            "possession_time": 3.0400755,
            "points": 0,
            "saves": 0,
            "goals": 0,
            "stuns": 1,
            "passes": 0,
            "catches": 0,
            "steals": 0,
            "blocks": 0,
            "interceptions": 0,
            "assists": 0,
            "shots_taken": 0
          },
          "number": 0,
          "level": 50,
          "stunned": False
          ,
          "ping": 53,
          "invulnerable": False
          ,
          "head": {
            "position": [
              -3.4400001,
              1.9220001,
              15.915001
            ],
            "forward": [
              -0.049000002,
              -0.35900003,
              -0.93200004
            ],
            "left": [
              -0.99800003,
              0.045000002,
              0.035
            ],
            "up": [
              0.030000001,
              0.93200004,
              -0.36100003
            ]
          },
          "possession": False
          ,
          "body": {
            "position": [
              -3.4400001,
              1.9220001,
              15.915001
            ],
            "forward": [
              -0.024,
              -0.0020000001,
              -1.0
            ],
            "left": [
              -1.0,
              0.0,
              0.024
            ],
            "up": [
              -0.001,
              1.0,
              -0.0020000001
            ]
          },
          "lhand": {
            "pos": [
              -3.5780001,
              1.309,
              15.760001
            ],
            "forward": [
              -0.26300001,
              -0.38100001,
              -0.88600004
            ],
            "left": [
              -0.92500007,
              0.36000001,
              0.12
            ],
            "up": [
              0.273,
              0.85200006,
              -0.44700003
            ]
          },
          "blocking": False
          ,
          "velocity": [
            -0.27100003,
            0.41800001,
            -5.0480003
          ]
        }
      ],
      "team": "BLUE TEAM",
      "possession": False
      ,
      "stats": {
        "points": 0,
        "possession_time": 28.725393,
        "interceptions": 0,
        "blocks": 0,
        "steals": 1,
        "catches": 0,
        "passes": 0,
        "saves": 0,
        "goals": 0,
        "stuns": 8,
        "assists": 0,
        "shots_taken": 4
      }
    },
    {
      "players": [
        {
          "rhand": {
            "pos": [
              -8.0620003,
              -0.98600006,
              -5.8130002
            ],
            "forward": [
              -0.017000001,
              -0.97400004,
              -0.22400001
            ],
            "left": [
              -0.81300002,
              -0.11700001,
              0.57100004
            ],
            "up": [
              -0.583,
              0.192,
              -0.79000002
            ]
          },
          "playerid": 3,
          "name": "Ceaser-",
          "userid": 4043903475627702,
          "stats": {
            "possession_time": 8.0362959,
            "points": 0,
            "saves": 2,
            "goals": 0,
            "stuns": 1,
            "passes": 0,
            "catches": 0,
            "steals": 0,
            "blocks": 0,
            "interceptions": 0,
            "assists": 0,
            "shots_taken": 0
          },
          "number": 23,
          "level": 50,
          "stunned": False
          ,
          "ping": 36,
          "invulnerable": False
          ,
          "head": {
            "position": [
              -8.2230005,
              -0.053000003,
              -5.7930002
            ],
            "forward": [
              -0.53900003,
              -0.033,
              -0.84200007
            ],
            "left": [
              -0.84200007,
              0.054000001,
              0.537
            ],
            "up": [
              0.028000001,
              0.99800003,
              -0.057000004
            ]
          },
          "possession": True
          ,
          "body": {
            "position": [
              -8.2230005,
              -0.053000003,
              -5.7930002
            ],
            "forward": [
              -0.53900003,
              -0.001,
              -0.84200007
            ],
            "left": [
              -0.84200007,
              -0.001,
              0.53900003
            ],
            "up": [
              -0.0020000001,
              1.0,
              -0.001
            ]
          },
          "lhand": {
            "pos": [
              -8.2330008,
              -0.86600006,
              -5.3780003
            ],
            "forward": [
              0.27500001,
              -0.82100004,
              -0.5
            ],
            "left": [
              -0.085000001,
              0.49800003,
              -0.86300004
            ],
            "up": [
              0.95800006,
              0.28,
              0.068000004
            ]
          },
          "blocking": False
          ,
          "velocity": [
            -2.1170001,
            0.51600003,
            -4.3010001
          ]
        },
        {
          "rhand": {
            "pos": [
              0.21200001,
              3.0760002,
              29.043001
            ],
            "forward": [
              -0.13800001,
              -0.19600001,
              0.97100008
            ],
            "left": [
              0.97800004,
              0.12900001,
              0.16500001
            ],
            "up": [
              -0.15800001,
              0.97200006,
              0.17400001
            ]
          },
          "playerid": 4,
          "name": "UltimateVR420",
          "userid": 2846841775428747,
          "stats": {
            "possession_time": 3.7109091,
            "points": 0,
            "saves": 0,
            "goals": 0,
            "stuns": 1,
            "passes": 0,
            "catches": 0,
            "steals": 0,
            "blocks": 0,
            "interceptions": 0,
            "assists": 0,
            "shots_taken": 0
          },
          "number": 0,
          "level": 50,
          "stunned": False
          ,
          "ping": 95,
          "invulnerable": False
          ,
          "head": {
            "position": [
              0.35600001,
              3.5350001,
              29.041002
            ],
            "forward": [
              -0.12900001,
              -0.11300001,
              0.98500007
            ],
            "left": [
              0.98600006,
              -0.12,
              0.115
            ],
            "up": [
              0.105,
              0.98600006,
              0.127
            ]
          },
          "possession": False
          ,
          "body": {
            "position": [
              0.35600001,
              3.5350001,
              29.041002
            ],
            "forward": [
              -0.22800002,
              0.001,
              0.97400004
            ],
            "left": [
              0.97400004,
              0.0020000001,
              0.22800002
            ],
            "up": [
              -0.001,
              1.0,
              -0.001
            ]
          },
          "lhand": {
            "pos": [
              0.49500003,
              2.9400001,
              29.293001
            ],
            "forward": [
              0.56400001,
              -0.40300003,
              0.72100002
            ],
            "left": [
              0.80000001,
              0.48200002,
              -0.35700002
            ],
            "up": [
              -0.20400001,
              0.77800006,
              0.59400004
            ]
          },
          "blocking": False
          ,
          "velocity": [
            -0.11800001,
            -0.28100002,
            1.8060001
          ]
        },
        {
          "rhand": {
            "pos": [
              2.9920001,
              4.3380003,
              29.716002
            ],
            "forward": [
              -0.59300005,
              0.22200002,
              0.77400005
            ],
            "left": [
              0.78200006,
              0.38700002,
              0.48800004
            ],
            "up": [
              -0.19100001,
              0.89500004,
              -0.40300003
            ]
          },
          "playerid": 6,
          "name": "Boosty_",
          "userid": 2767739789952823,
          "stats": {
            "possession_time": 16.922251,
            "points": 2,
            "saves": 1,
            "goals": 0,
            "stuns": 2,
            "passes": 0,
            "catches": 0,
            "steals": 0,
            "blocks": 0,
            "interceptions": 0,
            "assists": 0,
            "shots_taken": 2
          },
          "number": 42,
          "level": 50,
          "stunned": False
          ,
          "ping": 52,
          "invulnerable": False
          ,
          "head": {
            "position": [
              3.5000002,
              4.7000003,
              29.565001
            ],
            "forward": [
              -0.44200003,
              -0.22600001,
              0.86800003
            ],
            "left": [
              0.86400002,
              0.15300001,
              0.48000002
            ],
            "up": [
              -0.24100001,
              0.96200007,
              0.12800001
            ]
          },
          "possession": False
          ,
          "body": {
            "position": [
              3.5000002,
              4.7000003,
              29.565001
            ],
            "forward": [
              -0.23600002,
              -0.0020000001,
              0.97200006
            ],
            "left": [
              0.97100008,
              -0.024,
              0.23600002
            ],
            "up": [
              0.023000002,
              1.0,
              0.0070000002
            ]
          },
          "lhand": {
            "pos": [
              3.9850001,
              4.0230002,
              29.907001
            ],
            "forward": [
              0.34500003,
              -0.5,
              0.79400003
            ],
            "left": [
              0.92000002,
              0.34600002,
              -0.18100001
            ],
            "up": [
              -0.185,
              0.79400003,
              0.58000004
            ]
          },
          "blocking": False
          ,
          "velocity": [
            3.1810002,
            0.57100004,
            3.5750003
          ]
        },
        {
          "rhand": {
            "pos": [
              -0.39000002,
              7.3720002,
              23.223001
            ],
            "forward": [
              0.36200002,
              -0.81700003,
              -0.44900003
            ],
            "left": [
              0.73800004,
              -0.043000001,
              0.67400002
            ],
            "up": [
              -0.57000005,
              -0.57500005,
              0.58700001
            ]
          },
          "playerid": 7,
          "name": "M00nface",
          "userid": 2011070038974190,
          "stats": {
            "possession_time": 12.283728,
            "points": 0,
            "saves": 0,
            "goals": 0,
            "stuns": 3,
            "passes": 0,
            "catches": 0,
            "steals": 0,
            "blocks": 0,
            "interceptions": 0,
            "assists": 1,
            "shots_taken": 0
          },
          "number": 32,
          "level": 50,
          "stunned": False
          ,
          "ping": 99,
          "invulnerable": False
          ,
          "head": {
            "position": [
              -0.37200001,
              7.5310001,
              23.612001
            ],
            "forward": [
              -0.069000006,
              0.098000005,
              -0.99300003
            ],
            "left": [
              0.96600002,
              0.25500003,
              -0.042000003
            ],
            "up": [
              0.24900001,
              -0.96200007,
              -0.112
            ]
          },
          "possession": False
          ,
          "body": {
            "position": [
              -0.37200001,
              7.5310001,
              23.612001
            ],
            "forward": [
              0.073000006,
              -0.42000002,
              -0.90500003
            ],
            "left": [
              0.93100005,
              0.35500002,
              -0.089000002
            ],
            "up": [
              0.35800001,
              -0.83500004,
              0.41700003
            ]
          },
          "lhand": {
            "pos": [
              -0.42300001,
              8.1530008,
              23.284
            ],
            "forward": [
              -0.71800005,
              0.35000002,
              -0.60200006
            ],
            "left": [
              -0.52900004,
              0.28600001,
              0.79900002
            ],
            "up": [
              0.45200002,
              0.89200002,
              -0.020000001
            ]
          },
          "blocking": False
          ,
          "velocity": [
            -0.20700002,
            -0.027000001,
            -3.7530003
          ]
        }
      ],
      "team": "ORANGE TEAM",
      "possession": True
      ,
      "stats": {
        "points": 2,
        "possession_time": 40.953186,
        "interceptions": 0,
        "blocks": 0,
        "steals": 0,
        "catches": 0,
        "passes": 0,
        "saves": 3,
        "goals": 0,
        "stuns": 7,
        "assists": 1,
        "shots_taken": 2
      }
    },
    {
      "players": [
        {
          "rhand": {
            "pos": [
              -0.25,
              0.0,
              -9.6200008
            ],
            "forward": [
              0.0,
              0.0,
              1.0
            ],
            "left": [
              1.0,
              0.0,
              0.0
            ],
            "up": [
              0.0,
              1.0,
              0.0
            ]
          },
          "playerid": 8,
          "name": "StufMuff",
          "userid": 1806063112754467,
          "stats": {
            "possession_time": 0.0,
            "points": 0,
            "saves": 0,
            "goals": 0,
            "stuns": 0,
            "passes": 0,
            "catches": 0,
            "steals": 0,
            "blocks": 0,
            "interceptions": 0,
            "assists": 0,
            "shots_taken": 0
          },
          "number": 0,
          "level": 50,
          "stunned": False
          ,
          "ping": 60,
          "invulnerable": False
          ,
          "head": {
            "position": [
              0.0,
              0.0,
              -10.0
            ],
            "forward": [
              0.0,
              0.0,
              1.0
            ],
            "left": [
              1.0,
              0.0,
              0.0
            ],
            "up": [
              0.0,
              1.0,
              0.0
            ]
          },
          "possession": False
          ,
          "body": {
            "position": [
              0.0,
              0.0,
              -10.0
            ],
            "forward": [
              0.0,
              0.0,
              1.0
            ],
            "left": [
              1.0,
              0.0,
              0.0
            ],
            "up": [
              0.0,
              1.0,
              0.0
            ]
          },
          "lhand": {
            "pos": [
              0.25,
              -0.25,
              -10.0
            ],
            "forward": [
              0.0,
              0.0,
              1.0
            ],
            "left": [
              1.0,
              0.0,
              0.0
            ],
            "up": [
              0.0,
              1.0,
              0.0
            ]
          },
          "blocking": False
          ,
          "velocity": [
            0.0,
            0.0,
            0.0
          ]
        },
        {
          "rhand": {
            "pos": [
              -0.51000005,
              0.88000005,
              35.018002
            ],
            "forward": [
              -0.15100001,
              -0.95800006,
              0.24400002
            ],
            "left": [
              -0.97700006,
              0.18100001,
              0.109
            ],
            "up": [
              -0.149,
              -0.22200002,
              -0.96300006
            ]
          },
          "playerid": 9,
          "name": "www.ignitevr.gg",
          "userid": 2540488886071982,
          "stats": {
            "possession_time": 0.0,
            "points": 0,
            "saves": 0,
            "goals": 0,
            "stuns": 0,
            "passes": 0,
            "catches": 0,
            "steals": 0,
            "blocks": 0,
            "interceptions": 0,
            "assists": 0,
            "shots_taken": 0
          },
          "number": 0,
          "level": 1,
          "stunned": False
          ,
          "ping": 72,
          "invulnerable": False
          ,
          "head": {
            "position": [
              -0.69400001,
              1.8060001,
              34.689003
            ],
            "forward": [
              0.039000001,
              -0.141,
              -0.98900002
            ],
            "left": [
              -0.99500006,
              0.082000002,
              -0.051000003
            ],
            "up": [
              0.089000002,
              0.98700005,
              -0.13700001
            ]
          },
          "possession": False
          ,
          "body": {
            "position": [
              -0.69400001,
              1.8060001,
              34.689003
            ],
            "forward": [
              0.13800001,
              -0.001,
              -0.99000007
            ],
            "left": [
              -0.99000007,
              -0.0020000001,
              -0.13800001
            ],
            "up": [
              -0.001,
              1.0,
              -0.001
            ]
          },
          "lhand": {
            "pos": [
              -0.87300003,
              0.96300006,
              34.638
            ],
            "forward": [
              0.33000001,
              -0.78600001,
              -0.52200001
            ],
            "left": [
              -0.89100003,
              -0.077000007,
              -0.44700003
            ],
            "up": [
              0.31100002,
              0.61300004,
              -0.72600001
            ]
          },
          "blocking": False
          ,
          "velocity": [
            -0.24400002,
            -0.78500003,
            -4.1140003
          ]
        }
      ],
      "team": "SPECTATORS",
      "possession": False
      ,
      "stats": {
        "points": 0,
        "possession_time": 0.0,
        "interceptions": 0,
        "blocks": 0,
        "steals": 0,
        "catches": 0,
        "passes": 0,
        "saves": 0,
        "goals": 0,
        "stuns": 0,
        "assists": 0,
        "shots_taken": 0
      }
    }
]}

'''