from graphviz import Digraph

# Create a directed graph
dot = Digraph(comment="Experience Model Relationships", format="png")

# Define nodes
dot.node("User", "User\n(Django Auth User)", shape="box", style="filled", fillcolor="lightblue")
dot.node("Employment", "Employment", shape="box", style="filled", fillcolor="lightyellow")
dot.node("Education", "Education", shape="box", style="filled", fillcolor="lightyellow")
dot.node("Experience", "Experience", shape="box", style="filled", fillcolor="lightgreen")

# Define edges with relationships
dot.edge("User", "Experience", label="1 → many", dir="forward")
dot.edge("Employment", "Experience", label="0/1 → many", dir="forward")
dot.edge("Education", "Experience", label="0/1 → many", dir="forward")

# Save and render
output_path = "experience_model_relationships"
dot.render(output_path)

output_path + ".png"
