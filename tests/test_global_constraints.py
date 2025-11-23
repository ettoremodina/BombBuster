import unittest
from src.belief.global_belief_model import GlobalBeliefModel
from src.data_structures import GameObservation, SignalCopyCountRecord, SignalAdjacentRecord
from config.game_config import GameConfig

class TestGlobalConstraints(unittest.TestCase):
    def setUp(self):
        pass

    def test_copy_count_constraint(self):
        # Config: Values {1: 2, 2: 3}. Total 5 cards.
        # 2 players, 2 wires each.
        dist = {1: 2, 2: 3}
        config = GameConfig(wire_distribution=dist, n_players=2, wires_per_player=2)
        
        # P0 has [1, 2].
        # Remaining for P1: {1: 1, 2: 2}.
        # Possible P1 hands: [1, 2], [2, 2].
        # ([1, 1] impossible as only 1 '1' left)
        
        observation = GameObservation(
            player_id=0,
            my_wire=[1, 2],
            public_knowledge=[],
            current_turn=0
        )
        
        model = GlobalBeliefModel(observation, config)
        model.apply_filters()
        
        # Initially, P1 pos 0 can be 1 or 2.
        # [1, 2] -> pos 0 is 1
        # [2, 2] -> pos 0 is 2
        self.assertTrue(1 in model.beliefs[1][0])
        self.assertTrue(2 in model.beliefs[1][0])
        
        # Apply constraint: P1 pos 0 has copy count 2.
        # Value 1 has 2 copies. Value 2 has 3 copies.
        # So P1 pos 0 MUST be 1.
        signal = SignalCopyCountRecord(player_id=1, position=0, copy_count=2)
        model.process_copy_count_signal(signal)
        
        # Check beliefs
        print(f"P1 Pos 0 Beliefs: {model.beliefs[1][0]}")
        self.assertEqual(model.beliefs[1][0], {1})
        
        # Since P1 pos 0 is 1, and hand is sorted, P1 hand must be [1, 2] (since [1, 1] impossible).
        # So P1 pos 1 must be 2.
        self.assertEqual(model.beliefs[1][1], {2})

    def test_adjacent_equal_constraint(self):
        # Config: Values {1: 4, 2: 4}.
        # 2 players, 2 wires each.
        dist = {1: 4, 2: 4}
        config = GameConfig(wire_distribution=dist, n_players=2, wires_per_player=2)
        
        # P0 has [1, 2].
        # Remaining: {1: 3, 2: 3}.
        # Possible P1 hands: [1, 1], [1, 2], [2, 2].
        
        observation = GameObservation(
            player_id=0,
            my_wire=[1, 2],
            public_knowledge=[],
            current_turn=0
        )
        
        model = GlobalBeliefModel(observation, config)
        model.apply_filters()
        
        # Apply constraint: P1 pos 0 == P1 pos 1
        # Valid hands: [1, 1], [2, 2].
        # Invalid: [1, 2].
        signal = SignalAdjacentRecord(player_id=1, position1=0, position2=1, is_equal=True)
        model.process_adjacent_signal(signal)
        
        # Now, if we eliminate 1 from pos 0, pos 1 should also lose 1.
        # Let's artificially remove 1 from pos 0.
        model.beliefs[1][0].discard(1)
        model.apply_filters()
        
        print(f"P1 Pos 1 Beliefs: {model.beliefs[1][1]}")
        self.assertEqual(model.beliefs[1][1], {2})

    def test_adjacent_different_constraint(self):
        # Config: Values {1: 4, 2: 4}.
        # 2 players, 2 wires each.
        dist = {1: 4, 2: 4}
        config = GameConfig(wire_distribution=dist, n_players=2, wires_per_player=2)
        
        # P0 has [1, 2].
        # Remaining: {1: 3, 2: 3}.
        # Possible P1 hands: [1, 1], [1, 2], [2, 2].
        
        observation = GameObservation(
            player_id=0,
            my_wire=[1, 2],
            public_knowledge=[],
            current_turn=0
        )
        
        model = GlobalBeliefModel(observation, config)
        model.apply_filters()
        
        # Apply constraint: P1 pos 0 != P1 pos 1
        # Valid hands: [1, 2].
        # Invalid: [1, 1], [2, 2].
        signal = SignalAdjacentRecord(player_id=1, position1=0, position2=1, is_equal=False)
        model.process_adjacent_signal(signal)
        
        # P1 hand MUST be [1, 2].
        self.assertEqual(model.beliefs[1][0], {1})
        self.assertEqual(model.beliefs[1][1], {2})

if __name__ == '__main__':
    unittest.main()
