"""
Pretty dumb Dijkstra snake, but makes use of a bunch of handy-dandy utility
functions and classes I wrote, so good example usage for those interested.
:author Charlie
"""
import bottle
import logging
from bottle import request
import numpy as np

from bsapi.models import *
import helicoptermom.lib.pathfinding as pathfinding
from helicoptermom.lib.gameobjects import make_map
from helicoptermom.lib.utils import neighbors_of

app = bottle.app()


@app.post("/start")
def start():
    return StartResponse("#03A9F4")


def vornoi_defense(board, you):
    map = make_map(board)

    # Calculate d matrices for every snake
    d_matrices = {}
    enemy_snakes = [snake for snake in board.snakes if snake.id != you.id]
    for snake in enemy_snakes:
        d_matrix = pathfinding.dijkstra(map, snake.head())
        d_matrices.update({snake.id: d_matrix})

    # For each option, simulate snake move and calculate Vornoi zones
    highest_vornoi_area = -1
    highest_scoring_option = None
    for next_point in neighbors_of(you.head()[0], you.head()[1], map):
        np_scores, predecessor = pathfinding.dijkstra(map, next_point)
        in_vornoi_zone = np.full((board.height, board.width), True, dtype=np.bool)

        # Get all points in your Vornoi zone
        for val in d_matrices.values():
            in_vornoi_zone = np.logical_and(in_vornoi_zone, val - np_scores > 0)

        vornoi_area = np.sum(in_vornoi_zone)
        if vornoi_area > highest_vornoi_area:
            highest_vornoi_area = vornoi_area
            highest_scoring_option = next_point

    return pathfinding.get_next_move(you.head(), [highest_scoring_option])


def hungry_mode(board, you):
    """ Used when we need food. Dijkstra to nearest food. """
    map = make_map(board)
    distance, predecessor = pathfinding.dijkstra(map, you.head())

    nearest_food = None
    closest_distance = np.inf
    for fx, fy in board.food:
        if distance[fy][fx] < closest_distance:  # TODO: port pathfinding.is_safe()
            closest_distance = distance[fy][fx]
            nearest_food = (fx, fy)

    if closest_distance == np.inf:
        # If we can't get to any food, use defense mode
        return vornoi_defense(board, you)
    else:
        path = pathfinding.find_path_dijkstra(nearest_food[0], nearest_food[1], predecessor)
        return pathfinding.get_next_move(you.head(), path)


@app.post("/move")
def move():
    snake_req = SnakeRequest(request.json)
    board = snake_req.board

    longest_snake = max(board.snakes, key=lambda s: len(s.body))
    if snake_req.you.health < 60 or len(snake_req.you.body) < len(longest_snake.body):
        next_move = hungry_mode(board, snake_req.you)
    else:
        next_move = vornoi_defense(board, snake_req.you)

    return MoveResponse(next_move)


if __name__ == "__main__":
    app.run(port=8000)
