# TO DO

## CHECK ALL FILTERS INDIVIDUALLY
- _apply_subset_cardinality_filter (difficult to test)
- _apply_uncertain_position_value_filter: debug, la logica va ripensata, non deve contare i revealed e deve saltare le celle certain e revealed

## TEST SWAPPING
- it works, but I don't know if the belief system and value tracker is correctly updated in all cases
- it is no longer markovian when using swapping, because the history of swaps matters


# DONE

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

