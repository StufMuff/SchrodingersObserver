import mysql.connector
import mariadb
import pandas as pd
import pdb

mydb = mysql.connector.connect(
    host = "Your_Host",
    user="Username",
    password="password",
    database="database")
#    port=3306)

creat_tables = False
update_players = False
update_roster = False
testing = False

mycursor = mydb.cursor()
  
if creat_tables:

  # have to add foriegn key after creation
  sql = """
        CREATE TABLE IF NOT EXISTS people (
          ID int NOT NULL PRIMARY KEY AUTO_INCREMENT,
          first_name VARCHAR(15),
          last_name VARCHAR(15),
          oculus_name VARCHAR(30) UNIQUE,
          number int,
          contact_info VARCHAR(40),
          teamID int,
          league VARCHAR(3),
          discord VARCHAR(30)
        );
    """
  mycursor.execute(sql)

  mydb.commit()

  ## need a team for none -> team index of 1
  sql = """
        CREATE TABLE IF NOT EXISTS teams (
          ID int NOT NULL PRIMARY KEY AUTO_INCREMENT,
          name VARCHAR(30) NOT NULL,
          ownerID int,
          captainID int,
          roster1ID int,
          roster2ID int,
          roster3ID int,
          roster4ID int,
          roster5ID int,
          city varchar(20),
          league VARCHAR(3),
          FOREIGN KEY (ownerID) REFERENCES people(ID),
          FOREIGN KEY (captainID) REFERENCES people(ID),
          FOREIGN KEY (roster1ID) REFERENCES people(ID),
          FOREIGN KEY (roster2ID) REFERENCES people(ID),
          FOREIGN KEY (roster3ID) REFERENCES people(ID),
          FOREIGN KEY (roster4ID) REFERENCES people(ID),
          FOREIGN KEY (roster5ID) REFERENCES people(ID)
        );
    """
  mycursor.execute(sql)

  mydb.commit()
  
  # add not team if not in table
  sql = """
        INSERT INTO `teams` (name) VALUES ('No Team');
    """
  mycursor.execute(sql)
  mydb.commit()
  
  ##Alter people to have foreign key on teamID
  sql = """
        ALTER TABLE people 
        ADD FOREIGN KEY (`teamID`) REFERENCES `teams` (`ID`);
    """
  mycursor.execute(sql)

  mydb.commit()
  
  ## ALTER TABLE player_stats ADD UNIQUE KEY `single_game` (`date`,`playerID`);
  sql = """
        CREATE TABLE IF NOT EXISTS player_stats (
          ID int NOT NULL PRIMARY KEY AUTO_INCREMENT,
          date timestamp DEFAULT CURRENT_TIMESTAMP,
          teamID int,
          playerID int NOT NULL,
          stackID int,
          passes int NOT NULL,
          assist_bubble int NOT NULL,
          assist_3 int NOT NULL,
          assist_assist int NOT NULL,
          interceptions int NOT NULL,
          catches int NOT NULL,
          saves int NOT NULL,
          steals int NOT NULL,
          stuns int NOT NULL,
          blocks int NOT NULL,
          stk int NOT NULL,
          goal_7m int NOT NULL,
          goal_20m int NOT NULL,
          goal_40m int NOT NULL,
          goal_40up int NOT NULL,
          ping INT NOT NULL,
          shot_eval float NOT NULL,
          poss_eval float NOT NULL,
          possession float NOT NULL,
          man_eval float NOT NULL,
          lane_eval float NOT NULL,
          change_eval float NOT NULL,
          clear_eval float NOT NULL,
          stack_eval float NOT NULL,
          stuns_eval float NOT NULL,
          steal_eval float NOT NULL,
          goalie_eval float NOT NULL,
          mvp bool NOT NULL,
          location varchar(20) NOT NULL,
          serverIP varchar(20) NOT NULL,
          stack_count int,
          stack_time float,
          FOREIGN KEY (teamID) REFERENCES teams(ID),
          FOREIGN KEY (playerID) REFERENCES people(ID),
          FOREIGN KEY (stackID) REFERENCES people(ID),
          CONSTRAINT `single_game` UNIQUE (`date`,`playerID`)
        );
    """
  mycursor.execute(sql)

  mydb.commit()
  
  sql = """
      CREATE TABLE IF NOT EXISTS team_stats (
        ID int NOT NULL PRIMARY KEY AUTO_INCREMENT,
        date timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
        teamID int NOT NULL,
        side varchar(6) NOT NULL,
        points int NOT NULL,
        goal_dif int NOT NULL,
        joust_won int,
        joust_loss int,
        won bool,
        location varchar(20) NOT NULL,
        server_IP varchar(20) NOT NULL,
        FOREIGN KEY (teamID) REFERENCES teams(ID),
        CONSTRAINT `single_game_team` UNIQUE (`date`,`teamID`, `side`)
      );
  """
  mycursor.execute(sql)

  mydb.commit()

## select from
#mycursor.execute("SELECT * FROM people")
#
#myresult = mycursor.fetchall()
#
#for x in myresult:
#  print(x)
#  

# sql for table
#CREATE TABLE IF NOT EXISTS Orders (
#    ID int NOT NULL PRIMARY KEY AUTO_INCREMENT,
#    OrderNumber int NOT NULL,
#    PersonID int FOREIGN KEY REFERENCES Persons(PersonID)
#);
## insert
#mycursor = mydb.cursor()
#
#sql = "INSERT INTO customers (name, address) VALUES (%s, %s)"
#val = ("Michelle", "Blue Village")
#mycursor.execute(sql, val)
#
#mydb.commit()
#
#print("1 record inserted, ID:", mycursor.lastrowid)

if update_players:
  team_df = pd.read_csv("../NEPA_INFO/team_example.csv")
  player_df = pd.read_csv("../NEPA_INFO/player_example.csv")
  
  # matching the column name with database
  team_df.columns = ['name', 'owner', 'captain', 'city', 'league']
  player_df.columns = ['first_name', 'last_name', 'oculus_name', 'number', 'contact_info', 'team', 'discord', 'league', 'affiliate']
  # remove unneeded columns
  player_df = player_df.drop(['first_name', 'last_name', 'contact_info', 'affiliate'], axis=1)
  
  cur_team = pd.read_sql("select * from teams", mydb)
  cur_player = pd.read_sql("select * from people", mydb)
  
  # remove data that is already in
  players_needed = pd.merge(player_df, cur_player['oculus_name'], on="oculus_name", indicator=True, how='outer').query('_merge=="left_only"').drop('_merge', axis=1)
  teams_needed = pd.merge(team_df, cur_team['name'], on="name", indicator=True, how='outer').query('_merge=="left_only"').drop('_merge', axis=1)
  
  sql_df = players_needed.drop(['team'],axis=1).fillna('')
  
  ## adding players
  # creating column list for insertion
  cols = "`,`".join([str(i) for i in sql_df.columns.tolist()])
  cols1 = "`,`".join([str(i) for i in sql_df.columns.tolist() if i != 'number'])

  # Insert DataFrame recrds one by one.
  for i,row in sql_df.iterrows():
    if row['number']:
      sql = "INSERT INTO `people` (`" +cols + "`) VALUES (" + "%s,"*(len(row)-1) + "%s)"
      mycursor.execute(sql, tuple(row))
    else:
      row = row.drop(['number'])
      sql = "INSERT INTO `people` (`" +cols1 + "`) VALUES (" + "%s,"*(len(row)-1) + "%s)"
      mycursor.execute(sql, tuple(row))
    mydb.commit()
  
  ## adding teams
  cur_player = pd.read_sql("select * from people", mydb)
  teams_needed = teams_needed.fillna('')
  # not adding coaches or teams dynamically
#  coach = cur_player[cur_player['oculus_name'] == sql_df['coach']]
#  assist = cur_player[cur_player['oculus_name'] == sql_df['assistant']]
#  if coach:
#    sql_df['coachID'] = coach['ID']
#  if assist:
#    sql_df['assist_coachID'] = assist['ID']
    
  sql_df = teams_needed.drop(['owner','captain'], axis=1)
  # creating column list for insertion
  cols = "`,`".join([str(i) for i in sql_df.columns.tolist()])

  # Insert DataFrame recrds one by one.
  for i,row in sql_df.iterrows():
    sql = "INSERT INTO `teams` (`" +cols + "`) VALUES (" + "%s,"*(len(row)-1) + "%s)"
    mycursor.execute(sql, tuple(row))
    mydb.commit()
    
  ## insert into database
  #df.to_sql('table', con=mydb, if_exists='append')
  
if update_roster:
  team_df = pd.read_csv("../NEPA_INFO/team_example.csv")
  player_df = pd.read_csv("../NEPA_INFO/player_example.csv")
  
  # matching the column name with database
  team_df.columns = ['name', 'owner', 'captain', 'city', 'league']
  player_df.columns = ['first_name', 'last_name', 'oculus_name', 'number', 'contact_info', 'team', 'discord', 'league', 'affiliate']
  # remove unneeded columns
  player_df = player_df.drop(['first_name', 'last_name', 'contact_info'], axis=1)
  cur_team = pd.read_sql("select * from teams", mydb)
  cur_team["full_name"] = cur_team['city'] + " " + cur_team['name']
  team_df["full_name"] = team_df['city'] + " " + team_df['name']
  cur_player = pd.read_sql("select * from people", mydb)
  
  # get ID of team for player
  full_df = pd.merge(player_df[['oculus_name','team','league']], cur_team[['ID','full_name']], left_on='team', right_on='full_name', how='inner')
  full_df = full_df.rename(columns={'ID':'teamID'})
#  full1_df = pd.merge(player_df[['oculus_name','affiliate','league']], cur_team[['ID','full_name']], left_on='affiliate', right_on='full_name', how='inner')
#  full1_df = full1_df.rename(columns={'ID':'teamID', 'affiliate':'team'})
#  full_df = pd.concat([full_df, full1_df])
  full_df = pd.merge(cur_player[['oculus_name','ID']], full_df[['oculus_name','team','teamID','league']], on='oculus_name', how='inner')
  
  # get ID for coach and owner
  full_team = pd.merge(team_df[['owner','captain','name']], cur_team[['ID','name']], on='name', how='inner')
  full_team = full_team.rename(columns={'ID':"teamID"})
  full_team = pd.merge(full_team, cur_player[['ID','oculus_name']], left_on='captain', right_on='oculus_name', how='inner')
  full_team = full_team.rename(columns={'ID':"captainID"})
  
  team_roster = {}
  # Update records one by one.
  for i,row in full_df.iterrows():
    sql = f"""
      UPDATE `people` 
      SET 
        teamID = {row['teamID']}
      WHERE
        ID = {row['ID']};
    """
    mycursor.execute(sql)
    mydb.commit()
    
    if str(row['teamID']) not in team_roster:
      team_roster[str(row['teamID'])] = [row['ID']]
    else:
      team_roster[str(row['teamID'])].append(row['ID'])
        
  # adding starting roster
  for key,value in team_roster.items():
    sql_add = ""
    for index,val in enumerate(value):
        sql_add = sql_add + f",roster{index+1}ID = {val}"

    if len(full_team[full_team['teamID'] == int(key)]['captainID']):
      sql = f"""
        UPDATE `teams`
        SET 
          captainID = {full_team[full_team['teamID'] == int(key)]['captainID'].iat[0]}
          {sql_add}
        WHERE
          ID = {key}
      """
    else:
      sql_add = sql_add[1:]
      sql = f"""
        UPDATE `teams`
        SET 
          {sql_add}
        WHERE
          ID = {key}
      """
    mycursor.execute(sql)
    mydb.commit()

if testing:
#  # add team stat information Note: date is enter automatically
#  sql = """
#        INSERT INTO `team_stats` (`won`, `points`, `goal_dif`) 
#        VALUES (%s,%s,%s)
#  """
#  
#  mycursor.execute(sql, (True, 20, 10))
#  mydb.commit()
#  
#  mycursor.execute(sql, (False, 10,10))
#  mydb.commit()

  # add player stat information
  
  # this builds stats table
  sql = """
          SELECT ps.date, pi.oculus_name, ti.name as team_name, ts.points as results, 
                 CASE WHEN ts.won THEN 'WON' ELSE 'LOSS' END as outcome,
                 ps.passes, ps.assist_bubble, ps.assist_3, ps.assist_assist, ps.interceptions, ps.catches, 
                 ps.saves, ps.steals, ps.stuns, ps.blocks, ps.stk, ps.goal_7m, ps.goal_20m, ps.goal_40m,
                 ps.goal_40up, ps.shot_eval, ps.poss_eval, ps.possession, ps.man_eval,
                 ps.lane_eval, ps.change_eval, ps.clear_eval, ps.stack_eval, ps.stuns_eval,
                 ps.goalie_eval, ps.mvp
         FROM player_stats as ps
         JOIN people as pi ON ps.playerID = pi.ID
         JOIN teams as ti ON ps.teamID = ti.ID
         JOIN team_stats as ts on ps.teamID = ts.teamID AND ps.date = ts.date
  """
  
  # this builds ping table
  sql = """
          SELECT ps.date, pi.oculus_name, ti.name as team_name, 
                 ps.ping
         FROM player_stats as ps
         JOIN people as pi ON ps.playerID = pi.ID
         JOIN teams as ti ON ps.teamID = ti.ID
  """
  
  # final score -> Results
  # Outcome -> Win/Loss
#  current_game = pd.read_sql("select date from team_stats ORDER BY date DESC", mydb).head(1)
#  mycursor.execute(sql, (current_game.iat[0,0], 8, 0, 0, 0,
#                         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
#                         0, 0, 0, 0, 0, 0, 0, 0, 0, True))
#  mydb.commit()
  
## value at cell
#df.iat[0,0]
#df.at[0,"name"]
#df.at["name"].values[0]
pdb.set_trace()
  
mydb.close()