from langgraph.graph import StateGraph, START, END

from nodes.state import State
from nodes.planning import planning
from nodes.overview import overview
from nodes.replanning import replanning

graph = StateGraph(State)

graph.add_node("planning", planning)
graph.add_node("overview", overview)
graph.add_node("replanning", replanning)

graph.add_edge(START, "planning")
graph.add_edge("planning", "overview")
graph.add_edge("overview", "replanning")

agent = graph.compile()
