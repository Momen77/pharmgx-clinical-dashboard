"""
D3.js JSON-LD Visualizer for Streamlit
Renders a JSON-LD graph as an interactive radial tree.
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from rdflib import Graph, URIRef
from collections import defaultdict


def get_node_label(g, node_uri):
    """Finds a human-readable label for a given node URI."""
    # Try common labeling properties
    for prop in [
        URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
        URIRef("http://schema.org/name"),
        URIRef("http://xmlns.com/foaf/0.1/name"),
        URIRef("http://schema.org/identifier"),
    ]:
        label = g.value(subject=node_uri, predicate=prop)
        if label:
            return str(label)
    # Fallback to a shortened URI
    return str(node_uri).split('/')[-1].split('#')[-1]


def jsonld_to_hierarchy(jsonld_data: dict):
    """Converts flat JSON-LD to a hierarchical structure for D3."""
    g = Graph().parse(data=json.dumps(jsonld_data), format="json-ld")

    # Find the root node (the patient)
    root_node = None
    for s, p, o in g:
        if (p, o) == (URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef("http://xmlns.com/foaf/0.1/Person")):
            root_node = s
            break

    if not root_node:
        return {"name": "No Patient Root Found", "children": []}

    # Build hierarchy recursively
    def build_children(node_uri, visited):
        if node_uri in visited:
            return None  # Avoid cycles
        visited.add(node_uri)

        children = []
        for _, p, o in g.triples((node_uri, None, None)):
            if isinstance(o, URIRef):
                child_node = build_children(o, visited.copy())
                if child_node:
                    children.append(child_node)

        node_type = str(g.value(subject=node_uri, predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")) or "")
        node_label = get_node_label(g, node_uri)

        # Assign color based on type
        color = "#1f77b4" # Default blue
        if "Gene" in node_type: color = "#2ca02c" # Green
        if "Variant" in node_type: color = "#ff7f0e" # Orange
        if "Drug" in node_type or "drug" in node_label.lower(): color = "#d62728" # Red
        if "Disease" in node_type or "disease" in node_label.lower(): color = "#9467bd" # Purple

        return {
            "name": node_label,
            "uri": str(node_uri),
            "color": color,
            "children": children if children else None
        }

    return build_children(root_node, set())


def get_node_details(jsonld_data: dict, node_uri: str):
    """Extracts all properties of a specific node from the graph."""
    g = Graph().parse(data=json.dumps(jsonld_data), format="json-ld")
    uri_ref = URIRef(node_uri)
    details = {}
    for _, p, o in g.triples((uri_ref, None, None)):
        prop_name = str(p).split('/')[-1].split('#')[-1]
        prop_value = str(o)
        if prop_name not in details:
            details[prop_name] = []
        details[prop_name].append(prop_value)
    return details


def render_d3_visualization(d3_data: dict):
    """Renders the D3.js radial tree in Streamlit."""
    
    # Convert Python dict to JSON string for JS
    d3_json = json.dumps(d3_data)

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        .node circle {{
          cursor: pointer;
          stroke: #3182bd;
          stroke-width: 1.5px;
        }}
        .node text {{
          font: 12px sans-serif;
          cursor: pointer;
        }}
        .link {{
          fill: none;
          stroke: #ccc;
          stroke-width: 1.5px;
        }}
      </style>
    </head>
    <body>
      <div id="chart"></div>
      <script src="https://d3js.org/d3.v7.min.js"></script>
      <script>
        const width = 900;
        const height = 900;
        const cx = width * 0.5;
        const cy = height * 0.5;
        const radius = Math.min(width, height) / 2 - 60;

        const tree = d3.tree()
            .size([2 * Math.PI, radius])
            .separation((a, b) => (a.parent == b.parent ? 1 : 2) / a.depth);

        const data = {d3_json};
        const root = tree(d3.hierarchy(data));

        const svg = d3.select("#chart").append("svg")
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", [-cx, -cy, width, height])
            .attr("style", "width: 100%; height: auto; font: 12px sans-serif;");

        const g = svg.append("g");

        // Links
        g.append("g")
            .attr("fill", "none")
            .attr("stroke", "#ccc")
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", 1.5)
          .selectAll("path")
          .data(root.links())
          .join("path")
            .attr("d", d3.linkRadial()
                .angle(d => d.x)
                .radius(d => d.y));

        // Nodes
        const node = g.append("g")
            .attr("stroke-linejoin", "round")
            .attr("stroke-width", 3)
          .selectAll("g")
          .data(root.descendants())
          .join("g")
            .attr("transform", d => `rotate(${{d.x * 180 / Math.PI - 90}}) translate(${{d.y}},0)`)
            .on("click", (event, d) => {{
                // Send the clicked node's URI back to Streamlit
                const clicked_uri = d.data.uri;
                window.parent.postMessage({{
                    isStreamlitMessage: true,
                    type: "set_query_params",
                    queryParams: {{ "clicked_node_uri": clicked_uri }}
                }}, "*");
            }});

        node.append("circle")
            .attr("fill", d => d.data.color || (d.children ? "#555" : "#999"))
            .attr("r", 4.5);

        node.append("text")
            .attr("dy", "0.31em")
            .attr("x", d => d.x < Math.PI === !d.children ? 6 : -6)
            .attr("text-anchor", d => d.x < Math.PI === !d.children ? "start" : "end")
            .attr("transform", d => d.x >= Math.PI ? "rotate(180)" : null)
            .text(d => d.data.name)
            .clone(true).lower()
            .attr("stroke", "white");

        // Zooming
        const zoom = d3.zoom().on("zoom", (event) => {{
            g.attr("transform", event.transform);
        }});
        svg.call(zoom);

      </script>
    </body>
    </html>
    """
    components.html(html_template, height=900, scrolling=False)