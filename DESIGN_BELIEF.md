# Belief System Design

## Contract (short)
- Inputs: current game state, players' revealed/certain values, calls made by players.
- Outputs: per-position sets of possible values (and support structures such as called-values counters, r_k tracking) that can be used by agents/players to make decisions.
- Error modes: inconsistent game state (e.g., more revealed constants than allowed) should be detected and surfaced as warnings or exceptions by the caller.

## Markovian assumption
- The belief state depends only on the current game state and history of calls/reveals, not on the sequence of events that led to it.

## How to manage the Belief System
Summary of the user's points:
- Assign a set of possible values to each position on a wire/deck.
- The set is a single value when certain, or many values (all possible) when uncertain.
- When uncertain, a wire can have many values; when players make calls about specific values, those values should be accounted for.
- Proposed implementation idea: keep a set of ALL possible values, plus a separate data structure tracking values called by players. A filtering function applies called-values and other rules; filters are independent.
- Correct calls collapse possibilities to a single certain value for both players. Wrong calls remove a value from the called player's possibilities.


## obsolete _apply_r_k_constraint_filter
once I debug _apply_uncertain_position_value_filter I can remove _apply_r_k_constraint_filter because the other is more general and contemplates also the r_k constraint

## updated distance filter
I need to change the distance filter function because it is not correct, because it is not considering sequent values
the idea is to use a sliding window approach
for each value: mark the number of certains and revealed for that player and add the number of uncertains plus 1 if the player has called that value: that will be the size of the window
then start the sliding window across the wires, if the sliding window contains all the certain and revealed positions for that value, then all the other positions in that window can have that value too. store the possible positions for that value for that player and then remove that value from all other positions


## Ordering Filtering

Summary of the user's points:
- For each position, examine its set of possible values.
- Any position to the left cannot have values higher than the maximum of the current set.
- Any position to the right cannot have values lower than the minimum of the current set.

Assistant thoughts / caveats:
- This is a propagation of monotonic ordering constraints (useful when the wire/deck values must be sorted or constrained globally).
- The rule is valid if the wire/deck ordering enforces monotonic relations (e.g., strictly increasing along positions). If the game requires sorted wires, this is a correct global constraint.
- Implementation suggestion (design only): apply left-to-right and right-to-left passes repeatedly until no change 




## DATA STRUCTURE and CLASSES ideas
- no global data structure, we can build in the future an analysis script to aggregate beliefs and have global informataion for exploration etc.
- each player has
  -  the history: a dict of dict for each val, initialized as such 
        For tracking the possible position of the wires I thought of this data structure
          "value": {
                "total": r_k,
                "revealed": [list of players_IDs],
                "certain": [list of players_IDs],
                "called": [list of players_IDs]
                }
          where: revealed + certain + called* - r_k  = #uncertain
          if a player reveals a value, I add it to revealed, if it was certain I remove it from certain, if it was called I remove it from called
          if a value becomes certain and it was in called, I remove it from called
          when a player makes a wrong call, I add it to called only IF that values is not already in certain (meaning that value is present in a set of size>1, meaning it's still uncertain for that player)
    the lists are lists of ID of the players


  - the belief model Dict[int, Dict[int, Set[int]]] 
                    (player_ID    position   possible values)


  - these are the basic data structure, I could implement methods to have different views that can be helpful for specifc filters
  - I prefer to have a different class for the filter methods where I pass the belief models
    - NB: the belief models plus the history will have all the necessary and sufficient information 
    - this class could have an "update" function that reads all the latest belief models and history from a json. In this way I can manipulate by hand the json when necessary, and I can read and write with the BeliefModel and Filter classes
  - The call will have this structure player_i.call(player_j, position, value, success) or 
  call(player_i, player_j, position, value, success)
  - Data are also written on json files each time, and read back from it every time. Make it explicit so that I can not do it when simulating, but I want the option to intervene directly on the data when I am playing




## r_k distance filtering 
- once a value is revealed, I can also remove that value from positions that are more than r_k positions away
- the distance filtering should take into account the current number of copies uncertain, not just the r_k

## Subset cardinality matching
- I count the number of sets in which a value falls, if the number of these subsets equates the number of missing wires of that values, than I can confirm the position of all those wires with the same values (or the opposite, I start by considering the sets so I can consider more values at a time)

- ALGO IDEA: 
  - loop across all possible combinations of numbers ("1","2"...,"1,2","1,3"...,"1,2,3","1,2,4"...) tracking the cardinality of the combination (H) (full set excluded of course)
  - I look across all subsets of the merged belief decks for all the players and see if the combinations falls into exactly H subsets. 
  - if so I remove every other value from those subsets (value that belong to the complementary of the combination)
  
- This method does not consider the quantity of missing values, it's a more general strategy and I don't know if it should be integrated (guess is No)

## r_k constraint with called values
- Maintain a data structure to track total missing values across all players (i.e., how many instances of each value remain unaccounted for). DONE, it's ValueTracker
- It interfaces with both certain values and called ones.
- Example: if 3 "4" are certain, and another "4" has been called (but not revealed), then all "4"s are accounted and you can remove "4" from other players' possible sets and focus tracking on the player who called it.
- Hence this is a sort of player filtering, it doesn't inform you on position but excludes players

- ALGO IDEA: I assign the player ID (based on calls) for every uncertain remaining value, if none remains unnamed than i can filter the other players out for that value

- I have to be careful, if a value that has been called by a player becomes certain, it needs to be moved from called to certain. The opposite is not true: if a player that already has that value revealed calls for that value, I can add it to the called ones, so I can have this

Assistant thoughts / suggestions:
- This is effectively a global inventory/availability counter: for each value v, track how many instances exist in the deck (total), how many are certain/revealed, how many are claimed/called, and therefore how many remain unknown and where they might be.



## call suggester (easy)
- a function that suggests the best call to make based on the current belief model

- easy way: filter calls for values that are still covered that the player making the call has, then look in the belief system what are certain calls that he can make with certainty, if none, the one with the least amount 

## loop across filters until change = False
- track how many times it was needed, intersting info

## better playability when playing irl (easy)
- add names to players and an easier system for position (subtract 1 automatically) (easy)
When playing IRL I don't want to make the calls by counting from 0, it is easier to count from 1
also I would like to add a name to the players, so I don't get confused with the ID
Refactor the code in play_irl by moving most of the code in utilss and leaving a cleaner and shorter script in the play_irl script



## automatically disabling call validation when playing irl
- otherwise the random values create inconsistencies
- add a flag in the config to inform that I am playing IRL, when activated the constraint for calling only if the player only if it posesses that wire, the check can be found in _validate_call in the game script (now commented)

## double reveals 
- when a player reveals two wires at once whitout a call 
- they need to be revealed the other 2, for simulating games. manual is okay for irl
add a function to perform a new action, double reveal. If a player posesses the last 2 wires of the same value (the other were already revealed) then it can choose to reveal them at once
when playing IRL avoid the validation that they are in fact the last 2
the function call will have this aspect (Player_ID, value, pos1, pos2)
Players will then update their belief models and value tracker


## switching wires between players problem (hard, but important in specific cases)
add a function that enables two players to switch wires. The wires get placed in the correct place, maintaning the sorting
the swap function will have this aspect (player_ID1, player_ID2, init_pos1, init_pos2, final_pos1, final_pos2)
init_pos are the position of the chosen wires to be swapped, final_pos is where they get placed
the wire in init_pos1 ends un in final_pos1, same for 2
The player that make the exchange will obviusly know which value they receive, since they can see it, hence it will become certain
The other players will update their belief system by swapping the belief of the wires, and then applying the filter loop to make it consistent with the new placement in the players' decks
Keep in mind the ordering, I don't know how it can be handled since I am using a dictionary, but it needs to update all positions
in IRL I need to specify which value I am receiving when I am the player that is receiving the wire

## better differentiation certain vs revealed (easy)
- in the print function, and in the data structure

## stats class
It tracks uncertainty in the belief system, like how much entropy there is for each player
Write in a markdown the math to how you would calculate the entropy or similar measures
I want the implementation of the suggester to be moved in this class from #file:player.py , with a function for the print too so that it can be removed from the utils

For now keep it real simple, I'll add more statistics and suggesters later

# TO DO

## DEBUG value tracker update on swap (hard)

## swap extra info
- if I receive a wire, not only I know its value but also it's past position, this can be extra information for filtering, very hard to implement
- what I need is a backward tracking of some sort, think about it
- Thinking more about it, I am not sure is needed.


## CHECK ALL FILTERS INDIVIDUALLY
- _apply_subset_cardinality_filter (difficult to test)
- _apply_uncertain_position_value_filter (seems okay but needs more testing)


# Future Ideass

## bombs cannot be signaled
- I would need to add the signaling method, and remove the bomb possibility (not int values, or just .5) from the belief in those positions

## check markovian assumption
then in case calls, swaps, double reveals in order

## no one keeps 4 wires filter 
- very difficult to implement, but the idea is to reduce the possibility that 4 copies of a wire belong to the same player, this changes a lot of filters
### drop 4 function

## multipliers (easy and hard, future implementation)
- I don't know which they are targeting, if as meta I always choose the left one than it works fine
- actually not so easy to make it extra informative, I can just equate the belief system, but this put some extra usefull constraints that are not contemplated by the filtering functions
- also equal and different signals (extra)
- could it just be that I take the one signaled, "promote" it to king, and set the other around (or on the left if meta) as equal in the belief system. But then I still need to account for other stuff too

## advanced call suggester (hard)

## simulation function (hard)
- a very advance system that explores possible combination to see if they can be acceptable
  - this could be an intersting way to check the completness of my approach, if I find that some values end up in impossible games than that means that a filtering function can be implemented


# Notes
- some cases could be filtered further, not because they are special case but because they would fall on unresonable strategy
 - for example if a player has 4 copies it would drop all of them
   - if a player has 3 certain, it cannot be that it has the fourth too
 - it would be nice in the future to understand this cases broadly and refine the filtering accordingly, but it requires testing and trying

## swapping is extra hard in automatic mode
- I need to pass the final position, but it needs to be called by the player receiving the wire and has to be consistent with the ordering