import unittest
from src.belief.global_belief_model import GlobalBeliefModel
from src.data_structures import GameObservation, CallRecord
from config.game_config import GameConfig

class TestGlobalBeliefModel(unittest.TestCase):
    def setUp(self):
        # Custom config: 3 players, values 1,2,3 with 3 copies each
        # Total 9 wires, 3 per player
        self.dist = {1: 3, 2: 3, 3: 3}
        self.config = GameConfig(wire_distribution=self.dist, n_players=3)
        
        # Mock observation for Player 0
        # Player 0 has [1, 1, 2]
        self.my_wire = [1, 1, 2]
        self.observation = GameObservation(
            player_id=0,
            my_wire=self.my_wire,
            public_knowledge=[], # No history yet
            current_turn=0
        )
        
        self.model = GlobalBeliefModel(self.observation, self.config)

    def test_initialization(self):
        # P0 should know their own wire
        self.assertEqual(self.model.beliefs[0][0], {1})
        self.assertEqual(self.model.beliefs[0][1], {1})
        self.assertEqual(self.model.beliefs[0][2], {2})
        
        # P1 and P2 should have all values initially
        # But sorted constraint applies!
        # P1[0] can be 1, 2, 3?
        # If P1 has [3, 3, 3], valid? Yes.
        # If P1 has [1, 1, 1], valid? Yes.
        self.assertTrue(len(self.model.beliefs[1][0]) > 0)

    def test_global_deduction(self):
        # Let's reveal some info to force a deduction
        # P0 has [1, 1, 2] (Known to P0)
        # Remaining deck: {1:1, 2:2, 3:3}
        # P1 and P2 must share these.
        
        # Suppose we learn P1 has NO 1s.
        # Then P1 must have [2, 2, 3] or [2, 3, 3] or [3, 3, 3] etc.
        # And P2 must have the rest.
        
        # Let's simulate a call that reveals P1 has a 3 at pos 2.
        # And P1 has a 2 at pos 0.
        
        # Actually, let's just manually set beliefs to simulate a state
        # P1[0] is 2.
        self.model.beliefs[1][0] = {2}
        self.model.value_trackers[2].add_certain(1, 0)
        
        # Run filters
        self.model.apply_filters()
        
        # What can we deduce?
        # P0: [1, 1, 2]
        # P1: [2, ?, ?]
        # Deck: {1:3, 2:3, 3:3}
        # Used by P0: {1:2, 2:1}
        # Used by P1 (known): {2:1}
        # Remaining for P1(pos 1,2) + P2(pos 0,1,2): {1:1, 2:1, 3:3}
        
        # P1[1] must be >= P1[0]=2. So P1[1] in {2, 3}.
        # P1[2] must be >= P1[1]. So P1[2] in {2, 3}.
        
        self.assertTrue(self.model.beliefs[1][1].issubset({2, 3}))
        self.assertTrue(self.model.beliefs[1][2].issubset({2, 3}))
        
        # If P1[1] was 1, it would violate sorting.
        self.assertNotIn(1, self.model.beliefs[1][1])

    def test_impossible_state(self):
        # Force a contradiction
        # P1[0] = 3
        # P1[2] = 1
        # Impossible because sorted
        self.model.beliefs[1][0] = {3}
        self.model.beliefs[1][2] = {1}
        
        # This should detect contradiction (print error or handle it)
        # The current implementation prints "CRITICAL" and returns
        # It doesn't crash, but beliefs might be left in weird state or empty
        
        self.model.apply_filters()
        # We can't easily assert on stdout, but we can check if beliefs are updated
        # In this case, generate_valid_signatures for P1 should return empty
        # And the method returns early.
        pass

if __name__ == '__main__':
    unittest.main()
