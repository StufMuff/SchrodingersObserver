# Schrödinger's Observer 
-Created by Jeremy Stufflebeem (StufMuff)

![alt text](https://github.com/StufMuff/SchrodingersObserver/blob/main/Images/Observer_V100.png "Example Of GUI")

## Release Notes:
  This release is to highlight the basic idea of what the script is capable of. Not by any means has the information been "perfected"
The evaluation given is to give players an idea of what areas of the game are weaker. For example, to have one game with "man_coverage"
may not mean much. But to have 10 games with "man_coverage" being low could indicate that is a players weak point

  The GUI is a simple Tkinter GUI to make using the scripts easier for everyone. A person just has to download the zip file and run the 
EXE. More info in the setup section

* update 2/5/22

  Changed naming format on the files. Now they all match and will lineup to make game review eaiser. Included logic to handle reset being
hit in a private match. Changed when the files will be wrote so they are all wrote at the same time. Switched to allow GUI to show averages 
in between rounds. Corrected active player logic. Now player will only be considered active if they enter the tunnel.

* update 7/4/22
  1.  Added version under menu
  1.  Added deep linking ability for PC users
    *  Can create spark links by using "Spark Features" Menu
    *  Can use spark link by pasting spark link into "Use Spark" under "Spark Features"
  1.  Added more stats to compare!
    *  Catches and passes are tracked (even in private matches)
    *  Assist is broken into two areas - Assist (in the bubble) and 3pt assist
    *  Goals are now tracked
    *  Number of 3pt goals are now tracked
    *  Shots taken and saves are still off api
    *  Blocks are now tracked, note: API counts a block as a stun, we do not. But a block still goes toward your stun evaluation
    *  Possession time in state menu has been switched over to our possession
  1.  Added two streaming features
    *  New API interface. Can now access evaluation info and stats like an API!
    *  Alternativily, can save a live updated json to a file
  1.  Database Interface
    *  Now all the stats can be stored in a mysql database.
    *  Note: players will be added as they play, but team connections have to be made manually. 
    *  - User interface to update teams could be added per feature request in discord
  1.  New more accurate Replay Saving process
    *  Added replay process to another exe (replay_api.exe). Opens replay saving in another window
    *  Window will minimize right away.
    *  Added API controls to start and set replay information
    *  Do NOT close the window by hitting the "x". This will leave an unzipped replay file in the main folder
  1.  Corrected a bug on poss time recording that started mid game
  1.  Found a glitch when using auto connect. 
    *  After the first game the GUI takes a minute to actually show information on screen
    *  API and script are still functioning at full speed
    
## Link:
  * [Link to the github](https://github.com/StufMuff/SchrodingersObserver)
    
    1. Download branch as a zip folder
    2. Unzip to any desired loaction
    3. Run schrodingersObserver_GUI.exe

       *  Note: running unathorized EXE will be flaged and have to be bypassed to run (this should happen the first time only)
  * [link to discord](https://discord.gg/2uJyQD3w7X)
  
## GUI Notes
  You have 6 tabs of information. Each tab show another characteristic that is provided. The main focus is to refine the evaluation 
portion. However, the other portions have been added for the users pleasure. Evaluation data, speed data, and stack data is saved csv
files to be reviewd. Stats are only a shinny add on for a reference of game recap.

### Getting Started
  The first things to note are the LED's on the bottom of the GUI. This is to assist the user to understanding what the script is doing.
There will be times that noting is changing, but the script is still working. The Running LED indicates the current run is still "active"
The Replay LED is to show the replay is being saved. If there is ever an error, the Alarm LED will turn on and the messages will be 
displayed in the Error tab. One main feature offered is the ability to evaluate any game off the replay data. For this reason the Replay
saving has the highest priority. If there is an error, you will see all 3 LED's on. This means evaluation has stopped, but the replay is
still recording. The file can be re-evaluated from the replay data.

  The "Start" button is how to start an active read. This will attempt to connect to the API (if unable, it will say so in the Error tab).
The Stop button can be used in replay reads and live reads. This will stop the current read and replay saving. Also, the evaluation will 
also save files if the API is disconnected, ie leave the lobby without doing anything. Pressing stop can cause a slight pause in functionallity 
if multi-threading is turned on (more info in settings section). You can enable an auto connect feature in the settins. This can be seen in the
screen because the running LED will be yellow.

  More information on how to load specific files and what each file is for is in the settings section.
  
### Menu
  The menu selection has six options: Save GUI, Save as GUI, load GUI, load replay, open settings, and exit.
  
#### Save GUI
  Save GUI is a quick and easy way to save the GUI file (more about what this is later). This is an easy way to save the file and will use the 
nameing scheme setup in the settins. Note: this is what is done automatically if you have save gui setup in the settings.

  Save as GUI is a way to save the gui and set a new name all in one step. Both save functions can be done any time after the evaluation is complete.
  
#### Load GUI
  Load GUI is how you use these GUI files. It will bring the GUI up to the same state that it was when it was saved. So you can view everything but the
logs. (how each person did in each round, stack results, even all the stats and main recorded speed times). You can load multiple gui files and will show 
an adverage of how each person did throughout those rounds. So would be great to see how a team preformed on adverage over a span of time.

#### Load Replay
  Load replay will allow you to select multiple replays to evaluate the rounds. Note: if you try to evaulate mutiple replays at once, they should full 
games, or at the bare minimum end after the round is over. If they do not, the script may error becuase it thinks the game jumped to an invalid state.

#### Settings
  Open Settings is where you get access to most of the variables that can be set to adjust the script. On the first run, the script will 
create a gamePlay.json. This file will have evertything that can be adjusted. You will have the file directories (the locations to where you
will save the files) The file names that will auto increment to prevent files from overwriting. 
    * Note: the "Error_log" can only be changed in the json file. This is only used for trouble shooting. 
    
  * IP address is defaulted to 127.0.0.1, the IP for local API. 
    * For quest, you will need to put your IP here. 
  * Save_replay is a boolean that controls weather or not the replay is saved. 
  * Threading is another boolean to decide if multithreading should be used on the evaluation. 
    * Note: multi threading can cause a few hicc ups's if attempting to stop the script in mid run. 
      * All execptions that I have found will be handled cleanly, but there is a chance there may be a few data points missing. 
    * Some of the calculations are very extensive. 
      * It is recommonded to use threading on live reads and not use threading on replay reads. 
      * Results will very depeding on processing power. 
        * For most accuart results on slower machines, just save the replay and run the evaluation after the game. 
  * "Replay FPS" is the frames per second used to save the replay. 
    * The default is 30, but can be adjusted for your desire. 
  * Save Detailed files are for the csv files from the games. 
    * This would include the results from the evaluation, the evaluation log, stack log, and speed log. 
    * All of these are defaulted to csv files. 
  * Save GUI file is the gui state file. 
    * It will save a file ending in GUI. 
    * This file can be loaded and you can see everthing about the game (excpet the log) in the GUI. 
    * This is a quick and easy way to review a game without rerunning the evaluation. 
      * Also, it should be noted this is the only file that doesn't have to be recorded live. 
  * Auto Restart will have the GUI automatically start evaluating as soon as you enter a lobby. 
  * "Script_delay" is only accessed in the json and adjust how fast the evaluation will run. 
    * The faster, the more accurate results. 
  * "Gui_refresh" is how fast the gui will refresh. 
    * Default is 1 sec. 
      * If turned up too high, you will see slower evaluation results. 
  * "Retry_delay" is how often you will attempt to connect to a new lobby.

### Choosing the correct settings. 
  You want to focus on how fast the script can run. If you don't use threading, some calculations can take up to 3 
seconds to complete. This is the main reason for multithreading. If you can keep the refresh rate at about 30-50ms, you should have pretty accurate
results. Faster tends to lead to some artifacts in the data calculations and slower can lead to missed data. Most replays will save at 33ms, so this is
the main reason to aim for that target. 

## About the tabs:
  If going for straight preformance, leave the gui on speed info. This tab takes this least calculation, leaving more resources for the script. The
most process hungry tab is the stats tab. You will not notice too much a difference at the default settings, but if you increase the gui refresh rate,
these are some things to keep in mind.

### Evaluation Tab:
  This tab shows the evaluation results for a spacific team (Blue, Orange, Other). Other are for players who have gone to spectate or who have left
the game. The catagories are as follows (more information in Evaluation Section)

  * Shot:           Players shot preformance
  * Possession:     Players preformance in assisting team in keeping possession
  * Poss Time:      A more accurate poss time vs the API version (showed in API)*not used in total
  * Man Coverage:   Players preformance in man defence
  * Lane Coverage:  Players preformance in blocking passing lanes
  * Change Time:    Players preformance durning possession change
  * Clear:          Players preformance on clear choice and execution
  * Stack Control:  Players preformance on using stacks
  * Stuns:          How ofter a player is stuned vs when they stun
  * Steals:         Direct relation on steals awarded by game
  * Goalie:         Players preformance in the goalie position
  * Total:          The players "Grade" or accumulation of all areas (except poss time)
      * A scaling feature will be added at a later release to put more impact on desired areas
      
### Speed Tab:
  SAOKirito and I started writing scripts on the sole perpose to be "the fastest" stack in echo. This tab shows some of the tools we created to do so.
The GUI will only show the fastest center times for each team and the fastest defense joust (provided the stack can get to the opponents nest in 2.5
seconds or less). The log will show exit times and speeds, center times and speed and offensive/defensive times and speeds. Why is a 2.5 defense time
considered "insane?" A "top tier master" stack is averaging a center time of 1.75 seconds on the opening joust (as of VRML season 3). This does not
a backward stack. So at that speed carried through, you will be getting to the deffense disc at about 2.23 seconds (I credit this time most consistantly
to SweetTooth and Choco). At the creation of the script, this was devistating to an offense and started to encourange a PE joust for offense. For comparason,
a single launcher will get to the disc in 2.44 seconds going off the ring. The "normal" pub launch (second guy from the ring) will get the disc in 1.9 seconds.
a pe joust can have the same exit velocity but cut the time to 1.5 seconds. Lastely, most stacks can drop this down to 1.19. We challenge any fast stack to push
the limits to beat Kirito and I's best. We have reached the opponents nest in 1.89 seconds (without backwards regrabbing, but all is fair game :P)

### Stack Log Tab:
  This is an extension of the evaluation tab. This gives a quick breakdown of who stacked with who, how many times they stacked together, and how much time they
spent in the game stacked together

### Evaluation Log Tab:
  This is just a gui view of the contents wrote to the CSV file for the evaluation log. Showing what each action that a player was graded for. *this is a lot
easier to view in Excel but in the GUI for a quick referance.

### Stats Tab:
  This is a fun feature for people to compare stats with their evaluation scores. This section has 3 main parts: Evaluation recap, score recap, and player stats
recap. The top row will show the list of each team and their total score in the evaluation. The players will be ranked from highest to lowest. The center of the top 
row will show a score breakdown. The current round on top and subsequential rounds are shown below. The script can show up to 8 rounds before it stops showing.
Lastely, the bottom shows all the stats the API has to offer. A lot are always zero, but may be used later on. The breakdown is shown below:

  * points->PT,
  * assists->AST,
  * goals->GOL,
  * shots taken->STK,
  * saves->SAV,
  * stuns->STN,
  * blocks->BLK
  * passes->PAS,
  * catches->CAT,
  * interceptions->INT,
  * steals->STL,
  * poss->POS
  
### Error tab:
  So a prompt to let the user know if anything went wrong or a place to see what happened in the script. If any imporant information is to be seen, the error LED
will be on.

## Streaming
  To use the evaluation information on external programming, there are two options available. By going to the settings at navigating to the streaming tab. Here you can turn streaming on to activate the process. The second option is to use API. By turning this true, you are giving the option to setup the port to access the API.
If API is turned off, you are given a field to input the directory to save the json information and the name to save the file. Both options will give the same information. Example of the infromation is given in api_json.

  Some helpful tips:
  *  Most of the "useful" information from the echo API is given
  *  blue_joust and orange_joust will turn true for about 3 seconds when the team crosses the center on nuetral joust or when a team gets an "insane defensive joust"
  *  disc.live tells when the game is actually in play
  *  disc.wait is used to count bounces
  *  disc.bounce actually works 
  *  disc.held is used to show if a person has the disc
  *  disc.by_team and disc.near_to are used to find if the player is near a person (gives players index)
  *  poss shows whish team has possession (a true possession, not just who last touched the disc)
  *  team is an array of team information (index 0 is blue and 1 is orange)
    *  team[X].stats is api team stats
    *  team[X].roundScore is an array to show the score at the end of each round
    *  team[X].team is the team name given through the API
    *  team[X].joust_time is normally 0 but is turned to the true value of the joust when the appropriate teams joust found is true
    *  team[X].joust_speed...same as joust time but for speed information
    *  team[X].clear_rating is the current clearing rating the evalutation has for each team. (scale to 0 to 1)
    *  team[X].players is an array of players for each team (note: this infrmation is duplicated in player_info)
      *  Check player_info for players stat breakdown
    *  player_info is an array of all the players that have played in the game
      *  player_info[X].name is the players name
      *  player_info[X].team gives team index (0 for blue and 1 for orange)
      *  player_info[X].speed_data is an array for speed information
        *  in each array you have joust name. This is the joust that this item is talking about (starting at joust_0) If a player has no information on a joust, there will be no item for that joust
        *  you will have velocity for exit, disc, and center. If the value is 0 than the person had no information for that field on this joust
        *  you will also have time for exit, disc, and center. Same rule as above apply
      *  player_info[X].stats this is a presistant version of the API stats
      *  player_info[X].poss turns true when this player is holding the disc
      *  player_info[X].fantasy_stats are the new stats recorded by the bot
      *  player_info[X].grade_data is the live evaluation information. at the end of the round this info is appended to rounds
      *  player_info[X].rounds is the same as grade_data but also includes round number, team that player was on and total
      *  player_info[X].rating_data is the players rating in shots and possession the bot has given this player (range from 0 to 1)
      *  player_info[X].stack_info is an array to show all the stacking information for the player
        *  name is the player the person stacked with
        *  count is the number of times the player stacked with this person
        *  time is the time they were stacked together
        
## Replay Information
  Now replay recording has been moved over to an exe file. This allows the use of multiprocessing on the computers. This is to make replay recording the highest priority in the observer process. This is because the evaluation can be reran and debugged using the replay data. This is a fully functional application without a GUI interface.
The exe can be launched with the following parameters.
  * -p, --port, -> Port to run API on... Default is 7770
  * -d, --directory, -> Directory of file, empty if in same directory
  * -f, --file, -> Name of base file... Default is replay
  * -t, --time, -> Date and time to put on the file
  * -s, --fps, -> Frames Per Second... Default is 30
  * -i, --index, -> file index number
  * -a, --address, -> IP of API
  
  using no ending on the API (127.0.0.1/) will return "This is running" if the script is running and "This is not running" if it has stopped
  *  This is pretty meaningless because the application closes after it is complete
  using /run/ will enable a way to stop the replay cleaningly (127.0.0.1/run/running=False)
  *  Putting anytihng other than "False" will not stop the relay
  using /end/ will allow the file to be broken into a new round (127.0.0.1/end/stop=True)
  *  Putting anything other than "True" will not stop the round but will return round already ended
  *  If True is sent after the replay has auto ended the round, round already ended will also be returned
  
## Deep linking
  Now Schrodinger's Observer has deep linking ability. When you enter a private match, the lobby ID will be added to lobby 1. By clicking Lobby1 after closing the game, you can rejoin said lobby. (You can also post a valid sessionID into the field and hit lobby1 to enter that valid lobby)
When you enter another private match without closing the observer, lobby1 ID will move to lobby2 ID and the new lobby will be placed into lobby 1. This will allow you to exit the game and rejoin the lobby you were in before joining the current private match by clicking lobby2 button. Lastly, 
you can spectate private matches using Spectator and can pull a specific server by using Select Region.
  * Note: Deep Linking only works for PC users.
  
## Spark Links
  Seeing popularity of spark links, we have encoded a way to use those too! A spark link is just spark:// attached to the front of the session id. Therefore, you can either copy everything after the "//" and paste it into the lobby 1 field. However, you can also paste the entire link into the
  menu item "Spark Features" -> "Use Spark". To create the link, you can just add spark:// to the start of the session ID or just click the menu item "Spark Features" -> "Create Spark".
  * Note: Using spark link only works on PC
  
## SETUP
### EXE setup
  This is the easiest. Just download the zip, unzip to any location, find the schrodingersObserver_GUI.exe and run it. Done. 
  * I would recommend saving a short cut to the exe for easier access and make sure you change the locations to where you want to save the information. The default will be in the same directory as the EXE. 
    * For example, change "Results/" to "C:\Users\XXXXXX\Documents\Eval_Results\". 
    * And do the same for the replays. 

## Evaluation Break Down
### Evaluation:
  This script is the magic to evaluating a players preformance. I will attempt to keep this file up to date on how each area is graded. The bases of the grading style
is on a scale from -1 to 1. -1 bing as bad as a punishment as you can get and 1 being the best you can do. Furture release will have a weight that can increase the impact but is easily simulated by using excel. (May push out to -2 to 2 if calculations can detect truely extroadinary acts or acts that are intentionally against their own team.

* **Shot**:
 
  Current Version has not way to decide if the player took a shot. I am currently using the API shot recognition. (In later releases, I plan to develop a more
accurate shot detection) When the API decided the player took a shot, I evaluate what happens after that.
  * -1: 
    * shot is missed and team loses possession.
  * -0.5: 
    * shot is missed but team gets the rebound.
  * +0.5: 
    * shot made on a goalie (not in a pocket),
    * shot made off the goalies head.
  * +0.5: 
    * to the person who assisted the goal.
  * +1: 
    * shot made on an open net or on a guarded net and in a pocket.
  * Note: a players "shot_rating" is saved, and recoreded but currently has no effect. Will have later version increase the punishment if the rating goes
  too low and the player keeps forcing turn overs
* **Possession**:

  Attempting to grade each players action on offence as either helping or not for the possession of the disc. Each player will have a possession rating and this
rating has to be over 70% to be considered an open pass option. (you gain 10% for every good action, up to 100% and loose 10% for every bad action, down to 0%)
  * -1:
    * Loosing disc with pass options,
    * Clearing disc with no pressure and having possession less than 1 sec,
    * Lost the disc and threw the disc slower than 16 m/s,
    * Pass to a guarded Man,
    * Failed to catch the disc,
    * Bad pass (a pass that takes 3 bounces before getting to a target or taking longer then 3 seconds to get to the target),
    * Self Goal.
  * -0.5:
    * Failed to catch an intended pass (if a player dimes a pass and you don't get it),
    * Failed to get in a passing lane (only after change time is up, and happens every pass. Also, doesn't count if you are guarded).
  * +0.5:
    * Good pass (grade of 2 -> with in 1.5 meters of players head. At there velocity when the disc is released),
    * Open for a pass (any time the disc is released),
    * Pass completed to a guarded man (to make the total points for this action -0.5. Goal will be to punish the person who gave the player the disc if it is lost
        rather than the player who lost the disc).
  * +1:
    * Diming a pass (grade = 1 -> less than one meter from players head at their current velocity when the disc is released),
    * Gained possession of the disc,
    * Rebounded shot,
    * Received a pass.
* **Poss Time**:

  API counts possession time from the moment you touch the disc until it is touched by another player. I only count it when you have "control" of the disc. For
example, when you have the disc in your hand or are floating next to the disc at a speed < 5 and within arm reach.
* **Man Coverage**:
   
  Shows how well each person is doing on defense. Goalie is scored in goalie section. Tight coverage is inside 2 meters and light is inside 4 meters
  * -1: 
    * Player's mark scores the disc.
  * -0.5: 
    * Player was not covering a man on the pass (not durning change time),
    * Player was covering the man on the pass but was not near the man when he got the disc.
  * +0.5: 
    * Player had loose man coverage.
  * +1: 
    * Player had tight man coverage.
* **Lane Coverage**:

  Points are given to this catagory if a player is blocking a passing lane between the disc and the player. Note: if multiple people are blocking the same lane
the points will go to the person closest to the receiving player. No negative points are tracked.
  * +1: Player was blocking a lane.
* **Change Time**:

  This section grades how well a team transitions to offense/defense. The default time is set to 5 seconds. This means the players are expected to return to the
side of the disc within 5 seconds of the disc changing sides. This area is stil being tweaked because there are a lot of variables that would go into play. Defense
in echo is a numbers game. Therefore if you play 4v4 vs 3v3 in the bubble, the offense actually has a better advantage. However, if there is a number favoring one
side, that side is in favor (3v4) The points are layed out below:
  * -1:
    * Player did not recover to offense/defense in time.
  * -0.5:
    * Player was stacked and did not recover to offense/defense in time,
    * Defensive player was only stuck stranded with one offensive player,
    * Player was next to a teammate who was stunning stacks.
  * +0.5:
    * Offensive player was only stuck stranded with one deffensive player.
  * +1:
    * Player return to offense/defense in time,
    * Defensive player was stunning 2 or more offensive players,
    * Offensive player was stunning 2 or more defensive players.
* **Clear**:

  This second evaluates how well a player is clearing based on where the disc goes and how well the team is doing on recovering clears. There is a team and 
individual clear rating that will help decide what choice should be made. Also, the defense zone is only up until same side double diamonds. This is to allow
for a strategic clear to trap for a recovery to beat out perma goalies and such defenses
  * -1:
    * Attempted to clear but the disc stayed in the defensive zone.
  * -0.5:
    * Cleared the disc with a team rating under 70% and plwyer was not in danger.
  * +0.5:
    * Player Cleared the disc with a team rating over 70%,
    * Picked up a clear from the other team.
  * +1.0:
    * Picked up own teams clear.
* **Stack Control**:

  This section tries to grade how well a player stacks with his/her team mates.
  * -1:
    * Stack over ran the disc.
  * -0.5: 
    * Players are in stacks in bubble defense.
  * -0.25:
    * Players are stack in bubble defense but not in the bubble.
  * +0.5:
    * Players turned as a stack,
    * Players stopped as a stck,
    * Players stacked to give high pressure to the disc.
  * +1:
    * Stack recovered the disc,
    * Players were in stack defense.
* **Stuns**:

  This section is easy.
  * -0.5:
    * getting stunned.
  * +0.5:
    * stunning an opponent.
* **Steals**:

  * +1:
    * Player stole the disc (tracked by API).
* **Goalie**:

  This section is to show how well the player is playing Goalie.
  * -1:
    * Failed to stop a 3 pointer
    * Failed to stop a shot that took longer than 0.5 seconds to go in (only if player is not stunned).
  * -0.5:
    * Scored a self goal while trying to save the disc.
  * +0.5:
    * Covered the goal durning a pass.
  * +1: 
    * API awarded a save,
    * Gain possession as a goalie.
    
## Trouble Shooting Tips
  There is a "crashLog_gamePlay.log" file that will record most errors. This is a good place to start. Also, inside the schrodingersObserver folder you can find a 
schrodingersObserver_GUI_troubleshooting.exe. This exe will have the console window open. This console will be cluttered with info from the various scripts that are running,
but it should also show any errors that the GUI might not have caught. Any bugs or fixes can be requested in the discord server. Your help and patience is greatly appreciated.
