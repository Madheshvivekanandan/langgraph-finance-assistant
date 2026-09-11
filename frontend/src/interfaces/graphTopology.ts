export type GraphNodeKind = 'start' | 'end' | 'error_handler' | 'node'

export interface GraphNode {
  id: string
  label: string
  kind: GraphNodeKind
}

export interface GraphEdge {
  source: string
  target: string
  conditional: boolean
  label: string | null
}

/** A graph's nodes and edges, plus the mermaid source that renders them. */
export interface GraphTopology {
  name: string
  title: string
  nodes: GraphNode[]
  edges: GraphEdge[]
  mermaid: string
}

export interface GraphSummary {
  name: string
  title: string
  node_count: number
}

export interface GraphList {
  graphs: GraphSummary[]
}
