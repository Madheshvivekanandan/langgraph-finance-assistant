import { useGraphTopology } from '../hooks/useGraphTopology'
import { MermaidDiagram } from './MermaidDiagram'

const GRAPH_NAME = 'statement'

// A static, always-true description of the pipeline's reading order (D3). Not
// derived from the API response: node insertion order there reflects how the
// builder wired the graph, not the order a reader traces the diagram in.
const PIPELINE_STAGE_ORDER =
  'start, create statement, parse CSV, normalize rows, apply category rules, ' +
  'categorize with LLM, mark awaiting review, review low confidence, ' +
  'store transactions, record failure on error, end'

/** Shows the live topology of the statement ingestion pipeline (D2, D6). */
export function GraphView() {
  const { status, topology, errorMessage } = useGraphTopology(GRAPH_NAME)

  return (
    <div className="panel">
      <h2>Pipeline</h2>

      {status === 'loading' && <p className="message">Loading the pipeline diagram…</p>}

      {status === 'error' && (
        <p className="message message-error" role="alert">
          {errorMessage}
        </p>
      )}

      {status === 'ready' && topology && (
        <figure className="graph-figure">
          <div
            className="graph-diagram"
            role="img"
            aria-label={`${topology.title}: ${PIPELINE_STAGE_ORDER}`}
          >
            <MermaidDiagram chart={topology.mermaid} />
          </div>
          <figcaption className="graph-legend">
            Dashed edges are conditional branches. <strong>review_low_confidence</strong> is
            where the pipeline can pause for a person, via LangGraph&apos;s{' '}
            <code>interrupt()</code>. <strong>__error_handler__store_transactions</strong> is
            reached by an exception, not an edge — it never has an arrow pointing into it.
          </figcaption>
        </figure>
      )}
    </div>
  )
}
