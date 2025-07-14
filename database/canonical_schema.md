Category

Canonical_Column_Name

Data_Type

Description

General

player_id

INTEGER

Unique identifier for the player as assigned by StatsBomb.

General

player_name

STRING

Full name of the player.

General

team_id

INTEGER

Unique identifier for the player's team.

General

team_name

STRING

Name of the player's team.

General

match_id

INTEGER

Unique identifier for the match.

General

competition_id

INTEGER

Unique identifier for the competition.

General

season_id

INTEGER

Unique identifier for the season.

General

minutes_played

INTEGER

Total minutes the player participated in the match.

General

starting_position

STRING

The player's primary starting position in the match lineup.

General

is_starter

BOOLEAN

A boolean flag indicating if the player was in the starting lineup.

Shooting

shots

INTEGER

Total number of shots taken by the player.

Shooting

shots_p90

FLOAT

Total number of shots taken by the player, normalized per 90 minutes.

Shooting

shots_on_target

INTEGER

Total number of shots that were on target.

Shooting

shots_on_target_p90

FLOAT

Total number of shots on target, normalized per 90 minutes.

Shooting

shot_accuracy_pct

FLOAT

The percentage of shots that were on target. Calculated as (shots_on_target / shots) * 100.

Shooting

goals

INTEGER

Total number of goals scored by the player.

Shooting

goals_p90

FLOAT

Total goals scored by the player, normalized per 90 minutes.

Shooting

avg_shot_distance

FLOAT

The average distance from the center of the goal (in yards) for all shots taken, calculated from shot event location data.

Shooting

non_penalty_goals

INTEGER

Total goals scored, excluding penalties.

Shooting

non_penalty_goals_p90

FLOAT

Total non-penalty goals scored, normalized per 90 minutes.

Shooting

penalty_goals

INTEGER

Total goals scored from penalty kicks.

Shooting

xg_total

FLOAT

Total Expected Goals. Sum of the xG value of all shots taken by the player.

Shooting

xg_total_p90

FLOAT

Total Expected Goals, normalized per 90 minutes.

Shooting

npxg_total

FLOAT

Non-Penalty Expected Goals. Sum of the xG value of all non-penalty shots taken.

Shooting

npxg_total_p90

FLOAT

Non-Penalty Expected Goals, normalized per 90 minutes.

Shooting

xg_per_shot

FLOAT

Average Expected Goals value per shot. Calculated as xg_total / shots.

Shooting

goals_minus_xg

FLOAT

Goals scored minus total Expected Goals. Measures finishing ability over expectation.

Shooting

shots_from_open_play

INTEGER

Total number of shots taken during open play.

Shooting

shots_from_set_piece

INTEGER

Total number of shots taken from a set piece situation (e.g., free kick, corner).

Shooting

shots_first_time

INTEGER

Number of shots taken with the first touch.

Passing

passes_attempted

INTEGER

Total number of passes attempted by the player.

Passing

passes_attempted_p90

FLOAT

Total number of passes attempted, normalized per 90 minutes.

Passing

passes_completed

INTEGER

Total number of successful passes completed by the player.

Passing

pass_completion_pct

FLOAT

The percentage of attempted passes that were successful. Calculated as (passes_completed / passes_attempted) * 100.

Passing

pass_distance_total

FLOAT

The total length (in yards) of all completed passes.

Passing

pass_distance_progressive

FLOAT

The total length (in yards) of all completed progressive passes.

Passing

forward_pass_pct

FLOAT

Percentage of completed passes that were played forward (angle between -π/2 and π/2).

Passing

key_passes

INTEGER

Passes that directly lead to a shot.

Passing

key_passes_p90

FLOAT

Passes that directly lead to a shot, normalized per 90 minutes.

Passing

assists

INTEGER

Passes that directly lead to a goal.

Passing

assists_p90

FLOAT

Passes that directly lead to a goal, normalized per 90 minutes.

Passing

xa_total

FLOAT

Expected Assists. The sum of the xG value of shots that were assisted by the player's key passes.

Passing

xa_total_p90

FLOAT

Total Expected Assists, normalized per 90 minutes.

Passing

assists_minus_xa

FLOAT

Assists minus Expected Assists. Measures the quality of chances created versus the finishing of teammates.

Passing

progressive_passes

INTEGER

Completed passes that move the ball at least 10 yards closer to the opponent's goal, or any pass into the penalty area. Excludes passes from the defensive 40% of the pitch.

Passing

progressive_passes_p90

FLOAT

Total progressive passes, normalized per 90 minutes.

Passing

passes_into_final_third

INTEGER

Completed passes that end in the attacking third of the pitch.

Passing

passes_into_penalty_area

INTEGER

Completed passes that end inside the opponent's penalty area.

Passing

crosses_attempted

INTEGER

Number of passes attempted from a wide position into the penalty area.

Passing

crosses_completed

INTEGER

Number of successful crosses.

Passing

cross_completion_pct

FLOAT

The percentage of attempted crosses that were successful.

Passing

through_balls

INTEGER

Completed passes sent between defenders into open space for a teammate to run onto.

Passing

switches_of_play

INTEGER

Passes that travel more than 40 yards of the horizontal width of the pitch.

Ball Progression

carries

INTEGER

Number of times a player controlled the ball with their feet.

Ball Progression

carry_distance_total

FLOAT

Total distance (in yards) a player moved the ball with their feet.

Ball Progression

carry_distance_progressive

FLOAT

Total distance (in yards) a player moved the ball towards the opponent's goal.

Ball Progression

progressive_carries

INTEGER

Carries that move the ball at least 5 yards into the opponent's half or any carry into the penalty area.

Ball Progression

progressive_carries_p90

FLOAT

Total progressive carries, normalized per 90 minutes.

Ball Progression

carries_into_final_third

INTEGER

Carries that end in the attacking third of the pitch.

Ball Progression

carries_into_penalty_area

INTEGER

Carries that end inside the opponent's penalty area.

Possession

dribbles_attempted

INTEGER

Number of times a player attempted to take on an opponent.

Possession

dribbles_completed

INTEGER

Number of times a player successfully dribbled past an opponent.

Possession

dribble_success_pct

FLOAT

The percentage of attempted dribbles that were successful.

Possession

nutmegs

INTEGER

Number of times a player successfully played the ball through an opponent's legs.

Possession

miscontrols

INTEGER

Number of times a player failed to control the ball.

Possession

dispossessed

INTEGER

Number of times a player was tackled and lost possession of the ball.

Possession

ball_recoveries

INTEGER

Number of times a player recovered a loose ball.

Possession

turnovers

INTEGER

Total number of times a player lost possession through miscontrols and being dispossessed.

Defensive Actions

tackles_won

INTEGER

Number of times a player successfully tackled an opponent to win the ball.

Defensive Actions

tackles_won_p90

FLOAT

Number of successful tackles, normalized per 90 minutes.

Defensive Actions

interceptions

INTEGER

Number of times a player intercepted a pass.

Defensive Actions

interceptions_p90

FLOAT

Number of interceptions, normalized per 90 minutes.

Defensive Actions

clearances

INTEGER

Number of times a player kicked the ball away from their own goal under pressure.

Defensive Actions

blocks

INTEGER

Number of times a player blocked a pass or a shot.

Defensive Actions

blocked_shots

INTEGER

Number of times a player blocked a shot.

Defensive Actions

defensive_actions

INTEGER

A combined metric of tackles won, interceptions, clearances, and blocks.

Defensive Actions

aerial_duels_won

INTEGER

Number of aerial duels won.

Defensive Actions

aerial_duels_lost

INTEGER

Number of aerial duels lost.

Defensive Actions

aerial_duel_win_pct

FLOAT

The percentage of aerial duels won.

Pressing

pressures

INTEGER

Total number of times a player applied pressure to an opposing player who is receiving, carrying, or releasing the ball.

Pressing

pressures_p90

FLOAT

Total pressures, normalized per 90 minutes.

Pressing

pressure_regains

INTEGER

Number of times the player's team regained possession within 5 seconds of the player applying pressure.

Pressing

pressure_regain_pct

FLOAT

Percentage of pressures that resulted in the team regaining possession within 5 seconds.

Pressing

pressures_in_def_third

INTEGER

Pressures applied in the defensive third of the pitch.

Pressing

pressures_in_mid_third

INTEGER

Pressures applied in the middle third of the pitch.

Pressing

pressures_in_att_third

INTEGER

Pressures applied in the attacking third of the pitch.

Discipline

fouls_committed

INTEGER

Number of fouls committed by the player.

Discipline

fouls_won

INTEGER

Number of times the player was fouled by an opponent.

Discipline

yellow_cards

INTEGER

Number of yellow cards received.

Discipline

red_cards

INTEGER

Number of red cards received.

Goalkeeping

gk_shots_faced

INTEGER

Total number of shots on target faced by the goalkeeper.

Goalkeeping

gk_goals_conceded

INTEGER

Total number of goals conceded by the goalkeeper.

Goalkeeping

gk_saves

INTEGER

Total number of saves made by the goalkeeper.

Goalkeeping

gk_save_pct

FLOAT

Percentage of shots on target saved. Calculated as (gk_saves / gk_shots_faced) * 100.

Goalkeeping

gk_psxg_total

FLOAT

Post-Shot Expected Goals. The xG value of shots on target faced, indicating the quality of shots.

Goalkeeping

gk_goals_prevented

FLOAT

Calculated as gk_psxg_total - gk_goals_conceded. Measures a goalkeeper's shot-stopping ability above average.

Goalkeeping

gk_crosses_claimed

INTEGER

Number of crosses the goalkeeper successfully caught or punched.

Goalkeeping

gk_passes_launched

INTEGER

Number of passes by the goalkeeper that traveled over 40 yards.

Goalkeeping

gk_pass_launch_completion_pct

FLOAT

The completion percentage of passes launched over 40 yards.