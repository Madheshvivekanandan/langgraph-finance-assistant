import { useEffect, useId, useRef, useState } from 'react'
import { usePrefersDark } from '../hooks/usePrefersDark'

interface Props {
  /** Mermaid flowchart source, generated server-side from the live graph. */
  chart: string
}

type RenderStatus = 'loading' | 'ready' | 'error'

/** Reads a resolved (literal) colour from a CSS custom property. `var()`
 *  substitution happens at computed-value time, so this never returns the
 *  token reference itself — mermaid's `themeVariables` cannot consume
 *  `var(--x)` strings, only literal colours. */
function resolveToken(name: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

/**
 * Rewrites the `classDef default/first/last` lines LangChain's
 * `draw_mermaid()` bakes into the source (D4). An explicit `classDef` fill
 * beats anything `themeVariables` sets, so setting a theme alone cannot fix
 * the near-white-on-near-white bug — the fill has to be replaced outright.
 * Rewritten, not stripped: the source still contains `class X first`/`class
 * X last` statements, and leaving those pointing at undefined classes risks
 * a mermaid warning or throw. If none of the three lines are present (a
 * future LangChain version renamed them), the same three lines are appended
 * instead — a later `classDef` with the same name always wins, so this is
 * safe even when the replace *did* succeed and this still runs redundantly.
 */
function restyleClassDefs(
  source: string,
  colours: { fill: string; stroke: string; text: string; accentBg: string },
): string {
  const { fill, stroke, text, accentBg } = colours
  const styled = source
    .replace(
      /^\s*classDef\s+default\s+.*$/m,
      `\tclassDef default fill:${fill},stroke:${stroke},color:${text},line-height:1.2`,
    )
    .replace(
      /^\s*classDef\s+first\s+.*$/m,
      `\tclassDef first fill:${fill},stroke:${stroke},color:${text}`,
    )
    .replace(
      /^\s*classDef\s+last\s+.*$/m,
      `\tclassDef last fill:${accentBg},stroke:${stroke},color:${text}`,
    )
  if (/classDef\s+default/.test(styled)) return styled
  return (
    `${styled}\n` +
    `\tclassDef default fill:${fill},stroke:${stroke},color:${text}\n` +
    `\tclassDef first fill:${fill},stroke:${stroke},color:${text}\n` +
    `\tclassDef last fill:${accentBg},stroke:${stroke},color:${text}`
  )
}

/**
 * Renders mermaid source into an SVG.
 *
 * `mermaid` is dynamically imported inside the effect so it stays out of the
 * main bundle entirely - Vite emits it as a separate chunk fetched once this
 * component actually mounts (D1). The SVG mermaid returns is inserted via
 * `DOMParser` + `replaceChildren`, never `dangerouslySetInnerHTML`, to avoid
 * the innerHTML sink for content that ultimately comes from the network.
 *
 * Colour is entirely token-driven (D4): `theme: 'base'` plus `themeVariables`
 * resolved from the app's own custom properties, and the `classDef` lines
 * LangChain bakes into the source are rewritten to match. `usePrefersDark`
 * is a live media-query listener, not a one-time read, so flipping the OS
 * colour scheme re-renders the diagram without a reload.
 */
export function MermaidDiagram({ chart }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<RenderStatus>('loading')
  const rawId = useId()
  // useId() includes colons, which mermaid's internal `#id` selectors choke on.
  const diagramId = `mermaid-diagram-${rawId.replace(/[^a-zA-Z0-9]/g, '')}`
  const prefersDark = usePrefersDark()
  // Bumped on every effect run so StrictMode's dev-only double-invoke never
  // gives two overlapping `mermaid.render()` calls the same id. mermaid
  // creates a real (if temporary) DOM node keyed by that id while it lays
  // out the diagram; two concurrent calls sharing one id raced and produced
  // a visibly doubled, ghosted render — reproducible only in dev, and only
  // caught by actually looking at the screenshot, not by any automated check.
  const renderCountRef = useRef(0)

  useEffect(() => {
    let cancelled = false
    const renderId = `${diagramId}-${renderCountRef.current++}`

    async function render(): Promise<void> {
      setStatus('loading')
      try {
        const mermaid = (await import('mermaid')).default

        const fill = resolveToken('--bg-subtle', prefersDark ? '#1e222a' : '#eef1f5')
        const accentBg = resolveToken('--bg-selected', prefersDark ? '#1e2a46' : '#e3ebfd')
        const stroke = resolveToken('--border-strong', prefersDark ? '#697485' : '#6b7480')
        const text = resolveToken('--text-primary', prefersDark ? '#e9ecf1' : '#14181f')
        const canvas = resolveToken('--bg-canvas', prefersDark ? '#0f1114' : '#f6f7f9')
        const hover = resolveToken('--bg-hover', prefersDark ? '#242933' : '#e8ecf2')
        const surface = resolveToken('--bg-surface', prefersDark ? '#171a1f' : '#ffffff')

        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'strict',
          theme: 'base',
          fontFamily: 'system-ui, sans-serif',
          flowchart: { useMaxWidth: true },
          themeVariables: {
            background: canvas,
            primaryColor: fill,
            primaryBorderColor: stroke,
            primaryTextColor: text,
            secondaryColor: hover,
            tertiaryColor: surface,
            lineColor: stroke,
            textColor: text,
          },
        })

        const restyled = restyleClassDefs(chart, { fill, stroke, text, accentBg })
        const { svg } = await mermaid.render(renderId, restyled)
        if (cancelled) return
        const parsed = new DOMParser().parseFromString(svg, 'image/svg+xml')
        containerRef.current?.replaceChildren(parsed.documentElement)
        setStatus('ready')
      } catch {
        if (!cancelled) setStatus('error')
      }
    }

    void render()
    return () => {
      cancelled = true
    }
  }, [chart, diagramId, prefersDark])

  return (
    <>
      <div ref={containerRef} />
      {status === 'loading' && <p className="message">Rendering the diagram…</p>}
      {status === 'error' && (
        <p className="message message-error" role="alert">
          The diagram could not be rendered.
        </p>
      )}
    </>
  )
}
