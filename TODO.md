# NOTE
The entropy-based suggester is not optimal. It maximizes MY information gain, but not necessarily for the next player to play. Best way would be to maximize the expected information gain for the next player, given my action. This would require simulating all possible actions and their outcomes, which is more complex.

# TO DO

## rimuovi tessere con 99

## multipliers don't work in the global solver
- understand how global works and fix it

## switch solver based on entropy

## advance autoplay
- if the previous player uses a double chance, than I can extract information from that

## CHECK ALL FILTERS INDIVIDUALLY
- _apply_subset_cardinality_filter (difficult to test)
- _apply_remaining_copies_distance_filter (seems working)
- _apply_called_values_filter (not sure the logic is correct)


## TEST SWAPPING
- it works, but I don't know if the belief system and value tracker is correctly updated in all cases
- it is no longer markovian when using swapping, because the history of swaps matters

## IPAD interface

# DONE
## handle yellow cards
- it's not a problem right now, the easiest way is to add a method to specifically remove from a belief model one value  from one position. I have no idea on how to gain information from the fact that the caller has one of the yellow cards. There is not way of adding "he has x or y" to the belief model right now and no way of using that information to filter values.
- 
## called values filtering
When a player calls a value, I can use that information to further filter possible values in their wires.
special explanatory case: if for example one position is left for a player, and the player called only one of the two possible values, then I can remove the other value from that position

Find a way to generalize this logic to all cases, not only the simple one above and implement it as and additional filter in the belief model

## last filter for impossible values
- I need to implement the last filter function for this game
The idea is to limit the possible values due to two factors: remaining copies and distance
Let's say a player has ...11-11-11-11-y1-y2-y3-y4... this situation and another players has a 10
This mean that y1,y2,y3 can have a 10, but y4 cannot, since only 3 copies of 10 are left y4 cannot have 10.
Why? Because if I had for example 10 in y4,y3 and y2, no value would be possible for y1. Hence y4 cannot be a 10.
Another example: ...3-y1-y2-1... and another player has two 3, then y2 cannot be a 3, since y1 would have no possible value.
Notes: values are ordered and you must keep in mind when implementing this function to be careful to not remove values when in the set there is only 1. This should never happen if you implement it correctly but previous attempts failed in this way.

## Remove filtering for other players when doing IRL play

## Not present function
add a function to remove from the beliefs a value from a player. For example player1 announces he doesn't have a 5. Call will be (player_id, value). Implement it also in play_irl.py

## Signaling: single wire certain value
write a function to signal a certain value on a single wire, call will be (player_id, value, position)
add it to play_irl.py


## Input interface
create a class to handle input when playing with a user interface
It will be used to make calls, swaps, double reveals, signals, not present announcements and so on
I want something simple: buttons for players, postions (it would be nice to have a representation of the wires) and value called
The representation of the deck of wires will depend on the config and also the choice of the values. I want everything to be clicked, not typed
before coding it, write down how the interface will look like and how the user will interact with it

