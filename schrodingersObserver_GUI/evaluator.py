from requests.exceptions import ConnectionError     # used for connecting to HTTP server
import echovr_api                                   # importing echovr api information and functions
import json                                         # importing functions for json manipulation
from os import path, makedirs                       # importing path to see if file exist
import numpy as np                                  # importing to be able to calculate velocity from vectors
import pandas as pd
import threading as th                              # used for multi threading
from datetime import date                           # importing to set time stamps
import time as time_mod
import logging
import sys
import traceback                                    # used for error printing
import copy                                         # used to copy dictionaries

'''
progress notes:
    **Does headbutt give poss to player and team? Specifically off offense joust**
    
  Version 2: 
    Stack control:
      grade on who should be staking with who
      points for turns in stack (complete)
    Grade passes by trajectory(complete)
    Update Record_Recovery to verify only one person is stopping stacks(complete)
    Calculate weither throw was a shot
    
    dual threading seems to be working
      non-threading would range between 0.3 to 3-4 seconds (sometimes 8)
      threading was consistant at 0.3
    
    
    Thoughts:
      Move center farther then edge of tunnel? Maybe apple? or the wedge?
        keeping this as the same for now.
      Clear is only considered if disc bounces at least once(complete)
      Add pre_clear and don't punish for not being a pass option if it is the first pass
        after going through the middle(complete)
      when poss changes to None, punish for a bad pass(complete)
        
      Don't punish passer if receiver misses the disc(1 m from disc) (complete)
      set in grade pass -> add inteded receiver (completed)
        if want to make sure direct line is open, need to let thread run.
        if pass would have been 2 meter of person if they took no action, they will be
          pinalized for missing the disc (completed)
          
    testing:
        Updates:
            Goalie coverage on shot was wrong(corrected)
            clear was wrong (mixed up when it was in defense zone)(corrected)
            Not a successful pass if a clear(corrected)
            Moskyy headbutt at 3:37.8 was instantly counted as a bad pass(corrected)
            Moskyy Shot was still in his hand and was counted as a shot (3:30.84)(corrected)
            4:25:00 penalized for not covering a man on first pass after clear(corrected)
            Can I tell if the pass was a hosbital pass????
                Punish for a slow pass
            Add Poss Time (COMPLETE)
            Add Shot Tracker?
            End of game summary??
                Why You Won, Why You Lost?
            Individual Summary
            Evaluate why player was not in passing lane (dribblers fault or reciever)
            Lane coverage is varable to distance from disc and disc speed(complete)
               Change lane coverage to calculate using math instead of checking points
            added logic for stack control, punish if they miss the disc (round 2 test complete)
            change time, adjusted stack stunning (needs testing) "Tied up with"
'''
multithreading = True

test = False
api_info = {}
# tkinter widget to show log
log_widget = None

# setting IP and port to grab echoVR API data
echovr_api = echovr_api.api.API(base_url="http://127.0.0.1:6721")

# file containing invalid vertices
nvalid_file1 = 'csv/nValidPoints-1.csv'
nvalid_array = pd.read_csv(nvalid_file1).to_numpy()
nvalid_array = nvalid_array.tolist()
index_z = np.array([]).astype('int')

light_coverage = 4                  # global variable to control meters for light coverage
tight_coverage = 2                  # global variable to control meters for tight coverage
defense_zone = 25                   # global variable that shows how deep the disc can be an stacks coverage is still a good idea.
return_time = 5                     # global variable to control seconds allowed to return after poss change
open_distance = [5, 40]             # global array, first element is min distance to be open and 2ed is max
goal_center = np.array([0,0,36])
goal_coverage = 3.5
shot_time = 0.5                     # time used to grade goalie, goalie is punished if time > this time
pocket_size = 0.333                 # plus and minus for a pocket shot
poss_min = 1                        # global variable to set min time to have the disc before max penalty
clear_time = 3                      # seconds before team looses poss
stack_grab = 1                      # seconds between a stack grabs before it is considered broken
exp_disc_speed = 16                 # expected speed on the disc, used to penalize if poss loss and is under this speed

shot_rating = 0.7                   # global variable to control how low shot rating can be
possession_rating = 0.7             # global variable to control how low possession rating can be
clear_rating = 0.7                  # global variable to control how low clear rating can be


# Setting up file name variables
file_name = 'evaluation.csv'                  # base of file name
file_result = 'evaluation_result.csv'                  # base of file name
error_log = 'CrashLog_evaluation.log'
file_info = {                               # putting all file info into dictionary
        'file_directory': 'Results/',
        'file_name': 'evaluation.csv',
        'today': date.today(),
        'today_date': date.today().strftime('%y_%m_%d_'),
        'file_index': 0,
        'file_result': 'evaluation_result.csv',
        'stack_log': 'stack_log.csv',
        'first_write': True,                     # flag used to tell if file has info
        'wrote_file': False,                     # flag used to only write the file once
        'new_file_needed': True,                 # flag to control file creation
        'error_occured' : False                  # flag to see if there is a connection error
        }

#setting up threading object
threading = {
  'threading': multithreading,              # variable that trackes if threading is active
  'pre_threading': False,                   # variable that trackes if threading was active
  'thread_cycle': False,                    # flag used to see if this cycle was threaded
  'poss_loss': list(),                      # flag used to see if this cycle had a poss loss
  'continue': False,                        # flag used to see if queue needs to continue
  'queue': 0,                               # count of queue that is ready
  'disc_location': list(),                  # queue for threading disc locations
  'team_position': list(),                   # queue for threading team locations
  'team_index': list(),                     # queue for threading team index for offense
  'defense_position': list(),                # queue for threading defense locations
  'info': list()                            # queue for game_info
}
lock = th.Lock()

class RestartableThread(th.Thread):
    def __init__(self, *args, **kwargs):
      self._args, self._kwargs = args, kwargs
      super().__init__(*args, **kwargs)
      self.killed = False
    def clone(self, *args, **kwargs):
      return RestartableThread(*args, **kwargs)

    def start(self):
      self.__run_backup = self.run
      self.run = self.__run     
      th.Thread.start(self)

    def __run(self):
      sys.settrace(self.globaltrace)
      self.__run_backup()
      self.run = self.__run_backup

    def globaltrace(self, frame, event, arg):
      if event == 'call':
        return self.localtrace
      else:
        return None

    def localtrace(self, frame, event, arg):
      if self.killed:
        if event == 'line':
          raise SystemExit()
      return self.localtrace

    def kill(self):
      self.killed = True
      return
    

player_info = {}
game_info = {}

def update_widget(new_widget):
    global log_widget
    
    log_widget = new_widget
    return

def setup_file_info(file_info):
    file_info['file_open'] = file_info['file_directory'] + str(date.today().strftime('%y_%m_%d_')) + file_info['file_name']
    file_info['file_result_open'] = file_info['file_directory'] + str(date.today().strftime('%y_%m_%d_')) + file_info['file_result']
    file_info['stack_log_open'] = file_info['file_directory'] + str(date.today().strftime('%y_%m_%d_')) + file_info['stack_log']
    return

# This will add any players who are in the game and not in the dictionary to the dictionary
# takes a dictionary at the level of teams. dict['teams'][index]['players'][index]['name']
###example creating_player_info(current_status["teams"])
def creating_player_info(teams_data):

    # adding to prevent drop players from crashing script
    if "None" not in player_info:
        player_info["None"] = {}
        player_info["None"]['grade_data'] = {}
        player_info["None"]['grade_data']['shot'] = 0
        player_info["None"]['grade_data']['possession'] = 0
        player_info["None"]['grade_data']['poss_time'] = 0
        player_info["None"]['grade_data']['man_coverage'] = 0
        player_info["None"]['grade_data']['lane_coverage'] = 0
        player_info["None"]['grade_data']['change_time'] = 0
        player_info["None"]['grade_data']['clear'] = 0
        player_info["None"]['grade_data']['stack_control'] = 0
        player_info["None"]['grade_data']['stuns'] = 0
        player_info["None"]['grade_data']['steals'] = 0
        player_info["None"]['grade_data']['goalie'] = 0
        player_info["None"]['rating_data'] = {}
        player_info["None"]['rating_data']['shot'] = 1
        player_info["None"]['rating_data']['possession'] = 1
        player_info["None"]['stat_data'] = {}
        player_info["None"]['stat_data']['shot_taken'] = False
        player_info["None"]['stat_data']['shots_taken'] = 0
        player_info["None"]['stat_data']['drop_shots_taken'] = 0
        player_info["None"]['stat_data']['saves'] = 0
        player_info["None"]['stat_data']['drop_saves'] = 0
        player_info["None"]['stat_data']['stuns'] = 0
        player_info["None"]['stat_data']['drop_stuns'] = 0
        player_info["None"]['stat_data']['stunned'] = False
        player_info["None"]['info'] = {}
        player_info["None"]['info']['stacks'] = {}

    # making sure players are on the team
    if 'players' in teams_data[0]:
        for player in teams_data[0]['players']:

            # if the player isn't in the dictionary, they will be added.
            if not (player['name'] in player_info):
                player_info[player['name']] = {}
                player_info[player['name']]['grade_data'] = {}
                player_info[player['name']]['grade_data']['shot'] = 0
                player_info[player['name']]['grade_data']['possession'] = 0
                player_info[player['name']]['grade_data']['poss_time'] = 0
                player_info[player['name']]['grade_data']['man_coverage'] = 0
                player_info[player['name']]['grade_data']['lane_coverage'] = 0
                player_info[player['name']]['grade_data']['change_time'] = 0
                player_info[player['name']]['grade_data']['clear'] = 0
                player_info[player['name']]['grade_data']['stack_control'] = 0
                player_info[player['name']]['grade_data']['stuns'] = 0
                player_info[player['name']]['grade_data']['steals'] = 0
                player_info[player['name']]['grade_data']['goalie'] = 0
                player_info[player['name']]['rating_data'] = {}
                player_info[player['name']]['rating_data']['shot'] = 1
                player_info[player['name']]['rating_data']['possession'] = 1
                player_info[player['name']]['stat_data'] = {}
                player_info[player['name']]['stat_data']['shot_taken'] = False
                player_info[player['name']]['stat_data']['shots_taken'] = 0
                player_info[player['name']]['stat_data']['drop_shots_taken'] = 0
                player_info[player['name']]['stat_data']['saves'] = 0
                player_info[player['name']]['stat_data']['drop_saves'] = 0
                player_info[player['name']]['stat_data']['stuns'] = 0
                player_info[player['name']]['stat_data']['drop_stuns'] = 0
                player_info[player['name']]['stat_data']['stunned'] = False
                player_info[player['name']]['info'] = {}
                player_info[player['name']]['info']['stacks'] = {}
                # this will track how many times the player stacks with another player
                # and how long they were stacked -> count and time
                
    # making sure players are on the team
    if 'players' in teams_data[1]:
        for player in teams_data[1]['players']:
            if not (player['name'] in player_info):
                player_info[player['name']] = {}
                player_info[player['name']]['grade_data'] = {}
                player_info[player['name']]['grade_data']['shot'] = 0
                player_info[player['name']]['grade_data']['possession'] = 0
                player_info[player['name']]['grade_data']['poss_time'] = 0
                player_info[player['name']]['grade_data']['man_coverage'] = 0
                player_info[player['name']]['grade_data']['lane_coverage'] = 0
                player_info[player['name']]['grade_data']['change_time'] = 0
                player_info[player['name']]['grade_data']['clear'] = 0
                player_info[player['name']]['grade_data']['stack_control'] = 0
                player_info[player['name']]['grade_data']['stuns'] = 0
                player_info[player['name']]['grade_data']['steals'] = 0
                player_info[player['name']]['grade_data']['goalie'] = 0
                player_info[player['name']]['rating_data'] = {}
                player_info[player['name']]['rating_data']['shot'] = 1
                player_info[player['name']]['rating_data']['possession'] = 1
                player_info[player['name']]['stat_data'] = {}
                player_info[player['name']]['stat_data']['shot_taken'] = False
                player_info[player['name']]['stat_data']['shots_taken'] = 0
                player_info[player['name']]['stat_data']['drop_shots_taken'] = 0
                player_info[player['name']]['stat_data']['saves'] = 0
                player_info[player['name']]['stat_data']['drop_saves'] = 0
                player_info[player['name']]['stat_data']['stuns'] = 0
                player_info[player['name']]['stat_data']['drop_stuns'] = 0
                player_info[player['name']]['stat_data']['stunned'] = False
                player_info[player['name']]['info'] = {}
                player_info[player['name']]['info']['stacks'] = {}
                # this will track how many times the player stacks with another player
                # and how long they were stacked -> count and time
                

    return

def clear_player_info():
    global player_info

    player_info.clear()
    return

# creating game_info dictionary
# takes an active dictionary as an argument, clears the data and makes it match our blank_game_info dictionary
###example: create_game_info(game_info)
def create_game_info(info):

    # clearing dictionary
    info.clear()

    # setting default parameters
    info['possNum'] = 0             # random flag to show poss number
    info['thread_alive'] = False    #flag used to tell if second thread is alive
    info['game_live'] = False       #flag used to tell if game is on going
    info['disc'] = {
              'live': False,            #flag used to tell if disc is in play
              'wait': False,            #flag used to delay disc read by one cycle
              'position': [0,0,0],      #disc location
              'velocity': [0,0,0],      #disc velocity
              'pre_velocity': [0,0,0],  #disc velocity
              'throw_speed': 0,         #speed the disc was thrown at
              'bounce': 0,              #number of bounces the disc has
              'pre_bounce': 0,          #number of bounces of previous throw
              'held': False,            # flag to see if disc is in someones hand
              'pre_held': False,        # flag to see if disc was in someones hand
              'by_team': False,         #flag used to see if disc when near team member
              'near_to': -1             #index who triggered by_team
    }
    info['first_poss'] = True       #flag used to tell if disc is in play
    info['pre_poss'] = "None"       #None, Blue, Orange
    info['poss'] = "None"           #Tells which team has possesstion
    info['poss_time'] = 0           #used to calculate time when player got disc
    info['pre_poss_time'] = 0           #used to calculate time when player got disc
    info['release_time'] = 0     #used to calculate time when player releases disc
    info['game_time'] = 0           # current game time
    info['field_state'] = 0         #-1 for disc on blue area
                                    #0 for disc in center
                                    #1 for disc on orange area
    info['pre_field_state'] = 0     # state of previous field
    info['timer'] = 0               # used to record time that field change took place
    info['recover'] = False         # flag used to determine if team is recovering back to defense
    info['recover_stun'] = False    # flag to only run stun recovery once
    info['clear_flag'] = False      # global flag used to see if disc is in clear state
    info['pre_clear_flag'] = False  # global flag used to see if disc is in clear state
    info['danger'] = False          # flag for telling if a disc is under pressure
    info['goalie'] = False             # flag for telling if a goalie has been set yet
    info['shot_taken'] = False         # flag for telling if a shot was taken
    info['shot_made'] = False          # flag for telling if a shot was taken
    info['shot_recovered'] = False      # flag to tell that someone picked up the disc after the shot
    info['pass_intent'] = -1           # flag for telling if a shot was taken
    info['team'] = list()              # list of teams
    info['team'].append({              # blue team data
        'dropped_player': False,        # flag to see if a player dropped
        'clear': 1,                     # Rating to determin if clearing is a good choice
        'clear_flag' : False,           # flag to see if disc status is cleared by blue team
        'present': False,               # are players present
        'pre_present': False,           # were players present
        'goalie': False,                # does team have a goalie
        'passer': -1,                   # player that last released the disc
        'pre_passer': -1,               # player that 2ed last released the disc
        'num_players': 0,               # number of players
        'pre_num_players': 0,           # number of players in previous round
        'team': 'Blue Team',            # name of team
        'team_sign': -1,                # team sign (used in determine direction)
        'joust_poss': False,            # flag to show which team has jousting poss
        })
    info['team'][0]['player'] = list()
    for i in range(5):
        info['team'][0]['player'].append({
                "name": "None",               #name of player, used for delay calculations
                "poss": False,                #flag for showing current possession
                "pre_poss": False,            #flag for showing possession last cycle
                "covered": False,             #flag for showing if man being covered (offense) or covering a man (defense)
                "lane_covered": False,        #flag to track lane-coverage
                "goalie": False,              #flag to see who goalie is
                "pre_goalie": False,              #flag to see who was goalie previous scan
                "distance": [80,80,80,80,80],  #array of distance between player and other players on the opposite team
                "distance2": [80,80,80,80,80],  #array2 of distance between player and other players on the opposite team
                "goal_dist": 80,            #distance to the goal
                "mark":-1,                     # tell who player has marked
                "pre_mark":-1,                # tell who player had mark previous throw
                "location":[0,0,0],           #players location
                "velocity": [0,0,0],             #players velocity vector
                "id": -1,                     #players ID
                "stack":{
                  "stacked": False,             #flag to see if player is stacked
                  "locked": False,             #flag to see if player is locked in a stack
                  "broken": True,              #flag to see if player stack is broken
                  "partner": -1,              #id of player stacked with
                  "time": 0,                  #time since stack was broken
                  "velocity": [0,0,0],         #velocity of stack
                  "pre_velocity": [0,0,0],     #previous velocity of stack
                  "jousting":False,           #bool to see if stack is over 7 m/s
                  "turn":False,                #bool to see if stopped together
                  "near_disc": False,         #bool to see if the stack is close to the disc
                  "stunning": False,          #bool to see if this player is stunning stacks
                  "stack_stunning": False,    #bool to see if this player was stacked durning stunning stacks
                  "start_time": 0,            #time stack was formed
                  "end_time": 0,              #time stack was broken
                },
                "leached": False,             #flag to see if player is leached
                "leach_opp": -1,              #flag to see who player leached
                })
    
    info['team'].append({              # orange team data
        'dropped_player': False,        # flag to see if a player dropped
        'clear': 1,                     #Rating to determin if clearing is a good choice
        'clear_flag' : False,           # flag to see if disc status is cleared by orange team
        'present': False,               # are players present
        'pre_present': False,           # were players present
        'goalie': False,                # does team have a goalie
        'passer': -1,                   # player that last released the disc
        'pre_passer': -1,               # player that 2ed last released the disc
        'num_players': 0,               # number of players
        'pre_num_players': 0,           # number of players in previous round
        'team': 'Orange Team',           # name of team
        'team_sign': 1,                # team sign (used in determine direction)
        'joust_poss': False,            # flag to show which team has jousting poss
        })
    info['team'][1]['player'] = list()
    for i in range(5):
        info['team'][1]['player'].append({
                "name": "None",               #name of player, used for delay calculations
                "poss": False,                #flag for showing current possession
                "pre_poss": False,            #flag for showing possession last cycle
                "covered": False,             #flag for showing if man being covered (offense) or covering a man (defense)
                "lane_covered": False,        #flag to track lane-coverage
                "goalie": False,              #flag to see who goalie is
                "pre_goalie": False,              #flag to see who was goalie previous scan
                "distance":[80,80,80,80,80],  #array of distance between player and other players on the opposite team
                "distance2": [80,80,80,80,80],  #array2 of distance between player and other players on the opposite team
                "goal_dist": 80,            #distance to the goal
                "mark":-1,                     # tell who player has marked
                "pre_mark":-1,                # tell who player had mark previous throw
                "location":[0,0,0],           #players location
                "velocity": [0,0,0],             #players velocity vector
                "id": -1,                     #players ID
                "stack":{
                  "stacked": False,             #flag to see if player is stacked
                  "locked": False,             #flag to see if player is locked in a stack
                  "broken": True,              #flag to see if player stack is broken
                  "partner": -1,        #id of player stacked with
                  "time": 0,            #time since stack was broken
                  "velocity":[0,0,0],         #velocity of stack
                  "pre_velocity":[0,0,0],     #previous velocity of stack
                  "jousting": False,           #bool to see if stack is over 7 m/s
                  "turn": False,                #bool to see if stopped together
                  "near_disc": False,         #bool to see if the stack is close to the disc
                  "stunning": False,          #bool to see if this player is stunning stacks
                  "start_time": 0,            #time stack was formed
                  "end_time": 0,              #time stack was broken
                },
                "leached": False,             #flag to see if player is leached
                "leach_opp": -1,              #flag to see who player leached
                })
    
    info['team'].append({              # spectator data (only for completeness, never used)
        'present': False,               # members present (always False)
        'num_players': 0,               # number of players (always 0)
        'team': 'Spectator',            # team name
        'team_sign': 0,                 # team sign (not used)
        })
    info['name_in_game'] = list()       # list of names of players who are in the game
    info['pre_name_in_game'] = list()   # list of names of players who were in the game
    info['ran_once'] = False            # flag to determine if the program has ran once
    info['game_state'] = ''             # current game state the game is in
    info['orange_points'] = 0           # orange team points
    info['blue_points'] = 0             # blue team points
    info['id_in_game'] = list()        # list of player ID's in the game
    info['last_poss_team'] = -1       # shows which team had poss last
    info['last_poss_player'] = -1       # shows which player had the poss last
    info['shot_pause'] = False     # flag used to wait to get shot position
    info['info_logged'] = False         # So info is only logged once
    
    return
  
# when a player drops, the game_info will need to be updated so the index and game_status match. Will need to move current info to 
# correct index
def refresh_game_info(status, info):
  
  old_info = list()
  old_info.append(copy.deepcopy(info['team'][0]['player']))
  old_info.append(copy.deepcopy(info['team'][1]['player']))
  info['pre_name_in_game'] = info['name_in_game']
  info['name_in_game'] = list()
  info['id_in_game'] = list()
  clear_players = list()
  clear_players.append(info['team'][0]['num_players'] - 1)
  clear_players.append(info['team'][1]['num_players'] - 1)

  for i in range(2):
    if info['team'][i]['present']:
      # going through players in the game
      for index, player in enumerate(status['teams'][i]['players']):
        info['name_in_game'].append(player['name'])
        info['id_in_game'].append(str(player['playerid']))
        #find which index is the information for this player
        old_index = -1
        for x in range(5):
          if player['name'] == old_info[i][x]['name']:
            old_index = x
            break

        # Moving old information to current information
        if old_index != -1:
          info['team'][i]['player'][index] = old_info[i][old_index]
          info['team'][i]['player'][index]['location'] = player['head']['position']
          info['team'][i]['player'][index]['velocity'] = np.round(player['velocity'], 2)
        # if not, player is new to the game
        else:
          info['team'][i]['player'][index]['id'] = player['playerid']
          info['team'][i]['player'][index]['name'] = player['name']
          info['team'][i]['player'][index]['poss'] = False
          info['team'][i]['player'][index]['pre_poss'] = False
          info['team'][i]['player'][index]['covered'] = False
          info['team'][i]['player'][index]['lane_covered'] = False
          info['team'][i]['player'][index]['goalie'] = False
          info['team'][i]['player'][index]['pre_goalie'] = False
          info['team'][i]['player'][index]['distance'] = [80,80,80,80,80]
          info['team'][i]['player'][index]['distance2'] = [80,80,80,80,80]
          info['team'][i]['player'][index]['goal_dist'] = 80
          info['team'][i]['player'][index]['mark'] = -1
          info['team'][i]['player'][index]['pre_mark'] = -1
          info['team'][i]['player'][index]['stack']['stacked'] = False
          info['team'][i]['player'][index]['stack']['locked'] = False
          info['team'][i]['player'][index]['stack']['broken'] = True
          info['team'][i]['player'][index]['stack']['jousting'] = False
          info['team'][i]['player'][index]['stack']['turn'] = False
          info['team'][i]['player'][index]['stack']['near_disc'] = False
          info['team'][i]['player'][index]['stack']['stunning'] = False
          info['team'][i]['player'][index]['stack']['stack_stunning'] = False
          info['team'][i]['player'][index]['stack']['time'] = 0
          info['team'][i]['player'][index]['stack']['pre_velocity'] = [0,0,0]
          info['team'][i]['player'][index]['stack']['partner'] = -1
          info['team'][i]['player'][index]['leached'] = False
          info['team'][i]['player'][index]['leach_opp'] = -1
          #log new player
          write_file(info['game_clock'], player['name'], 'entry', '0', player['name'] + \
                     " entered game at " + str(status['game_clock']) + " seconds")

      clear_team_info(clear_players[i], i, info)
    
  #recording dropped player
  for name in info['pre_name_in_game']:
    if name not in info['name_in_game']:
      write_file(info['game_clock'], name,'Exit','0', name+\
                " left game at "+str(status['game_clock'])+" seconds")
      
      
  return

def update_game_info(status, info):
    # finding the number of players on each team

    correct = True
    for i in range(2):
        if 'players' in status['teams'][i]:
            info['team'][i]['num_players'] = len(status['teams'][i]['players'])
            # checking to see if names match
            for j, player in enumerate(status['teams'][i]['players']):
                if player['name'] != info['team'][i]['player'][j]['name']:
                    correct = False
                else:
                    # setting players info inside game_info
                    info['team'][i]['player'][j]['location'] = player['head']['position']
                    info['team'][i]['player'][j]['velocity'] = np.round(player['velocity'], 2)
                    info['team'][i]['player'][j]['id'] = player['playerid']
                    if str(player['playerid']) not in info['id_in_game']:
                      info['id_in_game'].append(str(player['playerid']))
        elif info['team'][i]['pre_present']:
            info['team'][i]['num_players'] = 0
            clear_team_info(-1, i, info)
        else:
            info['team'][i]['num_players'] = 0

    if not correct:
        refresh_game_info(status, info)


    return

def clear_team_info(num_players, team, info):
    # clearing old info
    for j in range(4, num_players, -1):
        info['team'][team]['player'][j]['id'] = -1
        info['team'][team]['player'][j]['name'] = "None"
        info['team'][team]['player'][j]['poss'] = False
        info['team'][team]['player'][j]['pre_poss'] = False
        info['team'][team]['player'][j]['covered'] = False
        info['team'][team]['player'][j]['lane_covered'] = False
        info['team'][team]['player'][j]['goalie'] = False
        info['team'][team]['player'][j]['pre_goalie'] = False
        info['team'][team]['player'][j]['distance'] = [80, 80, 80, 80, 80]
        info['team'][team]['player'][j]['goal_dist'] = 80
        info['team'][team]['player'][j]['mark'] = -1
        info['team'][team]['player'][j]['pre_mark'] = -1
        info['team'][team]['player'][j]['stack']['stacked'] = False
        info['team'][team]['player'][j]['stack']['partner'] = -1
        info['team'][team]['player'][j]['leached'] = False
        info['team'][team]['player'][j]['leach_opp'] = -1

    return


# creating a new file
def create_new_file():

    # if directoy doesn't exist
    if not path.exists(file_info['file_directory']):
        makedirs(file_info['file_directory'])
        
    # while loop used create a file name that doesn't exist yet
    while path.exists(file_info['file_open']):
        file_info['file_index'] += 1
        file_info['file_open'] = \
            file_info['file_directory'] + str(file_info['today_date']) + str(file_info['file_index']) + '_' + str(file_info['file_name'])
        file_info['file_result_open'] = \
            file_info['file_directory'] + str(file_info['today_date']) + str(file_info['file_index']) + '_' + str(file_info['file_result'])
        file_info['stack_log_open'] = \
            file_info['file_directory'] + str(file_info['today_date']) + str(file_info['file_index']) + '_' + str(file_info['stack_log'])

    # need to create the new file before we can call our writing CSV function
    with open(file_info['file_open'], 'w+') as file:
        file.write("Time,Name,Catagory,Points,Comment\n")
        file_info['first_write'] = True
        
    return

# writing infro into file
def write_file(time, name, catagory,points,comment):
    global log_widget
    
    #locking file to prevent multiple threads from writing
    lock.acquire()

    with open(file_info['file_open'], 'a+') as file:
        file.write(str(time)+','+str(name)+','+str(catagory)+','+str(points)+','+str(comment)+'\n')
        if file_info['first_write']:
            file_info['first_write'] = False

    lock.release()
    
    if log_widget != None:
      log_widget.config(state="normal")
      log_widget.insert("end", str(time)+','+str(name)+','+str(catagory)+','+str(points)+','+str(comment)+'\n')
      log_widget.yview_pickplace("end")
      log_widget.config(state="disabled")
    return

# logging final results of all the players
def log_player_performance(game_info):
  global player_info
  global t1
  
  thread_alive=False
  # makes sure second thread is not running
  if t1.is_alive():
    t1.join(timeout=5)
    if t1.is_alive():
      print("Timeout waiting for thread to join")
      thread_alive=True

  if player_info:
    with open(file_info['file_result_open'], 'a+') as file:
      dummyname = list(player_info.keys())[0]
      key_list = player_info.keys()
      logged_list = list()

      for i in range(2):
        point_total = list()
        total = 0
        for j in range(game_info['team'][i]['num_players']):
          file.write("Name,Catagory,Points,,")
          point_total.append(0)
          logged_list.append(game_info['team'][i]['player'][j]['name'])
        file.write("\n")

        for catagory in player_info[dummyname]['grade_data']:
          for j in range(game_info['team'][i]['num_players']):
            name = game_info['team'][i]['player'][j]['name']
            points = player_info[name]['grade_data'][catagory]
            file.write(str(name) + ',' + str(catagory) + ',' + str(points) + ',,')
            if catagory != "poss_time":
              point_total[j] += points
              total += points

          file.write("\n")

        for j in range(game_info['team'][i]['num_players']):
          name = game_info['team'][i]['player'][j]['name']
          points = point_total[j]
          file.write(str(name) + ',' + "Total" + ',' + str(points) + ',,')

        file.write("\n\n")

        if i == 0:
          file.write("Blue Team" + ',' + "Total" + ',' + str(total) + '\n\n')
        else:
          file.write("Orange Team" + ',' + "Total" + ',' + str(total) + '\n\n')

      still_need = list()
      for name in key_list:
        if name not in logged_list:
          if name != "None":
            still_need.append(name)

      if len(still_need) != 0:
        point_total = list()
        for j in range(len(still_need)):
          point_total.append(0)

        for catagory in player_info[dummyname]['grade_data']:
          for j in range(len(still_need)):
            name = still_need[j]
            points = player_info[name]['grade_data'][catagory]
            file.write(str(name) + ',' + str(catagory) + ',' + str(points) + ',,')
            point_total[j] += points

          file.write("\n")

        for j in range(len(still_need)):
          name = still_need[j]
          points = point_total[j]
          file.write(str(name) + ',' + "Total" + ',' + str(points) + ',,')

    with open(file_info['stack_log_open'], 'a+') as file:
      file.write("Name,Partner,Number of joust, Seconds,\n")
      for player in player_info:
        if player != "None":
          file.write(player+",,,,\n")

          for partner in player_info[player]['info']['stacks']:
            number = player_info[player]['info']['stacks'][partner]['count']
            time = player_info[player]['info']['stacks'][partner]['time']
            file.write("," + partner + "," + str(number) + "," + str(time) + ",\n")


    print("Completed round")
    game_info['info_logged'] = True
#    if thread_alive:
#      t1.kill()

  return

# test function used to calculate how fast script is running
def log_cycle_time(statement):
  
  log = 'time_cycle.csv'
  
  with open(log, 'a+') as file:
    file.write(str(statement)+'\n')
    
  return

# function used to calculate coverage in an additional thread
# mainly is controlled by threading dictionary
def thread_process():
  global threading

  try:
      disc_location = threading['disc_location'].pop(0)
      team_position = threading['team_position'].pop(0)
      team_index = threading['team_index'].pop(0)
      defense_position = threading['defense_position'].pop(0)
      poss_loss = threading['poss_loss'].pop(0)
      info = threading['info'].pop(0)

      team = info['last_poss_team']
      player = info['last_poss_player']

      # team should not be -1:
      if team != -1:
        for i in range(len(team_position)):
          # if they pass the eye sight test, they are open
          if not in_eye_sight([disc_location,team_position[i]], info, not team, defense_position):
            #logging if offense player was in an open lane
            info['team'][team]['player'][team_index[i]]['covered'] = True
            if not info['pre_clear_flag'] and not info['recover']:
              record_pass_lane_error(team, team_index[i], info)

        record_coverage_flags(team, info)
        grade_pass(team, player, False, info)

        if poss_loss:

          record_poss_loss(not team, info)

        if threading['continue']:
          threading['queue'] -= 1
          if threading['queue'] == 0:
            threading['continue'] = False
          thread_process()

      return
  except:
      print("ERROR Thread")
      print(traceback.format_exc())
      return


# finds the magnitude of the velocity from vector velocities.
# takes the velocity as a vector and returns the magnitude of that vector
def find_velocity_mag(velocity):

    velocity = np.linalg.norm(velocity)
    return velocity

# find the unit vector for the direction of a velocity vector
def find_velocity_direction(velocity):

    if (velocity!=0).all():
        velocity = np.array(velocity)/np.linalg.norm(velocity)
    else:
        velocity = 0
    return velocity

# takes two velocity vectors and finds the angle between them
def find_angle_two_vectors(vec1, vec2):
    vec1 = find_velocity_direction(vec1)
    vec2 = find_velocity_direction(vec2)
    return np.arccos(np.dot(vec1,vec2))
  
# finds the magnitude of the distance between two points.
# takes the position 1 as a vector and position 2 as a vector and returns the magnitude of that vector
def find_distance(pos1,pos2):

    pos1 = np.array(pos1)
    pos2 = np.array(pos2)
    distance = np.linalg.norm(pos1-pos2)
    return distance

def closest_point_on_line(a, b, p):
    a = np.array(a)
    ap = p-a
    # get a runtime error if a == b.
    if (a != b).all():
        ab = b-a
    else:
        ab = a
    result = a + np.dot(ap,ab)/np.dot(ab,ab) * ab
    return result

def find_angle(a, b, c):
	#find angle between a to c in reference to line a to b
    point = closest_point_on_line(a,b,c)
    adjacent = find_distance(point, a)
    hypo = find_distance(a, c)
    angle = np.arccos(adjacent/hypo)
    
    #finding if this angle should be over pi/2
    opp_dir = find_velocity_direction(b - a)
    opp_point = a - opp_dir*find_distance(a,b)
    if find_distance(c,b) > find_distance(c,opp_point):
        angle = np.pi - angle
    return angle


def find_angle_to_lane(start, velocity_1, velocity_2):
    start = np.array(start)
    point_2 = start+velocity_1
    point_3 = start+velocity_2
    
    angle = find_angle(start, point_2, point_3)
    
    return angle

# function was added due to api disc bounce count not working
def find_disc_bounce(status, info):

  info['disc']['held'] = False
  for i in range(2):
    for k in range(info['team'][i]['num_players']):
      if info['team'][i]['player'][k]['poss']:
        info['disc']['held'] = True
        info['disc']['wait'] = False

  # disc is not in someone's hands
  if not info['disc']['held']:
    # second cycle after the disc left the players hands
    if not info['disc']['pre_held']:
      # checking to see if this is the second cycle after disc slowed
      # still a glitch when I cetch the disc and it counting as a bounce. Added that velocity and pre should be the same
      if info['disc']['wait'] and (info['disc']['velocity'] == info['disc']['pre_velocity']).all():
        info['disc']['bounce'] += 1
        info['disc']['wait'] = False
      else:
        info['disc']['wait'] = False
      # velocity changed other then by a player
      if (info['disc']['velocity'] != info['disc']['pre_velocity']).all():
        info['disc']['wait'] = True

  # player is holding disc
  else:
    info['disc']['bounce'] = 0

  info['disc']['pre_velocity'] = info['disc']['velocity']
  info['disc']['pre_held'] = info['disc']['held']

  return

def find_disc_position(status, info):
    # getting disc positon
    if status['disc']['position'][2] > 5:
        info['field_state'] = 1
    elif status['disc']['position'][2] < -5:
        info['field_state'] = -1
    else:
        info['field_state'] = 0

    return

# pass in team index, and game info and will return a double array of players position.
def find_players_positions(index, info):
  # make array of defense positions
  position = np.array([[0,0,0]])
  if info['team'][index]['present']:
    for j in range(info['team'][index]['num_players']):
      position = np.append(position, [info['team'][index]['player'][j]['location']], axis=0)
    
  return np.delete(position,0,0)

def find_index_by_id(id, team, info):
    # if id is not on the team anymore, it will be pointed toward index 4
    index = 4

    for i in range(info['team'][team]['num_players']):
      if id == info['team'][team]['player'][i]['id']:
        index = i
        break

    return index
def find_if_marked(pteam, player, previous, info):
  # take in team and player index of person who received the disc
  # previous is a bool to know if we want mark or pre-mark
  disc_id = info['team'][pteam]['player'][player]['id']
  
  mark = "None"
  was_marked = False
  if previous:
    for i in range(5):
      if disc_id == info['team'][not pteam]['player'][i]['pre_mark']:
        mark = info['team'][not pteam]['player'][i]['name']
        was_marked = True
  else:
    for i in range(5):
      if disc_id == info['team'][not pteam]['player'][i]['mark']:
        mark = info['team'][not pteam]['player'][i]['name']
        was_marked = True

  return mark, was_marked

# function to break up nvalid_array array into z positions
# should be called in start of program and only needs to run once
def z_index():
    global nvalid_array
    global index_z
    
    start = -40
    for i in range(len(nvalid_array)):
        if nvalid_array[i][2] == start:
            index_z = np.append(index_z,i)
            start +=1
        elif nvalid_array[i][2] > start:
            start +=1
    return
  
# pass in the two z positions of the players and will return the 
# the starting and ending index value that is needs to be checked
def find_index(pos1,pos2):
    global index_z
    global nvalid_array
    
    first_found = False
    last_found = False
    result = np.array([0,-1]).astype('int')
    
    if pos1 > pos2:
        start = pos2
        end = pos1
    else:
        start = pos1
        end = pos2
      
    i=0
    while i < len(index_z) and not last_found:
        if not first_found:
            if nvalid_array[index_z[i]][2] >= start:
                result[0] = index_z[i]
                first_found = True
        else:
            if nvalid_array[index_z[i]][2] > end:
                result[1] = index_z[i]
                last_found = True
               
        i+=1
    return result

# function to determin if two objects are in range
# takes player location as an array, player velocity as a vector, location as an array and 
# tolerance as a number
def player_near_location(plocation,pvelocity,location,tol=1):
  step = 0.1
  time = 1
  plocation = np.array(plocation).astype('float64')
  pvelocity = np.array(pvelocity)*step
  
  distance = find_distance(plocation,location)
  if distance <= tol:
    return True
  else:
    for i in range(int(time/step)):
      plocation += pvelocity
      new_distance = find_distance(plocation,location)
      if new_distance > distance:
        return False
      else:
        distance = new_distance
        if distance <= tol:
          return True
    return False
  
  
# function used to determin if a player on the offesive team is near the disc
# will set flag inside info dictionary passed.
def player_near_disc(info, tol=1):
  team = info['last_poss_team']
  player = info['last_poss_player']
  disc = info['disc']['position']

  for i in range(info['team'][team]['num_players']):
    plocation = info['team'][team]['player'][i]['location']
    distance = find_distance(plocation, disc)
    if distance < tol:
      info['disc']['by_team'] = True
      info['disc']['near_to'] = i
  
  return
  

# function that will tell if two objects will cross paths.
# takes player1 location and velocity, player2 location and velocity, and 
# an option tolerance (default is 1). Will return a 0 if the objects do
# not cross, a 1 if they cross withen the tolerance and a 2 if they 
# cross withing 2 * tolerance.
def two_paths_cross(plocation,pvelocity,dlocation,dvelocity,tol=1):
  global clear_time
  step = 0.1
  time = clear_time
  
  plocation = np.array(plocation)
  pvelocity = np.array(pvelocity)*step
  dlocation = np.array(dlocation)
  dvelocity = np.array(dvelocity)*step
  
  distance = find_distance(plocation,dlocation)
  for i in range(int(time/step)):
    plocation += pvelocity
    dlocation += dvelocity
    new_distance = find_distance(plocation,dlocation)
    if new_distance > distance:
      if distance <= 1.5*tol:
        return 2
      else:
        return 0
    else:
      distance = new_distance
      if distance <= tol:
        return 1
  return 0
  
  
#funciton that will return all the points between two points in 3D space
#points are to be passed in a double array [[x1,y1,z1],[x2,y2,z2]]
#acc is the number of decimal places desired
def single_line(verts,acc=1):
    verts = np.array(verts)
    x=verts[:,0]
    y=verts[:,1]
    z=verts[:,2]
    vector = np.array([x[1]-x[0],y[1]-y[0],z[1]-z[0]])
    mag = np.sqrt(np.sum(vector**2))
    unitv = (np.array([vector[0]/mag,vector[1]/mag,vector[2]/mag])).round(3)*(10**-acc)
    curx = x[0]
    cury = y[0]
    curz = z[0]
    xline = np.array([])
    yline = np.array([])
    zline = np.array([])
    xdir = -1 if vector[0] < 0 else 1
    ydir = -1 if vector[1] < 0 else 1
    zdir = -1 if vector[2] < 0 else 1

    while xdir*curx <= xdir*x[1] and ydir*cury <= ydir*y[1] and zdir*curz <= zdir*z[1]:
        xline = np.append(xline,curx)
        yline = np.append(yline,cury)
        zline = np.append(zline,curz)
        curx += unitv[0]
        cury += unitv[1]
        curz += unitv[2]

    xline = xline.round(acc)
    yline = yline.round(acc)
    zline = zline.round(acc)
    
    verts = np.transpose([xline,yline,zline])
    
    return np.unique(verts, axis=0)
    
    

# function to check if verts are all valid vertieces i.e. a straigth path is a valid path
# verts of the path are the first argument, a double array of defense possition is the second,
# reach of a single arm in meters is the third, and the file can be set by name file.
def in_value_set(verts, info, defense, def_bodies=np.array([[]]), meters = 3, *args):
    global nvalid_array
    
    verts = verts.tolist()
    start,end = find_index(verts[0][2],verts[-1][2])
    check_set = nvalid_array[start:end]
    valuePresent = False
    j = 0
    
    if def_bodies.size == 0:
        
        # takes 2.88 seconds to complete 40 m check
        # checking to see if any objects are in th way
        while j < len(verts) and not valuePresent:
          if verts[j] in check_set:
              valuePresent = True
          j+=1
        
    else:
      #number of players provided
      num = len(def_bodies)
      disc_speed = info['disc']['throw_speed']
      # should not penalize lane coverage is player threw disc too soft
      if disc_speed < exp_disc_speed:
          disc_speed = exp_disc_speed
      #finding boundaries of players reach

      def_result = create_defense_line_coverage(verts[0], disc_speed, verts[-1], def_bodies)
      
      # checking to see if this lane is covered
      if def_result.any():
        valuePresent = True
        info['team'][defense]['player'][np.where(def_result)[0][0]]['lane_covered'] = True
        
      # checking to see if any objects are in the way
      while j < len(verts) and not valuePresent:
          if verts[j] in check_set:
              valuePresent = True
          j+=1
        
    return valuePresent

# function that returns a bool that is the inverse of bool received from in_value_set
def in_eye_sight(verts, info, defense, def_bodies=np.array([[]]), meters = 3, acc=1):
  return not in_value_set(single_line(verts,acc), info, defense, def_bodies, meters)

def person_to_line(point1, point2, point3, velocity, indiv_wing = 1, indiv_speed=5):
    # From point1 to point2 creates the line
    # Find distance from point 3 to the line
    
    point1 = np.array(point1)
    point2 = np.array(point2)
    point3 = np.array(point3)

    on_line = closest_point_on_line(point1, point2, point3)
    
    distance = find_distance(point3, on_line)
    time = find_distance(point1, on_line)/velocity
    reach = indiv_speed * time + indiv_wing
    
    return distance, on_line, reach

def create_defense_line_coverage(disc, disc_velocity, receiver, def_bodies, wing_span = 1, speed = 5):
      
    coverage_array = np.array([False])
    point_on_line = np.array([[0,0,0]])
    for i in range(len(def_bodies)):
        pass_distance = find_distance(disc, def_bodies[i])
        distance, intersect, reach = person_to_line(disc, receiver, def_bodies[i], disc_velocity, wing_span, speed)

        point_on_line = np.append(point_on_line, [intersect], axis=0)
        
        # pass line is not in reach or point on the line does not intersect the pass
        if distance > reach or pass_distance < find_distance(intersect,disc) or pass_distance < find_distance(intersect,def_bodies[i]):
          coverage_array = np.append(coverage_array, [False], axis=0)
        else:
          coverage_array = np.append(coverage_array, [True], axis=0)
        
    coverage_array = np.delete(coverage_array, 0, axis=0)
    point_on_line = np.delete(point_on_line, 0, axis=0)
    
    # checking to see if there are multiple ture's
    # award the person closer to the receiver
    trues = np.where(coverage_array)[0]
    if len(trues) > 1:
      whos_closer = np.array([0])
      for j in range(len(trues)):
        whos_closer = np.append(whos_closer, [find_distance(point_on_line[trues[j]], receiver)], axis=0)
      
      whos_closer = np.delete(whos_closer, 0, axis=0)
      trues = np.delete(trues, np.argmin(whos_closer), axis=0)
      
      for j in range(len(trues)):
        coverage_array[trues[j]] = False
      
    return coverage_array

# function to monitor stacks in game
# function will also write states to file
def find_stacks(status, info):
  global stack_grab
  global light_coverage
  
  for i in range(2):
      stacks_pair = list()
      for k in range(info['team'][i]['num_players']):
        team = -1
        # checking to see if player is holding a player in the game
        if status['teams'][i]['players'][k]['holding_left'] in info['id_in_game']:
          for j in range(2):
            for l in range(info['team'][j]['num_players']):
              if status['teams'][i]['players'][k]['holding_left'] == str(status['teams'][j]['players'][l]['playerid']):
                team = j
                player = l
                p_id = status['teams'][j]['players'][l]['playerid']
        elif status['teams'][i]['players'][k]['holding_right'] in info['id_in_game']:
          for j in range(2):
            for l in range(info['team'][j]['num_players']):
              if status['teams'][i]['players'][k]['holding_right'] == str(status['teams'][j]['players'][l]['playerid']):
                team = j
                player = l
                p_id = status['teams'][j]['players'][l]['playerid']
        
        # player is not holding a player and is not in a stack
        elif info['team'][i]['player'][k]['id'] not in stacks_pair:
          if info['team'][i]['player'][k]['stack']['locked']:
            
            if info['team'][i]['player'][k]['stack']['time'] - info['game_time'] > stack_grab:

              # checking to see if the disc was obtained
              if info['team'][i]['player'][k]['stack']['near_disc']:
                partner = find_index_by_id(info['team'][i]['player'][k]['stack']['partner'], i, info)
                info['team'][i]['player'][k]['stack']['near_disc'] = False
                info['team'][i]['player'][partner]['stack']['near_disc'] = False
                # checking to see if either player has the disc
                if info['team'][i]['player'][partner]['poss'] or info['team'][i]['player'][k]['poss']:
                  record_stack_disc(i, k, partner, info, 2)
                # checking to see if they slapped the disc
                elif info['last_poss_team'] == i and (info['last_poss_player'] == k or info['last_poss_player'] == partner):
                  record_stack_disc(i, k, partner, info, 2)

                elif find_distance(info['team'][i]['player'][k]['location'], info['disc']['position']) < light_coverage or \
                        find_distance(info['team'][i]['player'][partner]['location'], info['disc']['position']) < light_coverage:
                  record_stack_disc(i, k, partner, info, 1)

                # stack missed the disc
                else:
                  record_stack_disc(i, k, partner, info, 0)

              # stack is no longer together
              
              # saving stack infomation
              if info['team'][i]['player'][k]['stack']['locked']:
                info['team'][i]['player'][k]['stack']['end_time'] = info['game_time']
                stack_name = info['team'][i]['player'][k]['name']
                stack_partner = find_index_by_id(info['team'][i]['player'][k]['stack']['partner'], i, info)
                stack_p_name = info['team'][i]['player'][stack_partner]['name']
                stack_time = info['team'][i]['player'][k]['stack']['start_time'] - info['game_time']
                record_stacks_info(stack_name, stack_p_name, stack_time)
                print(stack_name + " and " + stack_p_name + " stack was broken at " + info['game_clock'])
                
                
              info['team'][i]['player'][k]['stack']['broken'] = True
              info['team'][i]['player'][k]['stack']['jousting'] = False
              info['team'][i]['player'][k]['stack']['locked'] = False
              info['team'][i]['player'][k]['stack']['stacked'] = False
              info['team'][i]['player'][k]['stack']['partner'] = -1
              info['team'][i]['player'][k]['stack']['pre_velocity'] = np.array([0,0,0])

            # if player is locked in a stack, checking to see if they are near the disc
            else:
              partner = find_index_by_id(info['team'][i]['player'][k]['stack']['partner'], i, info)
              stack_location = info['team'][i]['player'][k]['location']
              # checking to see if jousting stack is close to the disc
              if find_distance(stack_location, info['disc']['position']) < light_coverage:
                info['team'][i]['player'][k]['stack']['near_disc'] = True
                info['team'][i]['player'][partner]['stack']['near_disc'] = True

          # player has their own teammate, but has not jousted with them
          elif info['team'][i]['player'][k]['stack']['stacked']:
            
            if info['team'][i]['player'][k]['stack']['time'] - info['game_time'] > stack_grab:
                info['team'][i]['player'][k]['stack']['jousting'] = False
                info['team'][i]['player'][k]['stack']['locked'] = False
                info['team'][i]['player'][k]['stack']['stacked'] = False
                info['team'][i]['player'][k]['stack']['partner'] = -1

        # checking to see if that person is on the same team
        if team != -1:
          if team == i:
            if not info['team'][i]['joust_poss']:
                stacks_pair.append(p_id)
                # checking to see if two players match in partners
                if info['team'][team]['player'][k]['id'] == info['team'][team]['player'][player]['stack']['partner'] and not info['team'][team]['player'][k]['stack']['locked']:
                  info['team'][team]['player'][player]['stack']['locked'] = True
                  info['team'][team]['player'][k]['stack']['locked'] = True
                  info['team'][team]['player'][k]['stack']['partner'] = p_id
                  info['team'][team]['player'][player]['stack']['start_time'] = info['game_time']
                  info['team'][team]['player'][k]['stack']['start_time'] = info['game_time']
                  print(info['team'][team]['player'][k]['name'] + " and " + info['team'][team]['player'][player]['name'] + " formed a stack at " + info['game_clock'])
                # if the other person doesn't have a partner yet, set other person as his partner
                elif info['team'][team]['player'][player]['stack']['partner'] == -1:
                  info['team'][team]['player'][k]['stack']['partner'] = p_id
                  info['team'][team]['player'][k]['stack']['locked'] = False
                  info['team'][team]['player'][k]['stack']['stacked'] = True
                  info['team'][i]['player'][k]['stack']['time'] = info['game_time']

                # checking to see if the person player is holding on to is locked in a stack or
                # if player is locked instacked with this player
                if not info['team'][team]['player'][player]['stack']['locked'] or info['team'][team]['player'][k]['stack']['locked']:
                  info['team'][team]['player'][k]['stack']['stacked'] = True
                  info['team'][team]['player'][k]['stack']['broken'] = False
                  info['team'][team]['player'][k]['stack']['time'] = info['game_time']
                  info['team'][team]['player'][player]['stack']['stacked'] = True
                  info['team'][team]['player'][player]['stack']['broken'] = False
                  info['team'][team]['player'][player]['stack']['time'] = info['game_time']
                  info['team'][team]['player'][k]['leached'] = False
                  info['team'][team]['player'][k]['leach_opp'] = -1
                # if this player is locked and holding player is not, player is leached on a
                # friendly stacked
                else:
                  info['team'][team]['player'][k]['stack']['stacked'] = False
                  info['team'][team]['player'][k]['stack']['broken'] = True
                  info['team'][team]['player'][k]['leached'] = False
                  info['team'][team]['player'][k]['leach_opp'] = -1

                if info['team'][team]['player'][k]['stack']['locked']:
                  velocity = info['team'][team]['player'][player]['velocity']

                  stack_location = info['team'][team]['player'][player]['location']
                  info['team'][team]['player'][k]['stack']['velocity'] = velocity
                  info['team'][team]['player'][player]['stack']['velocity'] = velocity
                  if find_velocity_mag(velocity) > 13:
                    #chcking to see if stack turned greater then 45 degrees while keeping speed over 13
                    if (info['team'][team]['player'][k]['stack']['pre_velocity'] != np.array([0,0,0])).all():
                      if find_angle_to_lane(stack_location, info['team'][team]['player'][k]['stack']['pre_velocity'], velocity) > 0.7854:
                        record_stack_turn(team, k, player, info, True)
                        print("stack turn via angle")
                        print(180*find_angle_to_lane(stack_location, info['team'][team]['player'][k]['stack']['pre_velocity'], velocity)/np.pi)

                    info['team'][team]['player'][k]['stack']['jousting'] = True
                    info['team'][team]['player'][player]['stack']['jousting'] = True

                    # checking to see if jousting stack is close to the disc
                    if find_distance(stack_location, info['disc']['position']) < light_coverage:
                        info['team'][team]['player'][k]['stack']['near_disc'] = True
                        info['team'][team]['player'][player]['stack']['near_disc'] = True

                  elif info['team'][team]['player'][k]['stack']['jousting'] and find_velocity_mag(velocity) < 6:
                    info['team'][team]['player'][k]['stack']['jousting'] = False
                    info['team'][team]['player'][player]['stack']['jousting'] = False
                    record_stack_turn(team, k, player, info)
                    #checking to see if stack missed the disc
                    if info['team'][team]['player'][player]['stack']['near_disc']:
                      info['team'][team]['player'][k]['stack']['near_disc'] = False
                      info['team'][team]['player'][player]['stack']['near_disc'] = False
                      # stack missed the disc
                      if find_distance(stack_location, info['disc']['position']) < light_coverage:
                        record_stack_disc(team, k, player, info, 1)
                      else:
                        # stack gained poss of the disc
                        if info['team'][team]['player'][player]['poss'] or info['team'][team]['player'][k]['poss']:
                          record_stack_disc(team, k, player, info, 2)
                        else:
                          record_stack_disc(team, k , player, info, 0)


                  info['team'][team]['player'][k]['stack']['pre_velocity'] = velocity
                  info['team'][team]['player'][player]['stack']['pre_velocity'] = velocity

          else:
            if not info['team'][i]['player'][k]['leached']:
              info['team'][i]['player'][k]['leached'] = True
              info['team'][i]['player'][k]['leach_opp'] = p_id

          
  return

# will record who has stacked with who.
def record_stacks_info(name, pname, time):
  global player_info
  
  # checking to see if this person has stacked with anyone yet
  if len(player_info[name]['info']['stacks']) == 0:
    player_info[name]['info']['stacks'][pname] = {}
    player_info[name]['info']['stacks'][pname]['count'] = 1
    player_info[name]['info']['stacks'][pname]['time'] = time
  # checking to see if this player has stacked with this partner yet
  elif pname in player_info[name]['info']['stacks']:
    player_info[name]['info']['stacks'][pname]['count'] += 1
    player_info[name]['info']['stacks'][pname]['time'] += time
  # first time stacking with this player
  else:
    player_info[name]['info']['stacks'][pname] = {}
    player_info[name]['info']['stacks'][pname]['count'] = 1
    player_info[name]['info']['stacks'][pname]['time'] = time
    
  
  return
  
# function that takes api and game info as arguments
# will find the person who has the disc and return team index and player index
# if no body holds the disc, team and player will be -1
def find_who_poss(status,info):
    global threading

    team = -1
    player = -1
    for k in range(2):
      if info['team'][k]['present']:
        for i in range(info['team'][k]['num_players']):
            # checking to see who has possession flag
            if status['teams'][k]['players'][i]['possession']:
              name = info['team'][k]['player'][i]['name']
              # check to see if they are holding the disc
              if status['teams'][k]['players'][i]['holding_left'] == "disc" or \
                status['teams'][k]['players'][i]['holding_right'] == "disc":
                  info['disc']['by_team'] = False
                  info['team'][k]['player'][i]['poss'] = True
                  info['pass_intent'] = -1
                  one_poss(k,i,info)
                  # check to see if this is the first cycle grabbing the disc
                  if not info['team'][k]['player'][i]['pre_poss'] or info['poss_time'] > info['release_time']:
                    info['pre_poss_time'] = info['poss_time']
                    info['poss_time'] = info['game_time']
                  # if shot was taken, it has been recovered
                  if info['shot_taken'] and not player_info[name]['stat_data']['shot_taken']:
                    info['shot_recovered'] = True
                  team = k
                  player = i
              # checking to see if disc is moving faster then 4.7m/s or father then 1 meter away
              elif find_distance(status['disc']['position'], status['teams'][k]['players'][i]['head']['position']) < 1.5 and \
                find_velocity_mag(status['disc']['velocity']) < 4.7:
                  # person head butt to gain poss and kept the disc close by
                  if not info['team'][k]['player'][i]['pre_poss'] or info['poss_time'] > info['release_time']:
                      info['pre_poss_time'] = info['poss_time']
                      info['poss_time'] = info['game_time']

                  info['team'][k]['player'][i]['poss'] = True
                  one_poss(k, i, info)
                  team = k
                  player = i

              # player just head butted it. giving him poss for one cycle
              elif not info['team'][k]['player'][i]['pre_poss'] and info['last_poss_player'] != i and info['last_poss_team'] != k:
                  info['team'][k]['player'][i]['poss'] = True
                  info['pre_poss_time'] = info['poss_time']
                  info['poss_time'] = info['game_time']
                  info['release_time'] = info['game_time'] - 0.1
                  info['team'][k]['pre_passer'] = info['team'][k]['passer']
                  info['team'][k]['passer'] = info['team'][k]['player'][i]['id']
                  info['disc']['by_team'] = False
                  info['disc']['near_to'] = -1
                  team = k
                  player = i
              # person shows to have possession but disc is not with them
              else:
                # check to see if player just threw disc
                if info['release_time'] > info['poss_time']:
                  info['release_time'] = info['game_time']
                  info['team'][k]['pre_passer'] = info['team'][k]['passer']
                  info['team'][k]['passer'] = info['team'][k]['player'][i]['id']
                  info['disc']['by_team'] = False
                  info['disc']['near_to'] = -1
                  set_coverage_flags(k, i, info)
                  # function depends on threaded information
                  if not threading['thread_cycle']:
                    record_coverage_flags(k, info)
                    grade_pass(k, i, False, info)
                # player does not have poss
                info['team'][k]['player'][i]['poss'] = False

    return team,player

def calculate_poss_time(team, player, info):

    if team != -1:
        if info['team'][team]['player'][player]['pre_poss'] and not info['team'][team]['player'][player]['poss']:
            name = info['team'][team]['player'][player]['name']
            #checking to see if disc was stolen from the players hand
            if info['release_time'] > info['poss_time']:
                time = round(info['pre_poss_time'] - info['poss_time'], 3)
            # player threw disc
            else:
                time = round(info['poss_time'] - info['release_time'], 3)

            write_file(info['game_clock'], name, 'poss_time', '+' + str(time), name + " gained " + str(time) + " seconds of poss time")
            player_info[name]['grade_data']['poss_time'] += time

    return

#function will set open flags for the players, covered flag should already been set for all offense players
def find_pass_options(team, player, info):
  global open_distance
  global threading
  
  team_position = np.array([[0,0,0]])
  team_index = np.array([]).astype(int)
  
  # loop through to see who is not covered
  for i in range(info['team'][team]['num_players']):
    if i != player:
      if not info['team'][team]['player'][i]['covered']:
          team_position = np.append(team_position, [info['team'][team]['player'][i]['location']], axis=0)
          team_index = np.append(team_index, i)
  
  team_position = np.delete(team_position, 0, 0)

  # if nobody is not covered, there are no pass options.
  if team_position.size == 0:
    return
  # if players are not covered, we need to get their position
  else:
    disc_location = info['disc']['position']
    #removing players too close or too far
    i = 0
    while i < len(team_position):
      distance = find_distance(disc_location, team_position[i])
      # player cannot be too close or too far
      if distance < open_distance[0] or distance > open_distance[1]:
        team_position = np.delete(team_position, i, axis = 0)
        team_index = np.delete(team_index, i, axis = 0)
        i-=1
      i+=1
    
    # if team_position is empty now, there are no open passes
    if team_position.size == 0:
      for i in range(info['team'][team]['num_players']):
        info['team'][team]['player'][i]['covered'] = True
    
    #checking to see if anything is in the passing lane
    else:
      if not info['first_poss']:
        defense_position = find_players_positions(not team, info)

        #use two diferent logic if multithreading
        if threading['threading']:
          threading['disc_location'].append(disc_location)
          threading['team_position'].append(team_position)
          threading['team_index'].append(team_index)
          threading['defense_position'].append(defense_position)
          threading['info'].append((copy.deepcopy(info)))
          threading['poss_loss'].append(False)
          threading['thread_cycle'] = True
        else:
          for i in range(len(team_position)):
            # if they pass the eye sight test, they are open
            if not in_eye_sight([disc_location,team_position[i]], info, not team, defense_position):
              #logging if offense player was in an open lane
              info['team'][team]['player'][team_index[i]]['lane_covered'] = True
#              print(info['team'][team]['player'][team_index[i]]['name'] + " was not open for a pass.")
              if not info['pre_clear_flag'] and not info['recover']:
                record_pass_lane_error(team, team_index[i], info)
    
  return

#funciton that will set the defense goalie flag and record distance to goal
def find_goalie(defense, info):
  global goal_coverage
  global goal_center

  team_goal = goal_center * info['team'][defense]['team_sign']
  #setting flags to default
  for i in range(5):
    info['team'][defense]['player'][i]['goal_dist'] = 80
  
  if info['team'][defense]['present']:
    goal_change = False
    positions = find_players_positions(defense, info)
    distance = np.array([])
    for i in range(info['team'][defense]['num_players']):
      result = find_distance(positions[i],team_goal)
      distance = np.append(distance, result)
      info['team'][defense]['player'][i]['goal_dist'] = result
      if info['team'][defense]['player'][i]['goalie']:
        if result > goal_coverage:
          goal_change = True

    if info['team'][defense]['goalie']:
      if goal_change:
        min_index = np.argmin(distance)
        if distance[min_index] < goal_coverage:
          info['team'][defense]['player'][min_index]['goalie'] = True
          info['team'][defense]['goalie'] = True

          for i in range(info['team'][defense]['num_players']):
            if i != min_index:
              info['team'][defense]['player'][i]['goalie'] = False
        else:
          clear_goalie(defense,info)
    elif distance.size != 0:
      min_index = np.argmin(distance)
      if distance[min_index] < goal_coverage:
        info['team'][defense]['player'][min_index]['goalie'] = True
        info['team'][defense]['goalie'] = True
        for i in range(info['team'][defense]['num_players']):
          if i != min_index:
            info['team'][defense]['player'][i]['goalie'] = False
            
  return

# funciton that will set the teams passed position to the oppoent
# info is recorded inside info['team'][team]['player'][x]['distance']
def find_dist_to_opp(team, info, defense2 = False):
  
  # get defense positions
  def_position = find_players_positions(team, info)
  of_position = find_players_positions(not team, info)

  if not defense2:
    # getting distance to players
    for j in range(len(def_position)):
      for k in range(len(of_position)):
        info['team'][team]['player'][j]['distance'][k] = find_distance(def_position[j],of_position[k])
  else:
    # getting distance to players
    for j in range(len(def_position)):
      for k in range(len(of_position)):
        info['team'][team]['player'][j]['distance2'][k] = find_distance(def_position[j],of_position[k])

  
  return


def man_coverage(defense, info):
  global light_coverage
  global tight_coverage
  global goal_center
  global goal_coverage
  
  if info['team'][defense]['present']:
    #getting distance to other team
    find_dist_to_opp(defense, info)

    # finding who everyone is closest too
    coverage = np.array([]).astype(int)
    for j in range(info['team'][defense]['num_players']):
      # getting who is closest player
      near_player = np.argmin(info['team'][defense]['player'][j]['distance'])
      distance = info['team'][defense]['player'][j]['distance'][near_player]
      # if disance is greater then light_coverage, mark as -1
      if distance < light_coverage:
        coverage = np.append(coverage, near_player)
      else:
        coverage = np.append(coverage, -1)

    while(not single_coverage(coverage, defense, info).any()):
      # finding who everyone is closest too
      coverage = np.array([]).astype(int)
      for j in range(info['team'][defense]['num_players']):
        # getting who is closest player
        near_player = np.argmin(info['team'][defense]['player'][j]['distance'])
        distance = info['team'][defense]['player'][j]['distance'][near_player]
        # if disance is greater then light_coverage, mark as -1
        if distance < light_coverage:
          coverage = np.append(coverage, near_player)
        else:
          coverage = np.append(coverage, -1)

    # after loop, coverage is an array that shows which player is guarding who
    # [-1,2,1,-1] -> -1 is guarding nobody, guarding player 2, guarding player 1
    # setting defense flags
    for k in range(len(coverage)):
      info['team'][defense]['player'][k]['pre_mark'] = info['team'][defense]['player'][k]['mark']
      if coverage[k] > -1:
        info['team'][defense]['player'][k]['covered'] = True
        # setting mark
        info['team'][defense]['player'][k]['mark'] = info['team'][not defense]['player'][coverage[k]]['id']
      else:
        info['team'][defense]['player'][k]['covered'] = False
        info['team'][defense]['player'][k]['mark'] = -1


    # setting up offense flags
    # getting total number of players and setting covered to True
    offense = np.array([]).astype(int)
    for j in range(info['team'][not defense]['num_players']):
      offense = np.append(offense,j)
      info['team'][not defense]['player'][j]['covered'] = True
      info['team'][not defense]['player'][j]['lane_covered'] = False
    for j in range(info['team'][defense]['num_players']):
      info['team'][defense]['player'][j]['lane_covered'] = False

    offense = open_passes(coverage, offense)
    # change all open men back to False
    for k in range(len(offense)):
        info['team'][not defense]['player'][offense[k]]['covered'] = False
    
  return

def single_coverage(coverage, defense, info):
  # removing negative numbers that are used for holding places
  test_coverage = np.delete(coverage,np.argwhere(coverage<0).flatten())
  if len(test_coverage) != len(np.unique(test_coverage)):
    # finding values that match
    values, uni_count = np.unique(coverage,return_counts=True)
    
    matches = np.argwhere(uni_count>1).flatten()  #index value of values that are dubplicated
    
    #finding exact indices that are dublicated
    for j in range(len(matches)):
      
      if values[matches[j]] != -1:
        row_match = np.array([]).astype(int)
        distance = np.array([])

        for k in range(len(coverage)):
          if coverage[k] == values[matches[j]]:
            row_match = np.append(row_match,k)

        #checking to see which player is closest
        for k in range(len(row_match)):
          distance = np.append(distance, info['team'][defense]['player'][row_match[k]]['distance'][coverage[row_match[k]]])

        # now remove the closest person from row_match
        row_match = np.delete(row_match, np.argmin(distance))

        # set other values to 80
        for k in range(len(row_match)):
          info['team'][defense]['player'][row_match[k]]['distance'][coverage[row_match[k]]]=80
        
    return np.array([False])
  
  return coverage
  

# function that takes the team index, player index, a bool if the calculation is after a bounce
# and game info
def grade_pass(team, player, bounce, info):
  global player_info
  global open_distance

  if team != -1:
      name = info['team'][team]['player'][player]['name']

      start = info['disc']['position']
      dvelocity = info['disc']['velocity']
      grade = 0
      i = 0

      while i < info['team'][team]['num_players'] and not grade:
        if i != player:
          plocation = info['team'][team]['player'][i]['location']
          pvelocity = info['team'][team]['player'][i]['velocity']

          if find_distance(start, plocation) > open_distance[0]:
            grade = two_paths_cross(start, dvelocity, plocation, pvelocity)
            if grade:
              if not info['team'][team]['player'][player]['covered']:
                playerR = i
                info['pass_intent'] = i
                nameR = info['team'][team]['player'][playerR]['name']
              else:
                grade = -1
        i+=1

      if bounce:
        if grade == 1:
          write_file(info['game_clock'], name,'possession','+1', name + " dimed a bounce pass to " + nameR + "." )
          player_info[name]['grade_data']['possession'] += 1
          if player_info[name]['rating_data']['possession'] < 1:
            player_info[name]['rating_data']['possession'] += 0.1
        elif grade == 2:
          write_file(info['game_clock'], name,'possession','+0.5', name + " made a good bounce pass to " + nameR + "." )
          player_info[name]['grade_data']['possession'] += 0.5
          if player_info[name]['rating_data']['possession'] < 1:
            player_info[name]['rating_data']['possession'] += 0.1
      else:
        if grade == 1:
          write_file(info['game_clock'], name,'possession','+1', name + " dimed a pass to " + nameR + "." )
          player_info[name]['grade_data']['possession'] += 1
          if player_info[name]['rating_data']['possession'] < 1:
            player_info[name]['rating_data']['possession'] += 0.1
        elif grade == 2:
          write_file(info['game_clock'], name,'possession','+0.5', name + " made a good pass to " + nameR + "." )
          player_info[name]['grade_data']['possession'] += 0.5
          if player_info[name]['rating_data']['possession'] < 1:
            player_info[name]['rating_data']['possession'] += 0.1
  
  return


def open_passes(defense, o_team):
  
  drop_array = np.array([]).astype(int)
  
  #looping through to find duplicates
  for j in range(len(defense)):
    if defense[j] != -1:
      for k in range(len(o_team)):
        if defense[j] == o_team[k]:
          drop_array = np.append(drop_array, k)

  if drop_array.size != 0:
    o_team = np.delete(o_team,drop_array,0)
    
  return o_team
    

def is_pass_options(oteam, info):
  # need covered flags set and open
  global possession_rating
  global player_info
  
  pass_option = False
  for j in range(info['team'][oteam]['num_players']):
    if not info['team'][oteam]['player'][j]['poss']:
      if not info['team'][oteam]['player'][j]['covered'] and not info['team'][oteam]['player'][j]['lane_covered']:
        name = info['team'][oteam]['player'][j]['name']
        if player_info[name]['rating_data']['possession'] >= possession_rating:
          pass_option = True
    
  return pass_option

def disc_in_pocket(location):
  global pocket_size
  x = location[0]
  y = location[1]
  z = location[2]
  
  if (abs(x) < pocket_size and abs(y) > 1.5 - pocket_size) or (abs(y) < pocket_size and abs(x) > 1.5 - pocket_size):
    return True
    
  return False

#function to evaluate return to defense/offense
def evaluate_recovery(info):
  global return_time
  
  if info['field_state'] == -1:
    team = 0
  else:
    team = 1
    
  if info['timer'] - info['game_time'] >= return_time:
    info['recover'] = False
    info['recover_stun'] = False
    record_recovery(team, info)
  elif info['timer'] - info['game_time'] >= return_time/2:
    if not info['recover_stun']:
        record_recovery_stun(team, info)
        info['recover_stun'] = True

  return

def set_shots(status, info):
  global player_info
  
  for i in range(2):
    if info['team'][i]['present']:
      for player in status['teams'][i]['players']:
        # checking to see if shots in game are less than shots in records
        if player_info[player['name']]['stat_data']['shots_taken'] > player['stats']['shots_taken']:
          # moving recorded shots to drop so info is not lost and setting info equal to API
          player_info[player['name']]['stat_data']['drop_shots_taken'] += player_info[player['name']]['stat_data']['shots_taken']
          player_info[player['name']]['stat_data']['shots_taken'] = player['stats']['shots_taken']
        
        # checking to see if shots has increased
        if player_info[player['name']]['stat_data']['shots_taken'] < player['stats']['shots_taken']:
          player_info[player['name']]['stat_data']['shots_taken'] = player['stats']['shots_taken']
          if not info['shot_made']:
            player_info[player['name']]['stat_data']['shot_taken'] = True
            info['shot_taken'] = True

  info['shot_made'] = False



  return

def clear_shot_status(playerinfo, info):

    for name in playerinfo:
        playerinfo[name]['stat_data']['shot_taken'] = False

    info['shot_taken'] = False
    info['shot_recovered'] = False

    return

def clear_recover(info):

    info['recover'] = False
    info['recover_stun'] = False

    for k in range(2):
        for i in range(info['team'][k]['num_players']):
            info['team'][k]['player'][i]['stack']['stunning'] = False
            info['team'][k]['player'][i]['stack']['stack_stunning'] = False

    return

def reset_flags(team, info):
  clear_poss(team, info)
  clear_defense(team, info)
  clear_distance(team, info)
  
  return

def one_poss(team, player, info):

    for i in range(info['team'][team]['num_players']):
        if i != player:
          info['team'][team]['player'][i]['poss'] = False

def clear_poss(team, info):
  
  info['team'][team]['passer'] = -1
  #pre_passer is not reset incase the goal is a chicago we can find assister
  
  for i in range(info['team'][team]['num_players']):
      info['team'][team]['player'][i]['poss'] = False
  
  return

def clear_defense(team, info):
  
  for i in range(info['team'][team]['num_players']):
      info['team'][team]['player'][i]['covered'] = False

  return

def clear_distance(team, info):
  
  for i in range(info['team'][team]['num_players']):
      info['team'][team]['player'][i]['distance'] = [80,80,80,80,80,80]

  return

# need all the possesion flags set correctly and danger flag set
def clear_goalie(team, info):
  
  info['team'][team]['goalie'] = False
  for i in range(info['team'][team]['num_players']):
    info['team'][team]['player'][i]['goalie'] = False
  
  return
    
def record_poss_loss(loss_team, info):
  # defense team needs pre_poss flag set
  global poss_min
  global player_info

  player = info['last_poss_player']
  name = info['team'][loss_team]['player'][player]['name']
  throw_speed = info['disc']['throw_speed']
  taken_from_hand = False

  # find how long player had poss
  # if release time is greater, disc was stolen from players hand
  if info['release_time'] > info['pre_poss_time']:
      time = info['pre_poss_time'] - info['poss_time']
      taken_from_hand = True

  # player threw the disc
  else:
      time = info['pre_poss_time'] - info['release_time']

  if player_info[name]['stat_data']['shot_taken']:
    if (is_pass_options(loss_team, info)):
      write_file(info['game_clock'], name, 'possession', '-1',
                name + " shot the disc and loss possession; and had pass options available")
      player_info[name]['grade_data']['possession'] -= 1
      if player_info[name]['rating_data']['possession'] > 0:
        player_info[name]['rating_data']['possession'] -= 0.1
    else:
      write_file(info['game_clock'], name, 'possession', '-0.5',
                name + " shot the disc and loss possession; Had no pass options")
  else:
    if time < poss_min:
      if info['danger']:
        write_file(info['game_clock'], name,'possession','0', name + " loss possession but was under high pressure and had the disc for " + str(time) + "; less then " + str(poss_min) + " seconds.")
      else:
        write_file(info['game_clock'], name,'possession','-1', name + " loss possession; threw disc in less then " + str(poss_min) + " but was not under pressure")
        player_info[name]['grade_data']['possession'] -= 1
        if player_info[name]['rating_data']['possession'] > 0:
          player_info[name]['rating_data']['possession'] -= 0.1
    else:
      if(is_pass_options(loss_team, info)):
        write_file(info['game_clock'], name,'possession','-1', name + " loss possession; and had pass options available")
        player_info[name]['grade_data']['possession']-=1
        if player_info[name]['rating_data']['possession'] > 0:
          player_info[name]['rating_data']['possession'] -= 0.1

        if not taken_from_hand and throw_speed < exp_disc_speed:
            write_file(info['game_clock'], name, 'possession', '-1',
                       name + " loss possession and had threw the disc at " + str(throw_speed) + " and expected speed should be " + str(exp_disc_speed))
            player_info[name]['grade_data']['possession'] -= 1
            if player_info[name]['rating_data']['possession'] > 0:
                player_info[name]['rating_data']['possession'] -= 0.1
      else:
        write_file(info['game_clock'], name,'possession','-0.25', name + " loss possession; but had no pass options available")
  
  
  return

#function that awards player for being a pass option
#game info should have covered, open, and poss set
#will also save options
def record_poss_gain(gain_team, player, info):
  global player_info
  
  name = info['team'][gain_team]['player'][player]['name']
  # checking to see if player is goalie
  if info['team'][gain_team]['player'][player]['pre_goalie']:
    write_file(info['game_clock'], name,'goalie','1', name + " gained the disc from goalie possition")
    player_info[name]['grade_data']['goalie']+=1
  else:
    write_file(info['game_clock'], name,'possession','1', name + " gained possession of the disc")
    player_info[name]['grade_data']['possession']+=1
    
  return

def record_pass_options(team, info):
  global player_info
  global possession_rating
  
  for j in range(info['team'][team]['num_players']):
    if not info['team'][team]['player'][j]['poss']:
      if not info['team'][team]['player'][j]['covered'] and not info['team'][team]['player'][j]['lane_covered']:
        name = info['team'][team]['player'][j]['name']
          
        write_file(info['game_clock'], name,'possession','0.5', name + " was open for pass")
        player_info[name]['grade_data']['possession']+=0.5
    
  return


def record_success_pass(team, playerP, playerR, info):
  
  global player_info
  
  name = info['team'][team]['player'][playerR]['name']
  name1 = info['team'][team]['player'][playerP]['name']
  
  if name == name1:
    write_file(info['game_clock'], name,'possession','0', "Self Pass was preformed.")
    player_info[name]['grade_data']['possession']+=0
  else:
    if info['shot_taken']:

      write_file(info['game_clock'], name,'possession','1', name + " recovered " + name1 + "'s shot.")
      player_info[name1]['grade_data']['possession'] += 1
      if player_info[name1]['rating_data']['possession'] < 1:
        player_info[name1]['rating_data']['possession'] += 0.1

    else:
      # find out if this person was marked
      mark, was_marked = find_if_marked(team, playerR, False, info)
      
      if not info['team'][team]['player'][playerR]['covered']:
        write_file(info['game_clock'], name1,'possession','0.5', name1 + " completed pass to " + name + ".")
        player_info[name]['grade_data']['possession']+=0.5
        if player_info[name]['rating_data']['possession'] < 1:
          player_info[name]['rating_data']['possession'] += 0.1

        if was_marked:
          write_file(info['game_clock'], mark,'man_coverage','-0.5', mark + " was guarding " + name + " and wasn't close to them when they got the disc.")
          player_info[name1]['grade_data']['man_coverage']-=0.5

      else:
        write_file(info['game_clock'], name1,'possession','+0.5', name1 + " completed pass to " + name + " but he was guarded.")
        player_info[name]['grade_data']['possession']+=0.5

        if was_marked:
          write_file(info['game_clock'], mark,'man_coverage','0', mark + " was guarding " + name + " and they got the disc with high pressure.")

      write_file(info['game_clock'], name,'possession','1', name + " received a pass from " + name1 + ".")
      player_info[name1]['grade_data']['possession']+=1
      if player_info[name1]['rating_data']['possession'] < 1:
        player_info[name1]['rating_data']['possession'] += 0.1
    
  
  return

def record_danger_pass(team, player, info):
  
  global player_info
  
  name = info['team'][team]['player'][player]['name']

  passer = -1

  # checking to see if reciever was covered
  if info['team'][team]['player'][player]['covered']:

      # find index of passer
      passerid = info['team'][team]['passer']
      for j in range(info['team'][team]['num_players']):
          if info['team'][team]['player'][j]['id'] == passerid:
              passer_name = info['team'][team]['player'][j]['name']
              passer = j

  if passer != -1:
    write_file(info['game_clock'], passer_name,'possession','-1', passer_name + " pass to a guarded man.")
    player_info[passer_name]['grade_data']['possession'] -= 1
    if player_info[passer_name]['rating_data']['possession'] > 0:
      player_info[passer_name]['rating_data']['possession'] -= 0.1
  
  return

def record_bad_pass(team, player, info):
  global player_info
  
  name = info['team'][team]['player'][player]['name']
  
  if info['disc']['by_team']:
    name = info['team'][team]['player'][info['disc']['near_to']]['name']
    write_file(info['game_clock'], name,'possession','-1', name + " failed to catch the disc.")
    player_info[name]['grade_data']['possession'] -= 1
    if player_info[name]['rating_data']['possession'] > 0:
      player_info[name]['rating_data']['possession'] -= 0.1
  elif info['pass_intent'] != -1:
    name = info['team'][team]['player'][info['pass_intent']]['name']
    write_file(info['game_clock'], name,'possession','-0.5', name + " failed to catch the disc that was intended to them.")
    player_info[name]['grade_data']['possession'] -= 0.5
    if player_info[name]['rating_data']['possession'] > 0:
      player_info[name]['rating_data']['possession'] -= 0.1
  else:
    if not info['danger']:
      write_file(info['game_clock'], name,'possession','-1', name + " made a bad pass.")
      player_info[name]['grade_data']['possession'] -= 1
      if player_info[name]['rating_data']['possession'] > 0:
        player_info[name]['rating_data']['possession'] -= 0.1
    else:
      write_file(info['game_clock'], name,'possession','0', name + " made a bad pass but was under high pressure")

  return

# function that records man coverage results
# man_coverage function should have already been executed
def record_man_coverage(defense, info):
  global player_info
  global light_coverage
  global tight_coverage
  global defense_zone
  
  for j in range(info['team'][defense]['num_players']):
    name = info['team'][defense]['player'][j]['name']
    # checking to see if this is the goalie
    if info['team'][defense]['player'][j]['goalie']:
      write_file(info['game_clock'], name, 'goalie', '+0.5', name + " was covering the goal")
      player_info[name]['grade_data']['goalie'] += 0.5

    elif info['team'][defense]['player'][j]['stack']['locked']:
        if not info['recover']:
          # verify disc is in the offensive bubble
          stack_location = info['team'][defense]['player'][j]['location'][2] * info['team'][defense]['team_sign']
          if info['disc']['position'][2] * info['team'][defense]['team_sign'] >= defense_zone and info['team'][defense]['player'][j]['stack']['stacked']:
              if stack_location >= defense_zone:
                write_file(info['game_clock'], name, 'stack_control', '-0.5', name + " was stacked during bubble defense")
                player_info[name]['grade_data']['stack_control'] -= 0.5
              else:
                write_file(info['game_clock'], name, 'stack_control', '-0.25', name + " was stacked during bubble defense; but was not in the defense zone yet")
                player_info[name]['grade_data']['stack_control'] -= 0.5

          else:
              write_file(info['game_clock'], name, 'stack_control', '1', name + " was in a stack defense")
              player_info[name]['grade_data']['stack_control'] += 1

    elif info['team'][defense]['player'][j]['covered']:
      index = np.argmin(info['team'][defense]['player'][j]['distance'])
      if info['team'][defense]['player'][j]['distance'][index] <= tight_coverage:
        write_file(info['game_clock'], name,'man_coverage','1', name + " had tight man coverage")
        player_info[name]['grade_data']['man_coverage']+=1
      else:
        write_file(info['game_clock'], name,'man_coverage','0.5', name + " had loose man coverage")
        player_info[name]['grade_data']['man_coverage']+=0.5

    #man was not covered
    elif info['team'][defense]['player'][j]['lane_covered']:
      write_file(info['game_clock'], name,'lane_coverage','1', name + " blocked the lane")
      player_info[name]['grade_data']['lane_coverage']+=1
    # checking to see if disc is in the defense half and it isn't the first pass after a clear
    elif info['disc']['position'][2] * info['team'][defense]['team_sign'] > 0 and not info['pre_clear_flag']:
      write_file(info['game_clock'], name, 'man_coverage', '-0.5', name + " was not covering a man")
      player_info[name]['grade_data']['man_coverage'] -= 0.5

  return

# function to record a clear for a team
def record_disc_clear(info):
  global clear_rating
  global player_info
  global defense_zone
  
  team = info['last_poss_team']
  player = info['last_poss_player']
  
  name = info['team'][team]['player'][player]['name']

  disc = info['disc']['position'][2]

  if disc * info['team'][team]['team_sign'] > defense_zone:
    write_file(info['game_clock'], name,'clear','-1', name + " attempted to clear the disc and it stayed in the defense.")
    player_info[name]['grade_data']['clear']-=1
  elif info['team'][team]['clear'] > clear_rating:
    write_file(info['game_clock'], name,'clear','0.5', name + " cleared the disc and team clear rating is " + str(info['team'][team]['clear']))
    player_info[name]['grade_data']['clear']+=0.5
  elif info['danger']:
    write_file(info['game_clock'], name,'clear','0', name + " cleared the disc and team clear rating is " + str(info['team'][team]['clear']) + "; but player was in danger.")
  else:
    write_file(info['game_clock'], name,'clear','-0.5', name + " cleared the disc and team clear rating is " + str(info['team'][team]['clear']) + "; and player was not in danger.")
    player_info[name]['grade_data']['clear']-=0.5
  
  return

# function to record recovering disc clear
def record_disc_clear_recover(team, player, info):
  
  global player_info
  
  name = info['team'][team]['player'][player]['name']
  
  # plager picked up a clear
  if info['team'][team]['clear_flag']:
    write_file(info['game_clock'], name,'clear','+1', name + " recovered own's team cleared disc")
    player_info[name]['grade_data']['clear']+=1
  else:
    write_file(info['game_clock'], name,'clear','+0.5', name + " gained possession of cleared disc")
    player_info[name]['grade_data']['clear']+=0.5

  return

def record_recovery(team, info):
  #team is the defense team
  global light_coverage
  global player_info

  find_dist_to_opp(team, info)
  find_dist_to_opp(not team, info)

  if info['disc']['position'][2] > 0:
      disc_side = 1
  else:
      disc_side = -1
  


  for k in range(2):
      for i in range(info['team'][k]['num_players']):
        name = info['team'][k]['player'][i]['name']
        if info['team'][k]['player'][i]['location'][2] * disc_side >  5:
          if team == k:
            write_file(info['game_clock'], name,'change_time','1', name + " returned to defense in time")
            player_info[name]['grade_data']['change_time']+=1
          else:
            write_file(info['game_clock'], name,'change_time','1', name + " returned to offense in time")
            player_info[name]['grade_data']['change_time']+=1
        elif not info['team'][k]['player'][i]['stack']['stunning']:
          if info['team'][k]['player'][i]['stack']['stack_stunning']:
            write_file(info['game_clock'], name,'change_time','-0.5', name + " was stacked and did not return in time")
            player_info[name]['grade_data']['change_time']-=0.5

          if team == k:
            write_file(info['game_clock'], name,'change_time','-1', name + " did not recover to defense in time")
            player_info[name]['grade_data']['change_time']-=1
          else:
            write_file(info['game_clock'], name,'change_time','-1', name + " did not recover to offense in time")
            player_info[name]['grade_data']['change_time']-=1

        info['team'][k]['player'][i]['stack']['stunning'] = False
        info['team'][k]['player'][i]['stack']['stack_stunning'] = False
        
  return

def record_recovery_stun(team, info):
    global light_coverage
    range_dist = light_coverage * 1.5

    if info['disc']['position'][2] > 0:
        disc_side = 1
    else:
        disc_side = -1

    find_dist_to_opp(team, info)
    find_dist_to_opp(not team, info)

    # function that evaluates stack stunning during recovery. will be ran about half way into recovery time
    for k in range(2):
        stack_stopper = list()
        stack_grade = list()
        coverage = list()
        punish = list()
        for i in range(info['team'][k]['num_players']):

            if info['team'][k]['player'][i]['location'][2] * disc_side < 5:
                # player is not trying to stun if they are stacked
                if not info['team'][k]['player'][i]['stack']['stacked']:

                    sort_distance = info['team'][k]['player'][i]['distance'].copy()
                    sort_distance.sort()
                    for j in range(len(sort_distance) - 1, -1, -1):  # count backwards through sort_distance
                        if sort_distance[j] < range_dist:
                            stack_stopper.append(i)
                            stack_grade.append(j)
                            break
                else:
                    info['team'][k]['player'][i]['stack']['stack_stunning'] = True
                    


        # checking to see if more then one person was stopping stacks
        if len(stack_stopper) > 1:
            for i in range(len(stack_stopper)):
                index_order = np.array(info['team'][k]['player'][stack_stopper[i]]['distance']).argsort()
                junk = index_order[:stack_grade[i] + 1]
                junk.sort()
                coverage.append(junk)

        i = 0
        j = 0
        while i < len(coverage):
            while j < len(coverage):
                if i < j:
                    if np.any(coverage[i] == coverage[j]):
                        if stack_grade[i] > stack_grade[j]:
                            punish.append(stack_stopper.pop(j))
                            coverage.pop(j)
                            stack_grade.pop(j)
                            j -= 1
                        elif stack_grade[i] < stack_grade[j]:
                            punish.append(stack_stopper.pop(i))
                            coverage.pop(i)
                            stack_grade.pop(i)
                            i -= 1
                            break
                        # grade matches, now check distance. Add all distances to covered people. This is the most right person
                        else:
                            points = np.array([0, 0])
                            for l in range(len(coverage[i])):
                                distance_i = info['team'][k]['player'][stack_stopper[i]]['distance2'][coverage[i][l]]
                                distance_j = info['team'][k]['player'][stack_stopper[j]]['distance2'][coverage[j][l]]
                                diff_distance = distance_i - distance_j
                                # if both players were this close to the player, they did not have an advantage for that man
                                if abs(diff_distance) > light_coverage:
                                    if diff_distance < 0:
                                        points[0] += 1
                                    else:
                                        points[1] += 1

                            if points[0] > points[1]:
                                punish.append(stack_stopper.pop(j))
                                coverage.pop(j)
                                stack_grade.pop(j)
                                j -= 1
                            elif points[0] < points[1]:
                                punish.append(stack_stopper.pop(i))
                                coverage.pop(i)
                                stack_grade.pop(i)
                                i -= 1
                                break
                            # both will be punished
                            else:
                                punish.append(stack_stopper.pop(j))
                                coverage.pop(j)
                                stack_grade.pop(j)
                                j -= 1
                                punish.append(stack_stopper.pop(i))
                                coverage.pop(i)
                                stack_grade.pop(i)
                                i -= 1
                                break

                j += 1
            i += 1


        for i in range(len(punish)):
            name = info['team'][k]['player'][punish[i]]['name']

            write_file(info['game_clock'], name, 'change_time', '-0.5',
                       name + " was attempting to stun stacks when another player was already doing it")
            player_info[name]['grade_data']['change_time'] -= 0.5

        for i in range(len(stack_stopper)):
            name = info['team'][k]['player'][stack_stopper[i]]['name']
            info['team'][k]['player'][stack_stopper[i]]['stack']['stunning'] = True

            # k is the defense team
            if k == team:
                # only gets points if this gives them a number advantage
                if stack_grade[i]:
                    write_file(info['game_clock'], name, 'change_time', '+1',
                               name + " was tied up with more then 1 offensive player")
                    player_info[name]['grade_data']['change_time'] += 1
                # stopped a player, but offense has a better advantage now
                else:
                    write_file(info['game_clock'], name, 'change_time', '-0.5',
                               name + " was tied up with only 1 offensive player")
                    player_info[name]['grade_data']['change_time'] -= 0.5
            # offensive team
            else:
                # No need to keep one man tied up, but it does give a better advantage
                if stack_grade[i]:
                    write_file(info['game_clock'], name, 'change_time', '+1',
                               name + " was tied up with more then 1 defensive player")
                    player_info[name]['grade_data']['change_time'] += 1
                # stopped a player, but offense has a better advantage now
                else:
                    write_file(info['game_clock'], name, 'change_time', '+0.5',
                               name + " was tied up with only 1 defensive player")
                    player_info[name]['grade_data']['change_time'] += 0.5

    return

def record_coverage_flags(offense, info):
  
  record_man_coverage(not offense, info)
  record_pass_options(offense, info)
  
  return


def record_save(status, info):
    global player_info

    for i in range(2):
        if info['team'][i]['present']:
            for player in status['teams'][i]['players']:
                # checking to see if saves in game are less than saves in records
                if player_info[player['name']]['stat_data']['saves'] > player['stats']['saves']:
                    # moving recorded saves to drop so info is not lost and setting info equal to API
                    player_info[player['name']]['stat_data']['drop_saves'] += player_info[player['name']]['stat_data'][
                        'saves']
                    player_info[player['name']]['stat_data']['saves'] = player['stats']['saves']

                # checking to see if saves has increased
                while(player_info[player['name']]['stat_data']['saves'] < player['stats']['saves']):
                    player_info[player['name']]['stat_data']['saves'] += 1
                    write_file(info['game_clock'], player['name'], 'goalie', '+1',
                               player['name'] + " made a save")
                    player_info[player['name']]['grade_data']['goalie'] += 1

    return

def record_steals(status, info):
    global player_info

    for i in range(2):
        if info['team'][i]['present']:
            for player in status['teams'][i]['players']:
                # checking to see if saves in game are less than saves in records
                if player_info[player['name']]['stat_data']['steals'] > player['stats']['steals']:
                    # moving recorded saves to drop so info is not lost and setting info equal to API
                    player_info[player['name']]['stat_data']['drop_steals'] += player_info[player['name']]['stat_data'][
                        'steals']
                    player_info[player['name']]['stat_data']['steals'] = player['stats']['steals']

                # checking to see if saves has increased
                while(player_info[player['name']]['stat_data']['steals'] < player['stats']['steals']):
                    player_info[player['name']]['stat_data']['steals'] += 1
                    write_file(info['game_clock'], player['name'], 'steals', '+1',
                               player['name'] + " made a steal")
                    player_info[player['name']]['grade_data']['steals'] += 1

    return
  
  
def record_stuns(status, info):
  global player_info
  
  for i in range(2):
    if info['team'][i]['present']:
      for player in status['teams'][i]['players']:
        # checking to see if stuns in game are less than stuns in records
        if player_info[player['name']]['stat_data']['stuns'] > player['stats']['stuns']:
          # moving recorded stuns to drop so info is not lost and setting info equal to API
          player_info[player['name']]['stat_data']['drop_stuns'] += player_info[player['name']]['stat_data']['stuns']
          player_info[player['name']]['stat_data']['stuns'] = player['stats']['stuns']
        
        # checking to see if stuns has increased
        while(player_info[player['name']]['stat_data']['stuns'] < player['stats']['stuns']):
          player_info[player['name']]['stat_data']['stuns'] += 1
          write_file(info['game_clock'], player['name'],'stuns','+0.5', player['name'] + " stunned an opponent")
          player_info[player['name']]['grade_data']['stuns']+=0.5
            
        if player['stunned']:
          if not player_info[player['name']]['stat_data']['stunned']:
            write_file(info['game_clock'], player['name'],'stuns','-0.5', player['name'] + " was stunned by an opponent")
            player_info[player['name']]['grade_data']['stuns']-=0.5
            player_info[player['name']]['stat_data']['stunned'] = True
        else:
            player_info[player['name']]['stat_data']['stunned'] = False
            
  
  return

def record_shot_miss(poss_team, info):
  global player_info

  if info['shot_recovered']:
    for i in range(2):
      for j in range(info['team'][i]['num_players']):
        name = info['team'][i]['player'][j]['name']
        if player_info[name]['stat_data']['shot_taken']:
          player_info[name]['stat_data']['shot_taken'] = False
          info['shot_taken'] = False
          if player_info[name]['rating_data']['shot'] > 0:
            player_info[name]['rating_data']['shot'] -= 0.1
          if i != poss_team:
            write_file(info['game_clock'], name,'shot','-1', name + " missed the shot and resulted in a turn over")
            player_info[name]['grade_data']['shot']-=1
          else:
            write_file(info['game_clock'], name,'shot','-0.5', name + " missed the shot but team kept possession")
            player_info[name]['grade_data']['shot']-=0.5

    clear_shot_status(player_info, info)

  return


def record_shot_made(status, info):
  global player_info
  global goal_coverage
  global return_time
  global shot_time
  
  scorer = status['last_score']['person_scored']
  assister = status['last_score']['assist_scored']
  amount = status['last_score']['point_amount']
  distance = status['last_score']['distance_thrown']
  speed = status['last_score']['disc_speed']
  pocket = disc_in_pocket(info['disc']['position'])

  if status['last_score']['team'] == "blue":
    team = 0
  else:
    team = 1

  # setting joust poss
  info['team'][not team]['joust_poss'] = True

  # checking to see if person credited for goal is on the same team
  own_goal = True
  if 'players' in status['teams'][team]:
    for index, player1 in enumerate(status['teams'][team]['players']):
      if scorer == player1['name']:
        own_goal = False
        player = index
      
  if not own_goal:
    if player_info[scorer]['rating_data']['shot'] < 1:
      player_info[scorer]['rating_data']['shot'] += 0.1
    if not info['team'][not team]['goalie']:
      write_file(info['game_clock'], scorer,'shot','+1', scorer + " scored a " + str(amount) + " point goal from " + str(distance) + " meters away at " + str(speed) + " m/s on an open net.")
      player_info[scorer]['grade_data']['shot']+=1
    elif pocket:
      write_file(info['game_clock'], scorer,'shot','+1', scorer + " scored a " + str(amount) + " point goal from " + str(distance) + " meters away at " + str(speed) + " m/s into a pocket.")
      player_info[scorer]['grade_data']['shot']+=1
    else:
      write_file(info['game_clock'], scorer,'shot','+0.5', scorer + " scored a " + str(amount) + " point goal from " + str(distance) + " meters away at " + str(speed) + " m/s on guarded net.")
      player_info[scorer]['grade_data']['shot']+=0.5
    #setting shot made flag
    player_info[scorer]['stat_data']['shot_made'] = True
    # recording assist
    ###Need to check what unassisted goal reads###
    if assister != "[INVALID]":
      if player_info[assister]['rating_data']['shot'] < 1:
        player_info[assister]['rating_data']['shot'] += 0.1
      write_file(info['game_clock'], assister,'shot','+0.5', assister + " assisted " + scorer + " goal")
      player_info[assister]['grade_data']['shot']+=0.5
  # is an own goal, checking to see if it was a headbutt
  else:
    
    # other team head butt scored the goal, find who actually shot the disc
    for i in range(info['team'][team]['num_players']):
      name = info['team'][team]['player'][i]['name']
      if player_info[name]['stat_data']['shot_taken']:
        # clearing flgas
        player_info[name]['stat_data']['shot_taken'] = False
        info['shot_taken'] = False
        
        own_goal = False
        player = i
        # Awarding the point
        if player_info[name]['rating_data']['shot'] < 1:
          player_info[name]['rating_data']['shot'] += 0.1
        write_file(info['game_clock'], name,'shot','+0.5', name + " scored of the head of " + scorer + ".")
        player_info[name]['grade_data']['shot']+=0.5
        scorer = name
        # Awarding the assist
        if info['team'][team]['pre_passer'] != -1:
          passer = info['team'][team]['pre_passer']
          for j in range(info['team'][team]['num_players']):
            if info['team'][team]['player'][j]['id'] == passer:
              assister = info['team'][team]['player'][j]['name']
              write_file(info['game_clock'], assister,'shot','+0.5', assister + " assisted " + name + ".")
              player_info[assister]['grade_data']['shot']+=0.5
              if player_info[assister]['rating_data']['shot'] < 1:
                player_info[assister]['rating_data']['shot'] += 0.1

  if own_goal:
    team = not team
    #finding which index the scorer was
    pindex = -1
    for i in range(info['team'][team]['num_players']):
      if info['team'][team]['player'][i]['name'] == scorer:
        pindex = i
    # checking to see if player was the goalie.
    if pindex != -1:
      if info['team'][team]['player'][pindex]['goal_dist'] <= goal_coverage:
        write_file(info['game_clock'], scorer,'goalie','-0.5', scorer + " scored while trying to save the disc.")
        player_info[scorer]['grade_data']['goalie']-=0.5
      else:
        write_file(info['game_clock'], scorer,'possession','-1', scorer + " scored a self goal.")
        player_info[scorer]['grade_data']['possession']-=1
  else:
    #grading keeper
    if info['team'][not team]['goalie']:
      for i in range(info['team'][not team]['num_players']):
        if info['team'][not team]['player'][i]['goalie']:
          goalie = info['team'][not team]['player'][i]['name']
          # checking to see if goalie was stunned
          if not player_info[goalie]['stat_data']['stunned']:

            if amount == 3:
              write_file(info['game_clock'], goalie, 'goalie', '-1', goalie + " failed to stop a 3.")
              player_info[scorer]['grade_data']['goalie'] -= 1
            else:
              # disc was not released
              if info['release_time'] > info['poss_time']:
                write_file(info['game_clock'], goalie, 'goalie', '0', goalie + " failed to stop a dunk.")
              elif info['release_time'] - info['game_time'] > shot_time:
                write_file(info['game_clock'], goalie, 'goalie', '-1', goalie + " failed to stop the disc; shot took longer then " + str(shot_time) + ".")
                player_info[scorer]['grade_data']['goalie'] -= 1
              else:
                write_file(info['game_clock'], goalie, 'goalie', '0', goalie + " failed to stop the disc; shot took less then " + str(shot_time) + ".")

          else:
              write_file(info['game_clock'], goalie, 'goalie', '0', goalie + " was stunned durning the shot.")

    # punish person who was guarding shooter
    mark, was_marked = find_if_marked(team, player, True, info)
    if was_marked:
      write_file(info['game_clock'], mark, 'man_coverage', '-1',
                 mark + " was guarding " + scorer + " and this player scored.")
      player_info[mark]['grade_data']['man_coverage'] -= 1


  #checking to see if goal was breakaway
  if info['timer'] - info['game_time'] <= return_time:
    info['recover'] = False
    record_recovery(not team, info)
  
  # clear shots flags to start joust
  set_shots(status, info)
  clear_shot_status(player_info, info)
  info['shot_made'] = True

  return

def record_pass_lane_error(oteam, player, info):
  
  name = info['team'][oteam]['player'][player]['name']

  write_file(info['game_clock'], name, 'possession', '-0.5', name + " failed to get in a passing lane.")
  player_info[name]['grade_data']['possession'] -= 0.5
  
  return


def record_stack_disc(team, player1, player2, info, recovered = 0):
  # recovered flag is 0 for miss, 1 for stay near disc, and 2 for recovered the disc
  global player_info

  name1 = info['team'][team]['player'][player1]['name']
  name2 = info['team'][team]['player'][player2]['name']

  if not recovered:
      write_file(info['game_clock'], name1, 'stack_control', '-1', name1 + " and " + name2 + " over ran the disc as a stack.")
      player_info[name1]['grade_data']['stack_control'] -= 1
      write_file(info['game_clock'], name2, 'stack_control', '-1', name2 + " and " + name1 + " over ran the disc as a stack.")
      player_info[name2]['grade_data']['stack_control'] -= 1
  else:
      if recovered == 2:
          write_file(info['game_clock'], name1, 'stack_control', '+1', name1 + " and " + name2 + " recovered the disc as a stack.")
          player_info[name1]['grade_data']['stack_control'] += 1
          write_file(info['game_clock'], name2, 'stack_control', '+1', name2 + " and " + name1 + " recovered the disc as a stack.")
          player_info[name2]['grade_data']['stack_control'] += 1
      elif recovered == 1:
          write_file(info['game_clock'], name1, 'stack_control', '+0.5', name1 + " and " + name2 + " stacked to form high pressure on the disc.")
          player_info[name1]['grade_data']['stack_control'] += 0.5
          write_file(info['game_clock'], name2, 'stack_control', '+0.5', name2 + " and " + name1 + " stacked to form high pressure on the disc.")
          player_info[name2]['grade_data']['stack_control'] += 0.5

  return

def record_stack_turn(team, player1, player2, info, moving = False):
  global player_info
  
  name1 = info['team'][team]['player'][player1]['name']
  name2 = info['team'][team]['player'][player2]['name']
  
  if not moving:
    write_file(info['game_clock'], name1, 'stack_control', '+0.5', name1 + " and " + name2 + " stopped as a stack.")
    player_info[name1]['grade_data']['stack_control'] += 0.5
    write_file(info['game_clock'], name2, 'stack_control', '+0.5', name2 + " and " + name1 + " stopped as a stack.")
    player_info[name2]['grade_data']['stack_control'] += 0.5
      
  else:
    write_file(info['game_clock'], name1, 'stack_control', '+0.5', name1 + " and " + name2 + " turned in a stack.")
    player_info[name1]['grade_data']['stack_control'] += 0.5
    write_file(info['game_clock'], name2, 'stack_control', '+0.5', name2 + " and " + name1 + " turned in a stack.")
    player_info[name2]['grade_data']['stack_control'] += 0.5
  
  return

# will track which player lost the disc.
# takes team number of player that lost the disc and game_info object
def set_coverage_flags(offense, player, info):
  
  man_coverage(not offense, info)
  find_pass_options(offense, player, info)
  
  return

# setting danger flag after disc is released
def set_danger_flag(Dteam, info):
  global tight_coverage
  
  danger = False
  for j in range(info['team'][Dteam]['num_players']):
    plocation = info['team'][Dteam]['player'][j]['location']
    pvelocity = info['team'][Dteam]['player'][j]['velocity']
    location = info['disc']['position']
    if(player_near_location(plocation,pvelocity,location,tight_coverage)):
      danger = True

  info['danger'] = danger
  
  return

# function used to move current status to prestatus for next cycle
def setup_for_next_cycle(info):
  global threading
  global t1

  threading['pre_threading'] = threading['threading']
  if threading['thread_cycle']:
    if t1.is_alive():
      threading['continue'] = True
      threading['queue'] += 1
    else:
      print("New_thread")
      t1 = t1.clone(target=thread_process)
      t1.start()
  threading['thread_cycle'] = False
  
  info['pre_poss'] = info['poss']
  info['pre_field_state'] = info['field_state']
  info['disc']['pre_bounce'] = info['disc']['bounce']
  for i in range(2):
    info['team'][i]['pre_num_players'] = info['team'][i]['num_players']
    info['team'][i]['dropped_player'] = False
    info['team'][i]['pre_present'] = info['team'][i]['present']
    for k in range(info['team'][i]['num_players']):
      info['team'][i]['player'][k]['pre_poss'] = info['team'][i]['player'][k]['poss']
      info['team'][i]['player'][k]['pre_goalie'] = info['team'][i]['player'][k]['goalie']
      
      
  return

def setup_for_joust(info):
  info['poss'] = "None"
  info['pre_poss'] = "None"
  info['pre_field_state'] = info['field_state']
  info['timer'] = 0
  info['recover'] = False
  info['recover_stun'] = False
  info['clear_flag'] = False
  info['pre_clear_flag'] = False
  info['danger'] = False
  info['goalie'] = False
  info['dropped_player'] = False
  info['last_poss_team'] = -1
  info['last_poss_player'] = -1
  info['disc']['live'] = False
  info['disc']['bounce'] = 0
  info['disc']['pre_bounce'] = 0
  info['disc']['held'] = False
  info['disc']['wait'] = False
  info['shot_pause'] = False
  info['info_logged'] = False
  
  for i in range(2):
    info['team'][i]['clear_flag'] = False
    info['team'][i]['passer'] = -1
    info['team'][i]['pre_passer'] = -1
    
    for k in range(5):
      info['team'][i]['player'][k]['poss'] = False
      info['team'][i]['player'][k]['pre_poss'] = False
      info['team'][i]['player'][k]['covered'] = False
      info['team'][i]['player'][k]['lane_covered'] = False
      info['team'][i]['player'][k]['goalie'] = False
      info['team'][i]['player'][k]['pre_goalie'] = False
      info['team'][i]['player'][k]['distance'] = [80,80,80,80,80]
      info['team'][i]['player'][k]['distance2'] = [80,80,80,80,80]
      info['team'][i]['player'][k]['goal_dist'] = 80
      info['team'][i]['player'][k]['mark'] = -1
      info['team'][i]['player'][k]['pre_mark'] = -1
      info['team'][i]['player'][k]['stack']['stacked'] = False
      info['team'][i]['player'][k]['stack']['broken'] = True
      info['team'][i]['player'][k]['stack']['locked'] = False
      info['team'][i]['player'][k]['stack']['jousting'] = False
      info['team'][i]['player'][k]['stack']['turn'] = False
      info['team'][i]['player'][k]['stack']['partner'] = -1
      info['team'][i]['player'][k]['stack']['pre_velocity'] = [0,0,0]
      info['team'][i]['player'][k]['stack']['time'] = 0
      info['team'][i]['player'][k]['stack']['stunning'] = False
      info['team'][i]['player'][k]['stack']['stack_stunning'] = False
      info['team'][i]['player'][k]['stack']['near_disc'] = False
      info['team'][i]['player'][k]['leached'] = False
      info['team'][i]['player'][k]['leach_opp'] = -1

  return

def evaluate_structure(status, game_info):
    global player_info      # only used to clear for consecative games
    
    #calling function that runs every scan
    evaluate_every_scan(status, game_info)

    if not game_info['disc']['live']:
      game_info['release_time'] = game_info['game_time']
      game_info['poss_time'] = game_info['game_time']
      game_info['pre_poss_time'] = game_info['poss_time']
      game_info['pre_field_state'] = game_info['field_state']

    if status['game_status'] == "playing":
        game_info['disc']['live'] = True
        evaluate_play(status, game_info)
        if not game_info['game_live']:
          game_info['game_live'] = True
          if file_info['new_file_needed']:
            file_info['new_file_needed'] = False
            create_new_file()
        
    elif status['game_status'] == "score":
        if game_info['disc']['live']:
          if game_info['shot_pause']:
            record_shot_made(status, game_info)
            setup_for_joust(game_info)
            game_info['disc']['live'] = False
          else:
            time_mod.sleep(1)
            game_info['shot_pause'] = True

    elif status['game_status'] == "round_start":
        if game_info['disc']['live']:
          find_disc_position(status, game_info)
          setup_for_joust(game_info)
          game_info['disc']['live'] = False
        if not game_info['game_live']:
          game_info['game_live'] = True
          if file_info['new_file_needed']:
            file_info['new_file_needed'] = False
            create_new_file()
        if game_info['first_poss']:
          game_info['first_poss'] = False
          set_shots(status, game_info)
          clear_shot_status(player_info, game_info)
        
    elif status['game_status'] == "round_over":
        if game_info['disc']['live']:
          setup_for_joust(game_info)
          game_info['disc']['live'] = False
        
    elif status['game_status'] == "post_match" or status['game_status'] == "pre_match":
        if game_info['disc']['live']:
          setup_for_joust(game_info)
          game_info['disc']['live'] = False
        if game_info['game_live']:
          game_info['game_live'] = False
          file_info['new_file_needed'] = True
          log_player_performance(game_info)
          game_info['possNum'] = 0
          for i in range(2):
              for j in range(game_info['team'][i]['num_players']):
                  name = game_info['team'][i]['player'][j]['name']
                  print(name + " had a poss time of " + str(status['teams'][i]['players'][j]['stats']['possession_time']))
           
    elif status['game_status'] == "pre_sudden_death":
        if game_info['disc']['live']:
          setup_for_joust(game_info)
          game_info['disc']['live'] = False
        if not game_info['game_live']:
          game_info['game_live'] = True
        if game_info['first_poss']:
            game_info['first_poss'] = False
            set_shots(status, game_info)
            clear_shot_status(player_info, game_info)
        
    elif status['game_status'] == "post_sudden_death":
        if game_info['disc']['live']:
          setup_for_joust(game_info)
          game_info['disc']['live'] = False

    setup_for_next_cycle(game_info)

    return
  
# sprocess that runs regardless of game state
def evaluate_every_scan(status, game_info):
    
    # set disc location
    game_info['disc']['position'] = status['disc']['position']
    game_info['disc']['velocity'] = np.round(status['disc']['velocity'],2)
    # game_info['disc']['bounce'] = status['disc']['bounce_count']
    
    # checking to see if we have players on each team
    game_info['team'][0]['present'] = 'players' in status['teams'][0]
    game_info['team'][1]['present'] = 'players' in status['teams'][1]
    #getting time
    game_info['game_time'] = status['game_clock']
    game_info['game_clock'] = status['game_clock_display']

    #setup disc position
    find_disc_position(status, game_info)
    
    # creating the player info dictionary for all active players
    creating_player_info(status["teams"])

    update_game_info(status, game_info)
    
    return

# main function to grade players
def evaluate_play(status, game_info):
    global clear_time

    # checking shot status
    set_shots(status, game_info)

    # checking stacks
    find_stacks(status, game_info)
    
    # finding who has the disc
    team, player = find_who_poss(status, game_info)
    find_disc_bounce(status, game_info)
    
    # setting possesstion flags
    if team == 0:
      game_info['poss'] = "Blue"
      # checking field position
      if game_info['field_state'] == 1:
        find_goalie(not team, game_info)
      else:
        clear_goalie(not team, game_info)
      
    elif team == 1:
      game_info['poss'] = "Orange"
      if game_info['field_state'] == -1:
        find_goalie(not team, game_info)
      else:
        clear_goalie(not team, game_info)
            
    elif (game_info['release_time'] - game_info['game_time']) > clear_time:
      game_info['poss'] = "None"

    # if possession changed hands
    if game_info['poss'] != game_info['pre_poss']:

        if game_info['poss'] != 'None' and game_info['pre_poss'] != 'None':
            # this function depends on threaded result
            if threading['thread_cycle']:
                threading['poss_loss'][-1] = True
            else:
                record_poss_loss(not team, game_info)

            record_poss_gain(team, player, game_info)
        # if poss changed to None, a bad pass was made
        elif game_info['poss'] == 'None':
            if not game_info['clear_flag']:
                record_bad_pass(game_info['last_poss_team'], game_info['last_poss_player'], game_info)

        # possession has changed to anything but None
        if team != -1:
            clear_poss(not team, game_info)

    # checking to see if disc moved from one area to another
    if game_info['field_state'] != game_info['pre_field_state']:
      # checking to see if disc moved from center to goal
      if game_info['pre_field_state'] == 0:
        game_info['timer'] = game_info['game_time']
        game_info['recover'] = True
        # get players positions for recovery avaluation later
        find_dist_to_opp(0, game_info, True)
        find_dist_to_opp(1, game_info, True)
        # orange cleared the disc
        if game_info['field_state'] == -1 and game_info['poss'] == "Orange" and team == -1:
          game_info['team'][1]['clear_flag'] = True
          game_info['clear_flag'] = True
        # Blue cleared the disc
        elif game_info['field_state'] == 1 and game_info['poss'] == "Blue" and team == -1:
          game_info['team'][0]['clear_flag'] = True
          game_info['clear_flag'] = True
        # disc floated out of defense zone greater then clear time
        elif game_info['poss'] == "None":
          # team will need to recover
          if game_info['field_state'] == -1:
            # not a self clear
            if game_info['last_poss_team'] == 1:
              game_info['team'][game_info['last_poss_team']]['clear_flag'] = True
              game_info['clear_flag'] = True

          else:
            # not a self clear
            if game_info['last_poss_team'] == 0:
              game_info['team'][game_info['last_poss_team']]['clear_flag'] = True
              game_info['clear_flag'] = True
      else:
        clear_recover(game_info)

    # checking to see if the defense tried to clear
    # disc on defensive side
    if game_info['field_state'] == -1:
      if game_info['disc']['bounce'] > 1 and game_info['last_poss_team'] == 0:
        game_info['clear_flag'] = True
        game_info['team'][0]['clear_flag'] = True

    elif game_info['field_state'] == 1:
      if game_info['disc']['bounce'] > 1 and game_info['last_poss_team'] == 1:
        game_info['clear_flag'] = True
        game_info['team'][1]['clear_flag'] = True
        
      
    # evaluating players after timer is up
    if game_info['recover']:
      evaluate_recovery(game_info)

    # monitor passes
    # set clears
    if team != -1:
      if not game_info['team'][team]['player'][player]['pre_poss']:
        
        print("New Poss " + str(game_info['possNum']) + " at " + game_info['game_clock'])
        game_info['possNum'] += 1

        # clearing joust poss
        game_info['team'][team]['joust_poss'] = False
        game_info['team'][not team]['joust_poss'] = False

        # flag triggered after first disc grab
        if game_info['first_poss']:
            game_info['first_poss'] = False
            clear_shot_status(player_info, game_info)


        # pass grading
        set_danger_flag(not team, game_info)

        if not game_info['clear_flag']:
          if game_info['team'][team]['passer'] != -1:
            # find index of passer
            passerid = game_info['team'][team]['passer']
            passer = -1
            for j in range(game_info['team'][team]['num_players']):
              if game_info['team'][team]['player'][j]['id'] == passerid:
                passer = j

            # if passer dropped, give credit to position 5.
            if passer == -1:
              passer = 4

            record_success_pass(team, passer, player, game_info)

        #checking to see if the pass was to a guarded man
        record_danger_pass(team, player, game_info)

        #clear grading
          
        # evaluating if team clear status needs to be changed
        if game_info['clear_flag']:
          # disc is only a clear if the disc bounced at least once before pickup
          if game_info['disc']['pre_bounce'] > 0:
            record_disc_clear(game_info)
            record_disc_clear_recover(team, player, game_info)
            # checking to see if current team is the team that cleared
            if game_info['team'][team]['clear_flag']:
              if game_info['team'][team]['clear'] < 1:
                game_info['team'][team]['clear'] += 0.1
            else:
              if game_info['team'][not team]['clear'] > 0:
                game_info['team'][not team]['clear'] -= 0.1

            game_info['pre_clear_flag'] = True

          game_info['clear_flag'] = False
          game_info['team'][1]['clear_flag'] = False
          game_info['team'][0]['clear_flag'] = False
        elif game_info['pre_clear_flag']:
          game_info['pre_clear_flag'] = False

        # if defense got the disc, no longer need to recover
        if game_info['recover'] and (team == 1 and game_info['field_state'] == 1) or (team == 0 and game_info['field_state'] == -1):
          clear_recover(game_info)

    #evaluating stuns
    record_stuns(status, game_info)
    
    #evaluate saves
    record_save(status, game_info)

    #recording shots
    record_shot_miss(team, game_info)

    #recording poss time
    calculate_poss_time(game_info['last_poss_team'], game_info['last_poss_player'], game_info)

    # moving who last had poss
    # checking to see if the disc went by a team member
    if team != -1:
      game_info['last_poss_team'] = team
      game_info['last_poss_player'] = player
    else:
      if game_info['disc']['pre_bounce'] != game_info['disc']['bounce'] and game_info['disc']['bounce'] == 1:
        grade_pass(game_info['last_poss_team'], game_info['last_poss_player'], True, game_info)

      if game_info['pass_intent'] != -1:
        # seeing if disc is near a team member if pass was not right on target
        player_near_disc(game_info)

    # # testing flags
    # global test
    # if game_info['team'][0]['goalie']:
    #     if not test:
    #         print("Blue Goalie Set")
    #         test = True
    # else:
    #     if test:
    #         print("Blue Goalie Unset")
    #         test = False
    
    return
        


def main():
    global api_info
    global game_info
    # creating thread

    # flag used to prevent constant file creation on retry attempts
    if file_info['new_file_needed']:
      if not file_info['error_occured']:
        # creating blank dictionaries
        create_game_info(game_info)
    
        # setting up log file
        logging.basicConfig(filename=error_log, level=logging.ERROR)
      
    # setup index_z
    z_index()

    # loop to cycle through program
    while True:
        try:
            # retrieve data from server and check to see what the game status is
            current_status = echovr_api.fetch_state_data()
            api_info = current_status
            evaluate_structure(current_status, game_info)
            if file_info['error_occured']:
                file_info['error_occured'] = False

        # had a lot of KeyError going through the file writing with the dictionaries
        # this is added to make trouble shooting easier
        except (ConnectionError, json.decoder.JSONDecodeError):

            if game_info['game_live']:
                game_info['game_live'] = False
                file_info['new_file_needed'] = True
                if not game_info['info_logged']:
                  log_player_performance(game_info)                     # initializing player info dictionary (all player info is stored here)

            # time_mod.sleep(5)

            #try again
            main()

        # log any other error in the crash log
        except:

            print("ERROR")
            print(traceback.format_exc())

            if not game_info['info_logged']:
                log_player_performance(game_info)

            logging.exception(sys.exc_info()[0])
            # print(game_info)
            # print(api_info)
            # print(json.dumps(game_info, indent = 2))
            exit(0)


# global variable for threading
t1 = RestartableThread(target=thread_process)
create_game_info(game_info)
setup_file_info(file_info)

if __name__ == "__main__":
    main()
