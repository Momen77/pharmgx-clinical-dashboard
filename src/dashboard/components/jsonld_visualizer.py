import streamlit as st
import streamlit.components.v1 as components
import json
from collections import defaultdict

def get_best_label(node_obj, default_text="Unnamed"):
    """
    Finds the best human-readable label from a JSON object.
    It checks for common labeling properties in a specific order.
    """
    if not isinstance(node_obj, dict):
        return str(node_obj)

    # Prioritized list of keys to check for a label
    label_keys = [
        "skos:prefLabel",
        "rdfs:label",
        "schema:name",
        "name",
        "identifier"
    ]
    for key in label_keys:
        if node_obj.get(key):
            return node_obj[key]
    
    # Fallback if no prioritized key is found
    return default_text

def jsonld_to_force_graph_data(jsonld_data: dict):
    """
    Transforms the nested JSON-LD into a flat nodes/links structure
    suitable for a D3.js force-directed graph.
    """
    nodes = []
    links = []
    seen_nodes = set()

    # Helper to add a node if it hasn't been seen
    def add_node(node_id, label, node_type, data_obj={}):
        if node_id not in seen_nodes:
            seen_nodes.add(node_id)
            node_color_map = {
                "Patient": "#1f77b4",
                "Gene": "#2ca02c",
                "Variant": "#ff7f0e",
                "Drug": "#d62728",
                "Condition": "#9467bd",
                "Lifestyle": "#8c564b"
            }
            nodes.append({
                "id": node_id,
                "label": label,
                "type": node_type,
                "color": node_color_map.get(node_type, "#7f7f7f")
            })

    # 1. Process the root Patient node
    patient_id = jsonld_data.get('@id')
    patient_name = jsonld_data.get('name', 'Patient')
    add_node(patient_id, patient_name, "Patient", jsonld_data)

    # 2. Process Clinical Information
    if clinical_info := jsonld_data.get('clinical_information'):
        # Conditions
        for condition in clinical_info.get('current_conditions', []):
            cond_id = condition.get('@id')
            cond_label = get_best_label(condition, "Condition")
            add_node(cond_id, cond_label, "Condition", condition)
            links.append({"source": patient_id, "target": cond_id, "label": "has_condition"})

        # Medications
        for med in clinical_info.get('current_medications', []):
            med_id = med.get('@id')
            med_label = get_best_label(med, "Medication")
            add_node(med_id, med_label, "Drug", med)
            links.append({"source": patient_id, "target": med_id, "label": "takes_medication"})
            # Link medication to the condition it treats
            if treats := med.get('treats_condition', {}):
                treats_id = f"http://snomed.info/id/{treats.get('snomed:code')}"
                if treats_id in seen_nodes:
                    links.append({"source": med_id, "target": treats_id, "label": "treats"})

        # Lifestyle Factors
        for factor in clinical_info.get('lifestyle_factors', []):
            factor_id = factor.get('@id', f"lifestyle:{factor.get('rdfs:label')}")
            factor_label = get_best_label(factor, "Lifestyle Factor")
            add_node(factor_id, factor_label, "Lifestyle", factor)
            links.append({"source": patient_id, "target": factor_id, "label": "has_lifestyle_factor"})

    # 3. Process Variants
    gene_map = {} # To store gene nodes
    for variant in jsonld_data.get('variants', []):
        variant_id = variant.get('rsid') or variant.get('variant_id')
        if not variant_id: continue
        
        variant_node_id = f"variant:{variant_id}"
        variant_label = f"{variant.get('gene', '')} {variant_id}"
        add_node(variant_node_id, variant_label, "Variant", variant)

        # Link Variant to its Gene
        gene_symbol = variant.get('gene')
        if gene_symbol:
            if gene_symbol not in gene_map:
                gene_id = f"gene:{gene_symbol}"
                add_node(gene_id, gene_symbol, "Gene")
                gene_map[gene_symbol] = gene_id
            links.append({"source": gene_map[gene_symbol], "target": variant_node_id, "label": "has_variant"})

        # Link Variant to affected Drugs
        for drug in variant.get('drugs', []):
            drug_id = drug.get('snomed:uri')
            drug_label = drug.get('name')
            if drug_id and drug_label:
                add_node(drug_id, drug_label, "Drug", drug)
                links.append({"source": variant_node_id, "target": drug_id, "label": "affects_drug"})
                
    return {"nodes": nodes, "links": links}


def render_force_graph(graph_data: dict):
    """Renders the D3.js force-directed graph in Streamlit."""
    
    graph_json = json.dumps(graph_data)

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
            #container {{ display: flex; }}
            #chart {{ flex-grow: 1; height: 800px; border: 1px solid #ddd; border-radius: 8px; }}
            #legend {{ width: 200px; padding: 10px; background-color: #f9f9f9; border-left: 1px solid #ddd; }}
            .legend-item {{ display: flex; align-items: center; margin-bottom: 5px; font-size: 14px; }}
            .legend-swatch {{ width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
            .link {{ stroke: #999; stroke-opacity: 0.6; }}
            .node circle {{ stroke: #fff; stroke-width: 1.5px; cursor: pointer; }}
            .node text {{ pointer-events: none; font-size: 10px; fill: #333; }}
            .node:hover circle {{ stroke-width: 3px; stroke: black; }}
            #tooltip {{
                position: absolute;
                text-align: center;
                padding: 8px;
                font: 12px sans-serif;
                background: lightsteelblue;
                border: 0px;
                border-radius: 8px;
                pointer-events: none;
                opacity: 0;
            }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="chart"></div>
            <div id="legend">
                <h3>Legend</h3>
                <div class="legend-item"><span class="legend-swatch" style="background:#1f77b4"></span> Patient</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#2ca02c"></span> Gene</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#ff7f0e"></span> Variant</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#d62728"></span> Drug</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#9467bd"></span> Condition</div>
                <div class="legend-item"><span class="legend-swatch" style="background:#8c564b"></span> Lifestyle</div>
            </div>
        </div>
        <div id="tooltip"></div>

        <script src="https://d3js.org/d3.v7.min.js"></script>
        <script>
            const graphData = {graph_json};
            const width = document.getElementById('chart').clientWidth;
            const height = 800;

            const svg = d3.select("#chart").append("svg")
                .attr("width", width)
                .attr("height", height)
                .attr("viewBox", [0, 0, width, height]);

            const tooltip = d3.select("#tooltip");

            const simulation = d3.forceSimulation(graphData.nodes)
                .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(70))
                .force("charge", d3.forceManyBody().strength(-200))
                .force("center", d3.forceCenter(width / 2, height / 2));

            const link = svg.append("g")
                .attr("class", "links")
                .selectAll("line")
                .data(graphData.links)
                .enter().append("line")
                .attr("class", "link");

            const node = svg.append("g")
                .attr("class", "nodes")
                .selectAll("g")
                .data(graphData.nodes)
                .enter().append("g")
                .attr("class", "node")
                .call(drag(simulation));
            
            node.append("circle")
                .attr("r", d => d.type === 'Patient' ? 12 : 8)
                .attr("fill", d => d.color);

            node.append("text")
                .text(d => d.label)
                .attr("x", 12)
                .attr("y", 4);

            node.on("mouseover", (event, d) => {{
                tooltip.transition().duration(200).style("opacity", .9);
                tooltip.html(`<strong>Type:</strong> ${{d.type}}<br/><strong>ID:</strong> ${{d.id}}`)
                    .style("left", (event.pageX + 5) + "px")
                    .style("top", (event.pageY - 28) + "px");
            }})
            .on("mouseout", (d) => {{
                tooltip.transition().duration(500).style("opacity", 0);
            }});

            simulation.on("tick", () => {{
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                node
                    .attr("transform", d => `translate(${{d.x}}, ${{d.y}})`);
            }});

            function drag(simulation) {{
                function dragstarted(event) {{
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    event.subject.fx = event.subject.x;
                    event.subject.fy = event.subject.y;
                }}
                function dragged(event) {{
                    event.subject.fx = event.x;
                    event.subject.fy = event.y;
                }}
                function dragended(event) {{
                    if (!event.active) simulation.alphaTarget(0);
                    event.subject.fx = null;
                    event.subject.fy = null;
                }}
                return d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended);
            }}

        </script>
    </body>
    </html>
    """
    components.html(html_template, height=820)

# --- Streamlit App Main Logic ---
st.set_page_config(layout="wide", page_title="PGx Network Visualizer")

st.title("Interactive Pharmacogenomics (PGx) Patient Profile")
st.write(
    "This tool visualizes a patient's PGx profile from a JSON-LD file as an interactive **force-directed graph**. "
    "This network view helps uncover relationships between the patient's conditions, medications, and genetic variants. "
    "Drag nodes to rearrange the graph."
)

uploaded_file = st.file_uploader("Upload your comprehensive JSON-LD file", type=["json", "jsonld"])

if uploaded_file is not None:
    try:
        # Load the original data
        json_data = json.load(uploaded_file)

        # Transform data for the force-directed graph
        graph_data = jsonld_to_force_graph_data(json_data)
        
        if graph_data and graph_data["nodes"]:
            # Render the D3 visualization
            render_force_graph(graph_data)
        else:
            st.error("Could not parse the JSON-LD file to generate graph data.")

    except json.JSONDecodeError:
        st.error("Invalid JSON file. Please upload a valid JSON-LD file.")
    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.exception(e) # Provides a full traceback for debugging