import { useState } from 'react';
import {
  Accordion,
  AccordionItem,
  Button,
  ClickableTile,
  Link,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tag,
  Tile,
} from '@carbon/react';
import { Checkmark, Launch, WarningAlt } from '@carbon/icons-react';
import { sendClarification } from './customSendMessage.jsx';

const SERVICE_TAGS = {
  opensearch: { label: 'OpenSearch Vector DB', type: 'teal' },
};

// Legacy label the backend still emits; nothing on Spyre uses watsonx, so don't show it.
const HIDDEN_SERVICES = new Set(['watsonx_assistant']);

const METHOD_LABELS = {
  nlp_intent_detection: 'NLP intent detection',
  hybrid_table_lookup: 'Direct table lookup (no LLM)',
  full_rag_generation: 'Full RAG with LLM generation',
};

/** Link back to the original IBM Sales Manual page. */
function SourceLink({ url, label }) {
  if (!url) return null;
  return (
    <Link href={url} target="_blank" rel="noopener noreferrer" renderIcon={Launch}>
      {label || url}
    </Link>
  );
}

/** Ambiguous question: pick one option, the original question is re-sent with it. */
export function ClarificationBlock({ data, instance }) {
  const [chosen, setChosen] = useState(null);
  return (
    <div className="chat-block chat-block--options">
      {data.options.map((opt) => (
        <Button
          key={opt.value}
          kind={chosen === opt.value ? 'primary' : 'tertiary'}
          size="sm"
          disabled={chosen !== null}
          onClick={() => {
            setChosen(opt.value);
            sendClarification(instance, {
              prompt: data.prompt,
              param: data.param,
              value: opt.value,
              label: opt.label,
            });
          }}
        >
          {opt.label}
        </Button>
      ))}
    </div>
  );
}

/** Activation / physical features as an accordion, each expandable to the manual text. */
export function FeaturesBlock({ data }) {
  const features = data.features || [];
  if (features.length === 0) {
    return <Tile>No features found for this server.</Tile>;
  }
  return (
    <Accordion size="sm" className="chat-block">
      {features.map((f) => (
        <AccordionItem
          key={f.feature_code}
          title={
            <span className="feature-title">
              <strong>#{f.feature_code}</strong>{' '}
              {(f.description || 'No description').slice(0, 70)}
              {f.is_available ? (
                <Tag type="green" size="sm" renderIcon={Checkmark}>
                  Available
                </Tag>
              ) : (
                <Tag type="red" size="sm" renderIcon={WarningAlt}>
                  Discontinued
                </Tag>
              )}
            </span>
          }
        >
          <p>{f.description}</p>
          {f.discontinued_date && (
            <p className="chat-muted">Discontinued: {f.discontinued_date}</p>
          )}
          {f.chunk_text && <pre className="chat-pre">{f.chunk_text}</pre>}
          <SourceLink
            url={f.metadata?.source_url}
            label="View in IBM Sales Manual"
          />
        </AccordionItem>
      ))}
    </Accordion>
  );
}

function parseMarkdownTable(text) {
  const rows = String(text)
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.startsWith('|'))
    .filter((l) => !/^\|[\s:|-]+\|?$/.test(l))
    .map((l) => l.replace(/^\||\|$/g, '').split('|').map((c) => c.trim()));
  return rows.length >= 2 ? rows : null;
}

/** Lifecycle table exactly as published in the Sales Manual. */
export function LifecycleTableBlock({ data }) {
  const rows = parseMarkdownTable(data.table);
  if (!rows) return <pre className="chat-pre">{data.table}</pre>;
  const [head, ...body] = rows;
  return (
    <div className="chat-block">
      <p className="chat-muted">Lifecycle table from the Sales Manual</p>
      <Table size="sm" useZebraStyles>
        <TableHead>
          <TableRow>
            {head.map((h, i) => (
              <TableHeader key={i}>{h}</TableHeader>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {body.map((r, i) => (
            <TableRow key={i}>
              {head.map((_, j) => (
                <TableCell key={j}>{r[j] ?? ''}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** Original IBM Sales Manual link (always visible) + the retrieved context (expandable). */
export function SourcesBlock({ data }) {
  const [open, setOpen] = useState(false);
  const chunks = data.chunks || [];
  return (
    <div className="chat-block">
      {data.source_url && (
        <ClickableTile
          href={data.source_url}
          target="_blank"
          rel="noopener noreferrer"
          renderIcon={Launch}
        >
          <p className="chat-muted">Source - IBM Sales Manual</p>
          <strong>{data.source_filename || data.source_url}</strong>
        </ClickableTile>
      )}
      {chunks.length > 0 && (
        <>
          <Button kind="ghost" size="sm" onClick={() => setOpen(!open)}>
            {open ? 'Hide context used' : `Show context used (${chunks.length})`}
          </Button>
          {open &&
            chunks.map((c, i) => (
              <Tile key={i} className="chat-chunk">
                <div>
                  <Tag type="blue" size="sm">
                    Chunk {i + 1}
                  </Tag>
                  {c.section && (
                    <Tag type="outline" size="sm">
                      {c.section}
                    </Tag>
                  )}
                  {typeof c.score === 'number' && (
                    <Tag type="green" size="sm">
                      Score {c.score.toFixed(3)}
                    </Tag>
                  )}
                </div>
                <p className="chat-muted">{c.text}</p>
                <SourceLink url={c.source} label="Open this section's source" />
              </Tile>
            ))}
        </>
      )}
    </div>
  );
}

/** How the answer was produced: services used, method and response time. */
export function MetaBlock({ data }) {
  return (
    <div className="chat-block chat-meta">
      {data.services.filter((s) => !HIDDEN_SERVICES.has(s)).map((s) => {
        const known =
          s === 'llm'
            ? {
                label: data.llm_model === 'granite' ? 'Granite LLM' : 'LLM',
                type: 'purple',
              }
            : SERVICE_TAGS[s] || { label: s, type: 'gray' };
        return (
          <Tag key={s} type={known.type} size="sm">
            {known.label}
          </Tag>
        );
      })}
      {data.processing_method && (
        <Tag type="outline" size="sm">
          {METHOD_LABELS[data.processing_method] || data.processing_method}
        </Tag>
      )}
      {data.response_time_ms && (
        <span className="chat-muted">{data.response_time_ms} ms</span>
      )}
    </div>
  );
}
