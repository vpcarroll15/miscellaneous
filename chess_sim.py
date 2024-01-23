import asyncio
from enum import Enum, auto
import itertools
import random


class PossibleActions(Enum):
  MAKE_MOVE = auto()
  RESIGN = auto()
  GRANDMASTER_ARRIVES = auto()


async def chess_player(index: int, out_channel: asyncio.Queue, in_channel: asyncio.Queue):
  """
  Chess players in the exhibition have the following behavior:

  1) They think until they come up with a move after a random amount of time or until the grandmaster
  shows up and is ready for them. At that point, they're forced to move.
  2) On each turn, they have a random probability of resigning.
  3) If the grandmaster shows up and they're not ready, they have a higher probability of resigning.

  All the players have the White pieces and move first.
  """
  for i in itertools.count(start=1):
    print(f"Player #{index} considering move #{i}.")
    move_duration = random.randint(5, 15)
  
    # Wait until either the player is done thinking or the grandmaster shows up.
    thinking_task = asyncio.create_task(asyncio.sleep(move_duration))
    grandmaster_arrives_task = asyncio.create_task(in_channel.get())
    completed, pending = await asyncio.wait([thinking_task, grandmaster_arrives_task], return_when=asyncio.FIRST_COMPLETED)

    # Cancel the task that is pending.
    for task in pending:
      task.cancel()

    # Determine if we are going to resign.
    finished_thinking = thinking_task in completed
    probability_of_resigning = 0.05 if finished_thinking else 0.1
    has_resigned = random.random() < probability_of_resigning

    if finished_thinking:
      print(f"Player #{index} making move #{i} after finishing thinking. Now waiting for grandmaster.")
    else:
      print(f"Player #{index} making move #{i} because grandmaster has shown up.")

    if has_resigned:
      print(f"Player #{index} resigns on move #{i}.")
      await out_channel.put(PossibleActions.RESIGN)
      break
    # The player makes a move.
    await out_channel.put(PossibleActions.MAKE_MOVE)
    
    # Now the grandmaster is here and we've made our move. The last step is to wait for the grandmaster
    # to make a move or resign.
    while True:
      grandmaster_move = await in_channel.get()
      match grandmaster_move:
        case PossibleActions.RESIGN:
          print(f"The grandmaster has resigned on move {i}.")
          return
        case PossibleActions.MAKE_MOVE:
          break
        case PossibleActions.GRANDMASTER_ARRIVES:
          pass
    

async def grandmaster(in_and_out_channel_pairs: list[tuple[asyncio.Queue, asyncio.Queue]]):
  finished_player_ids = set()
  while len(finished_player_ids) < len(in_and_out_channel_pairs):
    # The grandmaster rotates among the boards until all the players are done.
    for i, (in_channel, out_channel) in enumerate(in_and_out_channel_pairs):
      if i in finished_player_ids:
        print(f"Grandmaster skipping player #{i} because they are done.")
        continue

      # Declare that we have arrived at the table.
      await out_channel.put(PossibleActions.GRANDMASTER_ARRIVES)

      # We have to wait for this player to make a move.
      move = await in_channel.get()
      # If the player has resigned, then we can break.
      if move is PossibleActions.RESIGN:
        finished_player_ids.add(i)
        continue
      assert move is PossibleActions.MAKE_MOVE
      
      # Now the grandmaster has to make a move or resign.
      print(f"Grandmaster considering move for player #{i}.")
      await asyncio.sleep(random.randint(1, 2))

      # The grandmaster has a fixed, small probability of resigning.
      should_resign = random.random() < 0.01
      if should_resign:
        print(f"Grandmaster resigns on move for player #{i}.")
        await out_channel.put(PossibleActions.RESIGN)
        finished_player_ids.add(i)
        continue
      
      # Otherwise, the grandmaster makes a move.
      print(f"Grandmaster making move for player #{i}.")
      await out_channel.put(PossibleActions.MAKE_MOVE)
      

async def main():
  NUM_PLAYERS = 10
  coroutines = []
  grandmaster_in_and_out_channels = []
  for i in range(NUM_PLAYERS):
    player_move_channel = asyncio.Queue()
    grandmaster_move_channel = asyncio.Queue()
    coroutines.append(asyncio.create_task(chess_player(i, player_move_channel, grandmaster_move_channel)))
    grandmaster_in_and_out_channels.append((player_move_channel, grandmaster_move_channel))
  coroutines.append(asyncio.create_task(grandmaster(grandmaster_in_and_out_channels)))
  await asyncio.gather(*coroutines)

if __name__ == "__main__":
  asyncio.run(main())
